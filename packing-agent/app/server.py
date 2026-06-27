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
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google.adk.artifacts import InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import BaseModel

from app.agent import app as adk_app

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
    async for event in _runner.run_async(
        user_id=USER_ID, session_id=session_id, new_message=message
    ):
        found = _extract_packing_list(event)
        if found is not None:
            packing_list = found

    if packing_list is None:
        raise HTTPException(
            status_code=502,
            detail="Agent did not produce a packing list (tool was not called).",
        )
    return packing_list


@web.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


web.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(web, host="127.0.0.1", port=8000)
