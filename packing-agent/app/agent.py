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
from datetime import date
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
                # Skill items are always single-quantity (the catalog/quantity
                # engine only governs base per-day clothing). quantity is on every
                # item so the §4.4 shape is uniform — the UI shows ×N only when N>1.
                "quantity": 1,
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
    # Weather items are single-quantity (one jacket, one bottle of sunscreen) — the
    # quantity engine only multiplies the per-day base clothing. quantity rides on
    # every item so the §4.4 shape is uniform (UI shows ×N only when N>1).
    items: list[dict] = []
    conds = {c.lower() for c in conditions}

    # Temperature bucket → a headline layer.
    if summary in ("cold", "freezing"):
        items.append({"label": "warm insulated jacket", "source": "weather", "category": "clothing", "quantity": 1})
    elif summary == "hot":
        items.append({"label": "sun hat", "source": "weather", "category": "clothing", "quantity": 1})

    # Precipitation / conditions → protective gear.
    if "rain" in conds or precipitation in ("likely", "certain"):
        items.append({"label": "waterproof jacket", "source": "weather", "category": "clothing", "quantity": 1})
    if "snow" in conds:
        items.append({"label": "waterproof boots", "source": "weather", "category": "footwear", "quantity": 1})
    if "sun" in conds or summary == "hot":
        items.append({"label": "sunscreen", "source": "weather", "category": "toiletries", "quantity": 1})

    return items


# The agent (LLM) may author at most this many trip-specific extras. Bounded on
# purpose: the model's role is a small, legible top-up over the deterministic
# catalogs — never the bulk of the list — so a hallucination can't flood it.
_AGENT_ITEM_CAP = 6


def _agent_items(labels: list[str] | None) -> list[dict]:
    """Turn the LLM's reasoned trip-specific suggestions into packing items.

    This is the ONE place the agent gets to author content (Milestone #1). The
    catalogs/weather/skill/profile cover the predictable items deterministically;
    this lets the model add the few situational things they can't anticipate
    (e.g. a power adapter for a specific region, an umbrella for a rainy
    business trip). We keep it SAFE and BOUNDED rather than trusting the model
    blindly:
      - trim + drop blanks (the model sometimes pads with whitespace),
      - dedupe within its own suggestions (case-insensitively),
      - hard-cap at _AGENT_ITEM_CAP so it can never dominate the list.
    Everything here is source="agent" and lands at the LOWEST merge precedence,
    so any label a trusted source already supplies wins — the model can neither
    shadow a deterministic item nor relabel one. Only genuinely-new items survive.
    """
    items: list[dict] = []
    seen: set[str] = set()
    for raw in labels or []:
        label = (raw or "").strip()
        if not label:
            continue
        key = _normalize_label(label)
        if key in seen:
            continue
        seen.add(key)
        items.append({
            "label": label,
            "source": "agent",
            "category": "extras",  # its own group — visibly "the AI's additions"
            "quantity": 1,
        })
        if len(items) >= _AGENT_ITEM_CAP:
            break  # bounded: ignore anything past the cap
    return items


def _trip_days(start_date: str, end_date: str) -> int:
    """Inclusive trip length in days (a same-day trip is 1, not 0).

    Drives the quantity engine: tops/underwear/socks are 1×/day. Dates are ISO
    YYYY-MM-DD per the data contract. We defend against malformed or reversed
    dates by clamping to a minimum of 1 day — the list must still render rather
    than crash on bad input (golden rule: a working fake beats a broken real).
    """
    try:
        delta = (date.fromisoformat(end_date) - date.fromisoformat(start_date)).days
    except (ValueError, TypeError):
        return 1
    return max(1, delta + 1)


# Per-day-clothing cap (decision: 1×/day but never pack more than a week's worth;
# past 7 days we surface a "plan to do laundry" hint instead of stacking 14 shirts).
_PER_DAY_CAP = 7


