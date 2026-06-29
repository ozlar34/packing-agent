# ruff: noqa
# Local, GCP-free web entrypoint for the packing-list agent (decision 6 topology).
#
#   python -m app.server   ->   FastAPI  ->  ADK agent (gemini-2.5-flash, AI Studio)
#
# This is intentionally separate from the scaffold's app/fast_api_app.py, which is
# wired for Cloud Run / A2A / Cloud Logging and needs GCP credentials at import.
# That file stays untouched for the deploy stretch; THIS file is the demo server.

import json
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google.adk.artifacts import InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from google.genai.errors import ClientError
from pydantic import BaseModel

from app.agent import _load_profile, PROFILE_PATH, app as adk_app

# Reuse the weather server's keyless Open-Meteo geocoding plumbing so the UI never
# has to talk to an external service directly (locked decision: UI is a dumb client,
# all external calls go through our server proxy).
from app.weather_server import _GEOCODE_URL, _get_json

# Load app/.env so GOOGLE_API_KEY (AI Studio) is available to the genai client.
load_dotenv(Path(__file__).resolve().parent / ".env")

APP_NAME = "app"
USER_ID = "demo-user"  # single hardcoded demo user (scope decision)
STATIC_DIR = Path(__file__).resolve().parent / "static"

# One Runner for the process; sessions are created per request (stateless form).
_runner = Runner(
    app=adk_app,
    session_service=InMemorySessionService(),
    artifact_service=InMemoryArtifactService(),
)


class TripInput(BaseModel):
    """§4.1 trip input from the form."""

    destination: str
    start_date: str
    end_date: str
    purpose: str
    # Picked from the geocoding dropdown (decision: dropdown captures lat/lon +
    # canonical label). Optional + additive — older non-dropdown callers still work,
    # and get_weather only *uses* these in Phase 2. For now they ride along on the
    # trip payload to the agent (accepted-but-not-yet-used: one unproven box).
    latitude: float | None = None
    longitude: float | None = None


class ProfileEdit(BaseModel):
    """Editable subset of the profile (the two headline lists the panel shows).

    Deliberately scoped to medications + always_pack: those are the items the
    "Your profile" panel surfaces and the only ones a user edits from the UI.
    preferences{avoids, notes} stays out of the contract here and is preserved
    untouched on write (it has no UI surface), so the editor never silently
    drops a hand-edited field.
    """

    medications: list[str]
    always_pack: list[str]


def _extract_packing_list(event) -> dict | None:
    """Pull the build_packing_list tool's structured return out of an event.

    We read the tool's function_response — NOT the model's prose — so the §4.4
    payload is exactly what the deterministic tool produced (decision 3).
    """
    if not (event.content and event.content.parts):
        return None
    for part in event.content.parts:
        fr = getattr(part, "function_response", None)
        if fr is None or fr.name != "build_packing_list":
            continue
        resp = fr.response
        if isinstance(resp, dict):
            # ADK passes dict returns through, but wraps some returns as {"result": ...}.
            if "items" in resp:
                return resp
            if "result" in resp and isinstance(resp["result"], dict):
                return resp["result"]
    return None


web = FastAPI(title="packing-agent (local demo)")


@web.post("/generate")
async def generate(trip: TripInput) -> dict:
    """Run the agent on the trip input and return the §4.4 packing list."""
    session_id = str(uuid.uuid4())
    await _runner.session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
    )

    # Hand the trip to the agent as a message; the agent decides to call the tool.
    message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=json.dumps(trip.model_dump()))],
    )

    packing_list: dict | None = None
    try:
        async for event in _runner.run_async(
            user_id=USER_ID, session_id=session_id, new_message=message
        ):
            found = _extract_packing_list(event)
            if found is not None:
                packing_list = found
    except ClientError as ce:
        # Free-tier Gemini caps requests/minute; ADK surfaces that as a
        # ClientError with code 429. Translate it into a clean JSON 429 so the
        # UI shows a helpful message instead of an unhandled 500. Any other
        # ClientError is a real fault — re-raise and let it 500.
        if ce.code == 429:
            raise HTTPException(
                status_code=429,
                detail=(
                    "Free-tier Gemini quota hit. The per-minute cap clears in ~1 min; "
                    "the per-day cap resets at midnight Pacific. Wait and retry."
                ),
            ) from ce
        raise

    if packing_list is None:
        raise HTTPException(
            status_code=502,
            detail="Agent did not produce a packing list (tool was not called).",
        )
    return packing_list


