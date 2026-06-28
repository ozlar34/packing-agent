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


def _normalize_label(label: str) -> str:
    """Canonical key for collision detection.

    Two labels are "the same item" if they match after lowercasing and collapsing
    internal whitespace — so "Sun Hat", "sun hat" and "sun  hat" dedupe together.
    Kept intentionally conservative (no stemming/synonyms): the merge must be
    deterministic and explainable, and over-eager matching could silently drop a
    distinct item. Near-synonyms ("sunglasses" vs "shades") are left as separate
    items by design rather than guessed at.
    """
    return " ".join(label.lower().split())


def _merge_by_precedence(ordered_sources: list[list[dict]]) -> list[dict]:
    """Merge several item lists into one, deduping by label, first-seen wins.

    THIS IS THE MILESTONE D MERGE — the agentic core the judges most want to see.

    `ordered_sources` is a list of item lists already arranged from HIGHEST to
    LOWEST precedence. We walk them in that order and keep the FIRST item we see
    for each normalized label; any later list that repeats the same label is
    skipped. So precedence is encoded purely by ORDER — the caller decides who
    wins a collision simply by where it places each source in the list.

    Why first-seen-wins-by-order (the simplest defensible rule):
      - It is fully deterministic and has no special cases to reason about.
      - "Which source's metadata (source/category) survives a tie" reduces to the
        single, visible decision of how the caller orders the inputs.
      - The caller puts PROFILE first, so the medication/always-pack copy of a
        colliding label always wins — that is exactly the guarantee we want
        (see build_packing_list). Weather (real forecast) beats the generic skill
        baseline, so the more trip-specific item's source label survives.

    Real overlaps this collapses (left un-deduped before D, by design):
      - beach skill vs weather both leaning toward sun items, and
      - cold skill vs weather both leaning toward warm layers.
    The skill authors currently defer those to the weather tool to avoid exact
    duplicates, but this merge makes the system robust if that ever changes.
    """
    seen: set[str] = set()
    merged: list[dict] = []
    for source_items in ordered_sources:
        for item in source_items:
            key = _normalize_label(item["label"])
            if key in seen:
                # A higher-precedence source already contributed this label.
                continue
            seen.add(key)
            merged.append(item)
    return merged


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

    # === Milestone D: assemble the three sources, then MERGE (dedupe by label). ===
    # Each source is built into its own list first; the merge below decides the
    # final order and resolves any label collisions. Keeping the sources separate
    # makes the precedence decision explicit and the reasoning legible.

    # --- Weather-driven items (Milestone B): derived from the real forecast. ---
    weather_items = _weather_items(weather_summary, precipitation, conditions)

    # --- Skill-driven items (Milestone C): from the agent's chosen trip skill. ---
    # Re-read the chosen skill's items here (deterministically) rather than trust
    # the model to relay them. A bad/unknown name yields no skill items rather than
    # crashing — the weather + profile list still renders.
    skill_items = _load_skill(skill_name).get("items", [])

    # --- Profile items: the demo headline ("it knows you"). ---
    # EVERY medication is included UNCONDITIONALLY — regardless of destination,
    # purpose, weather, or any label collision. This is the headline value moment,
    # so it must never depend on the model and must never be the item a dedupe
    # drops. We guarantee that STRUCTURALLY: medications go into the FIRST (highest
    # precedence) slot of the merge, so a med is always the first occurrence of its
    # label and therefore the copy that survives. always_pack rides alongside it.
    med_items = [
        {"label": med, "source": "profile", "category": "health"}
        for med in profile.get("medications", [])
    ]
    always_items = [
        {"label": thing, "source": "profile", "category": "essentials"}
        for thing in profile.get("always_pack", [])
    ]

    # PRECEDENCE (highest -> lowest): profile > weather > skill.
    #   - profile first  => meds/always-pack always win a collision (the guarantee
    #     above) and the personalized item's metadata is the one kept.
    #   - weather second => the real, trip-specific forecast beats the generic
    #     archetype baseline when both imply the same item.
    #   - skill last      => the generic trip-archetype list fills in the rest.
    # Order is the ONLY knob; _merge_by_precedence keeps the first label it sees.
    items = _merge_by_precedence([
        med_items + always_items,  # profile (meds first within profile)
        weather_items,             # weather
        skill_items,               # skill
    ])

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
