# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import sys
from pathlib import Path

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.genai import types
from mcp import StdioServerParameters

# project root = one level above this app/ package (the packing-agent/ dir).
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# profile.json lives at the project root (one level above this app/ package).
# It is gitignored personal data (§6 — local-only). The AGENT reads it at
# reasoning time; the UI and external tools never see it.
PROFILE_PATH = PROJECT_ROOT / "profile.json"

# Trip-archetype skills live in skills/<name>/SKILL.md (decision 4). The set is a
# fixed allowlist: select_skill only ever reads one of these folders, so the LLM
# cannot make us read an arbitrary path. Keep this in sync with the skills/ dir.
SKILLS_DIR = PROJECT_ROOT / "skills"
SKILL_NAMES = ("cold_weather", "beach")


def _load_profile() -> dict:
    """Load the local user profile. Returns empty sections if absent so the
    spine still runs on a clean clone before profile.json is created."""
    try:
        return json.loads(PROFILE_PATH.read_text())
    except FileNotFoundError:
        return {"medications": [], "always_pack": [], "preferences": {}}


def _parse_skill_items(skill_text: str) -> list[dict]:
    """Deterministically parse the `## Packing items` list out of a SKILL.md.

    The item list is parsed by fixed Python (decision 4: "no LLM mis-parse"), NOT
    by the model. Convention: under the `## Packing items` heading, each item is a
    bullet `- <label> :: <category>`. Anything outside that section (the human
    guidance prose) is ignored here — it is surfaced to the model separately as
    rationale by select_skill.
    """
    items: list[dict] = []
    in_items = False
    for raw in skill_text.splitlines():
        line = raw.strip()
        if line.startswith("## "):
            # Enter the items section on its heading; any other H2 ends it.
            in_items = line[3:].strip().lower() == "packing items"
            continue
        if in_items and line.startswith("- ") and "::" in line:
            label, _, category = line[2:].partition("::")
            items.append({
                "label": label.strip(),
                "source": "skill",
                "category": category.strip(),
            })
    return items


def _load_skill(name: str) -> dict:
    """Load ONE trip-archetype skill folder (progressive disclosure, decision 4).

    Reads only skills/<name>/SKILL.md and returns both the human guidance prose
    (rationale for the model) and the deterministically-parsed item list. `name`
    is validated against the SKILL_NAMES allowlist so an unexpected value can never
    turn into an arbitrary file read. Returns an {"error": ...} dict on bad input
    or a missing file so neither tool ever hard-fails the run.
    """
    if name not in SKILL_NAMES:
        return {"error": f"unknown skill '{name}'; choose one of {list(SKILL_NAMES)}"}
    skill_path = SKILLS_DIR / name / "SKILL.md"
    try:
        text = skill_path.read_text()
    except FileNotFoundError:
        return {"error": f"skill '{name}' has no SKILL.md"}
    return {
        "name": name,
        "guidance": text,
        "items": _parse_skill_items(text),
    }


def select_skill(name: str) -> dict:
    """Load the trip-archetype skill the agent has chosen for this trip.

    This is the agent-facing progressive-disclosure tool (decision 4): the agent
    decides which archetype fits the forecast/purpose, calls select_skill with its
    name, and gets back the skill's guidance (so the model can reason about it) and
    the list of item labels it contributes. The agent then passes the SAME name to
    build_packing_list, which re-reads the items deterministically — so only the
    short skill *name* is ever threaded through the model, never the item list.

    Args:
        name: The skill to load. One of: cold_weather | beach.

    Returns:
        {name, guidance, items[]} for a known skill, or {error} otherwise.
    """
    return _load_skill(name)


def _weather_items(summary: str, precipitation: str, conditions: list[str]) -> list[dict]:
    """Deterministically turn a §4.3 forecast into weather-driven packing items.

    The agent reads the forecast and decides to call build_packing_list, but the
    mapping from weather → items is fixed Python (decision 3) so it can't drift.
    Milestone D folds this into the full three-source merge; for now it just
    proves "changing destination changes the forecast changes the list."
    """
    items: list[dict] = []
    conds = {c.lower() for c in conditions}

    # Temperature bucket → a headline layer.
    if summary in ("cold", "freezing"):
        items.append({"label": "warm insulated jacket", "source": "weather", "category": "clothing"})
    elif summary == "hot":
        items.append({"label": "sun hat", "source": "weather", "category": "clothing"})

    # Precipitation / conditions → protective gear.
    if "rain" in conds or precipitation in ("likely", "certain"):
        items.append({"label": "waterproof jacket", "source": "weather", "category": "clothing"})
    if "snow" in conds:
        items.append({"label": "waterproof boots", "source": "weather", "category": "footwear"})
    if "sun" in conds or summary == "hot":
        items.append({"label": "sunscreen", "source": "weather", "category": "toiletries"})

    return items