@web.get("/geocode")
async def geocode(q: str) -> dict:
    """Disambiguating place search for the destination autocomplete.

    Proxies Open-Meteo's keyless geocoding API and returns up to ~10 ranked
    candidates so the user can pick the EXACT place (killing the "Bali → a village
    near Kolkata" bug). The UI talks only to us, never to Open-Meteo directly.
    Returns {results: [{name, admin1, country, latitude, longitude, population}]}.
    Open-Meteo already ranks by relevance/population, so we preserve that order.
    """
    q = q.strip()
    if len(q) < 2:
        # Too short to disambiguate usefully; avoid a noisy upstream call.
        return {"results": []}
    try:
        data = _get_json(
            _GEOCODE_URL,
            {"name": q, "count": 10, "language": "en", "format": "json"},
        )
    except Exception:
        # Network/parse hiccup: degrade to "no matches" rather than 500 the UI.
        return {"results": []}

    results = [
        {
            "name": r.get("name"),
            "admin1": r.get("admin1"),
            "country": r.get("country"),
            "latitude": r.get("latitude"),
            "longitude": r.get("longitude"),
            "population": r.get("population"),
        }
        for r in (data.get("results") or [])
    ]
    return {"results": results}


@web.get("/profile")
async def profile() -> dict:
    """Read-only profile display data for the "Your profile" panel (Phase 4).

    Surfaces ONLY the two fields the panel renders — medications + always-pack —
    so the UI can visibly prove the agent "knows you". This is the LOCAL boundary
    (§6.4): showing medication NAMES in the user's own local UI is fine; the
    protected boundary is the EXTERNAL one (the weather tool still gets only
    destination + dates). preferences/avoids/notes are deliberately not returned —
    the panel doesn't show them, so we don't surface them. No write side exists:
    profile.json stays hand-edited (locked scope — no editor).
    """
    p = _load_profile()
    return {
        "medications": p.get("medications", []),
        "always_pack": p.get("always_pack", []),
    }


# Loopback hosts allowed to WRITE the profile. The profile holds medication names
# (§6 sensitive, local-only): writes are accepted only from the same machine, so
# even if the server is ever bound to 0.0.0.0 the editor stays local-only.
_LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost"}


@web.put("/profile")
async def update_profile(edit: ProfileEdit, request: Request) -> dict:
    """Write the editable profile fields back to profile.json (localhost only).

    The companion to the read-only GET /profile: lets the user maintain the two
    headline lists from the UI instead of hand-editing JSON. The data-minimization
    story is preserved — this endpoint only WRITES the local file; medication names
    never cross the external (weather) boundary, which still gets destination+dates.
    """
    client_host = request.client.host if request.client else None
    if client_host not in _LOCAL_HOSTS:
        # Sensitive personal data: refuse writes from anything but the local machine.
        raise HTTPException(status_code=403, detail="Profile is editable from localhost only.")

    # Normalize: trim each entry, drop blanks. The UI sends one item per textarea
    # line, so empty lines / stray whitespace must not become empty packing items.
    def _clean(items: list[str]) -> list[str]:
        return [s.strip() for s in items if s.strip()]

    # Read-modify-write so the un-edited preferences{} block survives untouched.
    p = _load_profile()
    p["medications"] = _clean(edit.medications)
    p["always_pack"] = _clean(edit.always_pack)

    # Atomic write: render to a temp file in the same dir, then replace, so a crash
    # mid-write can't leave a truncated/corrupt profile.json.
    tmp = PROFILE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(p, indent=2) + "\n")
    tmp.replace(PROFILE_PATH)

    return {"medications": p["medications"], "always_pack": p["always_pack"]}


@web.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


web.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(web, host="127.0.0.1", port=8000)
