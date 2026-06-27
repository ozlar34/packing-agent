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
from pathlib import Path

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

# profile.json lives at the project root (one level above this app/ package).
# It is gitignored personal data (§6 — local-only). The AGENT reads it at
# reasoning time; the UI and external tools never see it.
PROFILE_PATH = Path(__file__).resolve().parent.parent / "profile.json"


def _load_profile() -> dict:
    """Load the local user profile. Returns empty sections if absent so the
    spine still runs on a clean clone before profile.json is created."""
    try:
        return json.loads(PROFILE_PATH.read_text())
    except FileNotFoundError:
        return {"medications": [], "always_pack": [], "preferences": {}}


def build_packing_list(
    destination: str, start_date: str, end_date: str, purpose: str
) -> dict:
    """Build a personalized packing list for a trip.

    This is the deterministic core (decision 3): the LLM decides to call it and
    passes the trip details, but the list itself — especially the medications —
    is assembled by this Python code, never left to the model. That is what makes
    "it knows you" trustworthy.

    MILESTONE A (spine): weather and trip-archetype skills are still stubbed with
    a couple of placeholder items so the UI can show all three `source` types.
    Milestones B–D replace those stubs with the real weather tool + skill merge.

    Args:
        destination: Free-text place name, e.g. "Reykjavik, Iceland".
        start_date: Trip start, ISO YYYY-MM-DD.
        end_date: Trip end, ISO YYYY-MM-DD.
        purpose: One of leisure | business | beach | outdoors.

    Returns:
        A packing list in the §4.4 shape: {trip, weather_summary, items[]}, where
        each item is {label, source, category} and source ∈ {weather, skill, profile}.
    """
    profile = _load_profile()

    items: list[dict] = []

    # --- Stub: weather-driven items (Milestone B replaces this with get_weather) ---
    items.append({"label": "weather-appropriate jacket", "source": "weather", "category": "clothing"})

    # --- Stub: skill-driven items (Milestone C replaces this with select_skill) ---
    items.append({"label": "general toiletries", "source": "skill", "category": "toiletries"})

    # --- Profile items: the demo headline. Added UNCONDITIONALLY, every trip. ---
    # EVERY medication is always included regardless of destination or purpose.
    for med in profile.get("medications", []):
        items.append({"label": med, "source": "profile", "category": "health"})
    for thing in profile.get("always_pack", []):
        items.append({"label": thing, "source": "profile", "category": "essentials"})

    return {
        "trip": {
            "destination": destination,
            "start_date": start_date,
            "end_date": end_date,
        },
        "weather_summary": "(stubbed — real forecast arrives in Milestone B)",
        "items": items,
    }


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=(
        "You are a personalized trip packing assistant. When the user gives you "
        "trip details (destination, start_date, end_date, purpose), you MUST call "
        "the build_packing_list tool with those exact values, then briefly confirm "
        "the list is ready. Do not invent packing items yourself — the tool is the "
        "source of truth."
    ),
    tools=[build_packing_list],
)

app = App(
    root_agent=root_agent,
    name="app",
)