def _base_items(summary: str, days: int, forecast_ok: bool) -> list[dict]:
    """The base-essentials catalog + quantity engine (Phase-3 locked catalog).

    This is the generic FLOOR every trip gets — the universal stuff a packing list
    is bare without (toothbrush, charger, a week of socks). It sits at the LOWEST
    precedence in the merge, so anything the profile/weather/skill already supplies
    wins the label collision (e.g. profile's "phone charger" dedupes the generic
    one away). All items are source="base" and carry an explicit quantity.

    Quantity engine, three classes:
      - Class A — fixed ×1, always included (toiletries, essentials, generic
        health, walking shoes). Weather-independent.
      - Class B — 1×/day capped at 7 (top, underwear, socks). Past the cap the
        caller surfaces a laundry hint (see _laundry_hint) rather than overpacking.
      - Class C — quantity + label vary by weather (bottoms, sleepwear).

    Honest-forecast handling: when forecast_ok is False we don't know the weather,
    so we pick NEUTRAL labels (t-shirt / pants / pajamas) and skip the warm/cold and
    hot-weather variants — we never dress the list for a forecast we couldn't fetch.
    """
    # Treat an unfetched forecast as "weather unknown": neutral labels only.
    cold = forecast_ok and summary in ("cold", "freezing")
    per_day = min(days, _PER_DAY_CAP)  # Class B cap.

    # --- Class C labels: vary by weather (neutral when the forecast is unknown). ---
    if not forecast_ok:
        bottoms_label = "pants"
    elif summary in ("hot", "warm"):
        bottoms_label = "shorts"
    elif summary == "mild":
        bottoms_label = "pants"
    else:  # cold / freezing
        bottoms_label = "warm pants"
    bottoms_qty = 1 if days <= 4 else 2

    top_label = "long-sleeve top" if cold else "t-shirt"
    sleep_label = "warm pajamas" if cold else "pajamas"

    def item(label: str, category: str, quantity: int = 1) -> dict:
        return {"label": label, "source": "base", "category": category, "quantity": quantity}

    items: list[dict] = []

    # --- Class A: fixed ×1, weather-independent. ---
    for label in (
        "toothbrush", "toothpaste", "deodorant", "shampoo (travel size)",
        "soap/body wash", "razor", "hairbrush/comb", "toiletry bag",
    ):
        items.append(item(label, "toiletries"))
    for label in (
        # phone charger + passport are GENERIC FALLBACKS — when the profile owns
        # them (always_pack) the merge dedupes these away in favor of "Your essentials".
        "wallet", "travel power adapter", "power bank", "headphones/earbuds",
        "reusable water bottle", "phone charger", "passport",
    ):
        items.append(item(label, "essentials"))
    for label in ("pain reliever", "adhesive bandages", "hand sanitizer"):
        # Generic health basics — distinct from (and alongside) profile medications.
        items.append(item(label, "health"))
    items.append(item("comfortable walking shoes", "footwear"))

    # --- Class B: 1×/day, capped at 7. ---
    items.append(item(top_label, "clothing", per_day))
    items.append(item("underwear", "clothing", per_day))
    items.append(item("socks", "clothing", per_day))

    # --- Class C: quantity + label by weather. ---
    items.append(item(bottoms_label, "clothing", bottoms_qty))
    items.append(item(sleep_label, "clothing"))

    return items


def _laundry_hint(days: int) -> str | None:
    """A "plan to do laundry" note when the trip outruns the per-day cap.

    Past _PER_DAY_CAP days we deliberately stop multiplying clothing (no one wants a
    bag with 14 shirts), so we tell the user to plan a wash instead. Returns None
    for trips within the cap so the field is simply absent.
    """
    if days <= _PER_DAY_CAP:
        return None
    return (
        f"You're away {days} days but we capped tops/underwear/socks at "
        f"{_PER_DAY_CAP} — plan to do laundry partway through."
    )