def build_packing_list(
    destination: str,
    start_date: str,
    end_date: str,
    purpose: str,
    weather_summary: str,
    temp_c_min: float,
    temp_c_max: float,
    precipitation: str,
    conditions: list[str],
    skill_name: str,
) -> dict:
    """Build a personalized packing list for a trip.

    This is the deterministic core (decision 3): the LLM decides to call it and
    passes the trip details plus the forecast it got from get_weather, but the
    list itself — especially the medications — is assembled by this Python code,
    never left to the model. That is what makes "it knows you" trustworthy.

    MILESTONE C: weather items are derived from the real forecast and skill items
    come from the trip-archetype skill the agent chose (skill_name). Items are read
    back from the SKILL.md deterministically here — the model only passes the skill
    *name* — so the agent's choice can't corrupt the actual item list. Milestone D
    adds the real three-source dedupe on top.

    Args:
        destination: Free-text place name, e.g. "Reykjavik, Iceland".
        start_date: Trip start, ISO YYYY-MM-DD.
        end_date: Trip end, ISO YYYY-MM-DD.
        purpose: One of leisure | business | beach | outdoors.
        weather_summary: §4.3 coarse bucket: hot | warm | mild | cold | freezing.
        temp_c_min: Forecast min temperature in °C.
        temp_c_max: Forecast max temperature in °C.
        precipitation: §4.3 precipitation likelihood, e.g. "likely" | "none".
        conditions: §4.3 notable conditions, e.g. ["rain", "wind"].
        skill_name: The trip-archetype skill chosen via select_skill, whose items
            are added to the list. One of: cold_weather | beach.

    Returns:
        A packing list in the §4.4 shape: {trip, weather_summary, items[]}, where
        each item is {label, source, category} and source ∈ {weather, skill, profile}.
    """
    profile = _load_profile()

    items: list[dict] = []

    # --- Weather-driven items (Milestone B): derived from the real forecast. ---
    items.extend(_weather_items(weather_summary, precipitation, conditions))

    # --- Skill-driven items (Milestone C): from the agent's chosen trip skill. ---
    # Re-read the chosen skill's items here (deterministically) rather than trust
    # the model to relay them. A bad/unknown name yields no skill items rather than
    # crashing — the weather + profile list still renders.
    skill = _load_skill(skill_name)
    items.extend(skill.get("items", []))

    # --- Profile items: the demo headline. Added UNCONDITIONALLY, every trip. ---
    # EVERY medication is always included regardless of destination or purpose.
    for med in profile.get("medications", []):
        items.append({"label": med, "source": "profile", "category": "health"})
    for thing in profile.get("always_pack", []):
        items.append({"label": thing, "source": "profile", "category": "essentials"})

    # Human-readable forecast line for the UI (§4.4 weather_summary).
    precip_note = f", {precipitation} precip" if precipitation not in ("none", "") else ""
    display_summary = (
        f"{weather_summary}{precip_note}, {round(temp_c_min)}-{round(temp_c_max)}C"
    )

    return {
        "trip": {
            "destination": destination,
            "start_date": start_date,
            "end_date": end_date,
        },
        "weather_summary": display_summary,
        "items": items,
    }


# get_weather lives in a separate MCP server (decision 5: stdio transport). ADK
# spawns app/weather_server.py as a subprocess — no port, no second terminal, the
# whole app is one launch command. The tool boundary enforces §6.1 data
# minimization: only destination + dates ever cross it, never the profile.
_weather_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=["-m", "app.weather_server"],
            cwd=str(PROJECT_ROOT),
        ),
    ),
    tool_filter=["get_weather"],
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=(
        "You are a personalized trip packing assistant. When the user gives you "
        "trip details (destination, start_date, end_date, purpose):\n"
        "1. FIRST call get_weather with the destination, start_date, and end_date "
        "to fetch the forecast.\n"
        "2. THEN choose ONE trip-archetype skill and call select_skill with its "
        "name. Selection rule (apply in order):\n"
        "   - if the forecast summary is 'cold' or 'freezing' -> 'cold_weather'\n"
        "   - else if the summary is 'hot' OR the purpose is 'beach' -> 'beach'\n"
        "   - otherwise use 'purpose' as a secondary hint: outdoors/leisure in warm "
        "weather lean 'beach', anything clearly cold leans 'cold_weather'. When "
        "unsure, pick 'beach' for warm/mild trips and 'cold_weather' for cool ones.\n"
        "3. THEN call build_packing_list, passing the original trip details, the "
        "forecast fields from get_weather (weather_summary=summary, temp_c_min, "
        "temp_c_max, precipitation, conditions), AND skill_name = the skill you "
        "selected in step 2.\n"
        "4. Briefly confirm the list is ready.\n"
        "Do not invent packing items yourself — the tools are the source of truth."
    ),
    tools=[_weather_toolset, select_skill, build_packing_list],
)

app = App(
    root_agent=root_agent,
    name="app",
)