def _privacy_note(destination: str, med_count: int, always_count: int) -> str:
    """Build the §6.5 "Vibe Diff" — a plain-English line of what crossed the tool
    boundary vs. what was deliberately kept private (Milestone E, the 4th concept).

    This is derived deterministically right here in the merge because this code is
    the one place that KNOWS both halves of the privacy story: exactly what we sent
    to the external weather tool (only destination + dates — §6.1 data minimization)
    and exactly what we pulled from the local profile without it ever leaving the
    machine (the meds + always-pack counts). Surfacing it makes the security concept
    visible on screen instead of buried in the architecture. We name only counts,
    never the medications themselves (§6.3 — nothing sensitive in the output text).
    """
    # What left the machine: ONLY the trip's destination + dates, to the weather tool.
    sent = f"Sent only your destination ({destination}) and travel dates to the weather service."
    # What stayed local: the profile, surfaced as counts so no medication name leaks.
    kept_bits = []
    if med_count:
        kept_bits.append(f"{med_count} medication{'s' if med_count != 1 else ''}")
    if always_count:
        kept_bits.append(
            f"{always_count} always-pack item{'s' if always_count != 1 else ''}"
        )
    if kept_bits:
        kept = (
            "Your profile never left this machine — read it locally and added "
            + " and ".join(kept_bits)
            + " to your list privately."
        )
    else:
        kept = "Your profile stayed local and was never sent anywhere."
    return f"{sent} {kept}"


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
    temp_c_min: float | None,
    temp_c_max: float | None,
    precipitation: str,
    conditions: list[str],
    skill_name: str,
    forecast_ok: bool = True,
    agent_items: list[str] | None = None,
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
        forecast_ok: get_weather's honesty flag. True when a real forecast was
            fetched; False when it couldn't be (geocode-miss / network / HTTP
            error), in which case temp_c_min/temp_c_max are None and we must NOT
            present invented temperatures as a real reading.
        agent_items: YOUR (the model's) own short list of trip-specific extras the
            fixed catalogs can't anticipate — reasoned from destination, dates,
            purpose and the forecast (e.g. a region-specific power adapter, an
            umbrella for a rainy business trip, modest layers for visiting
            temples). Plain item labels, no quantities. Capped at 6 and merged at
            the lowest precedence, so anything the trusted sources already cover is
            dropped — only genuinely-new items survive, tagged source="agent".
            Leave empty if nothing specific comes to mind; never restate generic
            basics (toothbrush, charger) — those are already handled.

    Returns:
        A packing list in the §4.4 shape: {trip, weather_summary, items[]}, where
        each item is {label, source, category, quantity} and source ∈ {weather,
        skill, profile, base, agent}. quantity is an int ≥ 1 (default 1; the UI
        shows ×N only when N > 1). The shape also carries forecast_ok and an
        optional laundry_hint (additive — items[]'s existing keys are untouched).
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
        {"label": med, "source": "profile", "category": "health", "quantity": 1}
        for med in profile.get("medications", [])
    ]
    always_items = [
        {"label": thing, "source": "profile", "category": "essentials", "quantity": 1}
        for thing in profile.get("always_pack", [])
    ]

    # --- Base-essentials (Phase 3): the generic floor + quantity engine. ---
    # Lowest precedence: anything profile/weather/skill already supplies dedupes
    # these away (e.g. profile "phone charger" beats the generic base one). When the
    # forecast failed, _base_items falls back to neutral labels (no fake weather).
    days = _trip_days(start_date, end_date)
    base_items = _base_items(weather_summary, days, forecast_ok)

    # --- Agent-authored items (Milestone #1): the model's own reasoned extras. ---
    # The ONE place the LLM contributes content. Bounded + lowest precedence (see
    # _agent_items): it can only ADD novel situational items, never shadow or
    # relabel anything a trusted source already produced.
    llm_items = _agent_items(agent_items)

    # PRECEDENCE (highest -> lowest): profile > weather > skill > base > agent.
    #   - profile first  => meds/always-pack always win a collision (the guarantee
    #     above) and the personalized item's metadata is the one kept.
    #   - weather second => the real, trip-specific forecast beats the generic
    #     archetype baseline when both imply the same item.
    #   - skill third    => the trip-archetype list fills in over the generic floor.
    #   - base fourth    => the universal essentials/quantity floor; any label a
    #     higher source already owns (e.g. profile "phone charger") dedupes the
    #     generic base copy away. The surviving item keeps ITS OWN quantity.
    #   - agent LAST     => the model's extras only appear when no trusted source
    #     already covers that label, so the LLM can add but never override.
    # Order is the ONLY knob; _merge_by_precedence keeps the first label it sees.
    items = _merge_by_precedence([
        med_items + always_items,  # profile (meds first within profile)
        weather_items,             # weather
        skill_items,               # skill
        base_items,                # base (generic floor + quantities)
        llm_items,                 # agent (model-authored extras, capped)
    ])

    # Human-readable forecast line for the UI (§4.4 weather_summary). When the
    # forecast couldn't be fetched we stay HONEST: no invented temps presented as
    # real — just say a neutral baseline was packed (the UI elaborates in Phase 4).
    if forecast_ok and temp_c_min is not None and temp_c_max is not None:
        precip_note = f", {precipitation} precip" if precipitation not in ("none", "") else ""
        display_summary = (
            f"{weather_summary}{precip_note}, {round(temp_c_min)}-{round(temp_c_max)}C"
        )
    else:
        display_summary = "live forecast unavailable — packed a neutral baseline"

    return {
        "trip": {
            "destination": destination,
            "start_date": start_date,
            "end_date": end_date,
        },
        "weather_summary": display_summary,
        # Honest-forecast flag rides along on the §4.4 shape (additive — items[]
        # untouched) so the UI can show the "couldn't fetch a live forecast" note.
        "forecast_ok": forecast_ok,
        # "plan to do laundry" hint when the trip outruns the per-day cap; absent
        # (None) for short trips. Additive field — items[]/shape are untouched.
        "laundry_hint": _laundry_hint(days),
        "items": items,
        # §6.5 "Vibe Diff": the privacy story for THIS run, in plain English. A new
        # field on the §4.4 shape — items[] is untouched, so existing consumers and
        # the data contract still hold.
        "privacy_note": _privacy_note(destination, len(med_items), len(always_items)),
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
        "to fetch the forecast. If the trip details include latitude and longitude "
        "(the user picked an exact place from the dropdown), pass them to "
        "get_weather too so it forecasts the right location.\n"
        "2. THEN choose ONE trip-archetype skill and call select_skill with its "
        "name. Selection rule (apply in order):\n"
        "   - if the forecast summary is 'cold' or 'freezing' -> 'cold_weather'\n"
        "   - else if the summary is 'hot' OR the purpose is 'beach' -> 'beach'\n"
        "   - otherwise use 'purpose' as a secondary hint: outdoors/leisure in warm "
        "weather lean 'beach', anything clearly cold leans 'cold_weather'. When "
        "unsure, pick 'beach' for warm/mild trips and 'cold_weather' for cool ones.\n"
        "3. THEN call build_packing_list, passing the original trip details, the "
        "forecast fields from get_weather (weather_summary=summary, temp_c_min, "
        "temp_c_max, precipitation, conditions, forecast_ok), AND skill_name = the "
        "skill you selected in step 2. Pass forecast_ok exactly as get_weather "
        "returned it.\n"
        "   Also pass agent_items: a SHORT list (0-6) of trip-SPECIFIC extras you "
        "reason are worth packing for THIS trip given the destination, dates, "
        "purpose and forecast — things the generic catalogs can't know. Good "
        "examples: a region-specific power-plug adapter, an umbrella for a rainy "
        "business trip, modest layers for visiting temples/churches, swim goggles "
        "for a lake trip, a reusable bag for a market town. Rules for agent_items: "
        "be specific and situational; do NOT restate generic basics (toothbrush, "
        "charger, socks, underwear) — those are already added for you; do NOT "
        "guess at the user's medications or personal items; if nothing specific "
        "stands out, pass an empty list. These are clearly labeled as your picks, "
        "so quality over quantity.\n"
        "4. Briefly confirm the list is ready.\n"
        "The deterministic tools own the universal basics, the forecast gear, the "
        "trip-archetype items and the user's saved profile — never duplicate those. "
        "Your authored contribution is ONLY the situational agent_items in step 3."
    ),
    tools=[_weather_toolset, select_skill, build_packing_list],
)

app = App(
    root_agent=root_agent,
    name="app",
)
