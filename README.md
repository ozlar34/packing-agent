# Personalized Trip Packing-List Agent

> An AI **agent** that generates a personalized, trip-specific packing list by combining what it
> knows about the **trip** (destination, dates, purpose, live weather) with what it knows about
> **you** (medications, recurring essentials, preferences) — so you never forget the things
> generic lists miss.

**🔒 No API keys or secrets are committed to this repository.** The only secret (a Google AI
Studio key) lives in a gitignored `.env`, and the personal `profile.json` is gitignored too. See
[Privacy & security](#privacy--security).

Capstone for the Kaggle "AI Agents / Vibe Coding" course (Google-sponsored), **Concierge Agents**
track.

---

## The problem

Travellers forget the things generic checklists never know about: the **daily medication**, the
charger they always need, the rain layer the forecast quietly demands for *those specific dates in
that specific place*. A static template can't reason about any of it.

## The solution — "it knows you"

You fill a short web form (destination, dates, purpose). A stored **profile** holds your persistent
personal facts. The agent reads both, fetches the **live forecast**, picks the right **trip-archetype
skill**, and **merges** all three sources into a single checklist.

The headline value is **"it knows you"**: every medication and always-pack essential survives into
**every** list, regardless of trip type or weather — and we guarantee that *structurally*, not by
hoping the model remembers. That's the demo moment.

## Why an agent (and not a template)

The value requires *reasoning over multiple sources and orchestrating tools*: fetch live weather for
specific dates and place, choose the right domain knowledge (skill) for the trip type, and merge
that against persistent personal facts that must always be honored (e.g. medication) regardless of
trip. Deciding **what to call, when, and how to combine the results** is exactly what an agent does
and a template cannot.

---

## Architecture

Only the agent is "smart"; everything else is a tool or a data source it orchestrates.

```
        +-----------------------------+        +-----------------------------+
        |          Web UI             |        |        User profile         |
        | questionnaire + checklist   |        |  meds, essentials, prefs    |
        |  (destination, dates,       |        |  (profile.json)             |
        |   purpose)                  |        |                             |
        +--------------+--------------+        +--------------+--------------+
                       |                                      |
                       | trip input (JSON)                    | read at runtime
                       v                                      v
        +-------------------------------------------------------------------+
        |                       Core agent (ADK)                            |
        |  reads inputs -> calls weather tool -> selects ONE skill          |
        |  -> merges profile items + weather items + skill items            |
        |  CONCEPT 1: Agent (ADK)             app/agent.py                   |
        +----------------+----------------------------+---------------------+
                         |                            |
            calls (MCP)  |                            | loads on demand
                         v                            v
        +-----------------------------+   +-----------------------------+
        |     Weather MCP server      |   |   Trip skills (Agents CLI)  |
        |  get_weather(dest, dates)   |   |  beach / cold_weather       |
        |  CONCEPT 2: MCP Server      |   |  CONCEPT 3: Agent Skills    |
        |  app/weather_server.py      |   |  skills/<name>/SKILL.md     |
        +-----------------------------+   +-----------------------------+
                         \                            /
                          \                          /
                           v                        v
                    +-------------------------------------+
                    |        Rendered packing list        |
                    |   personalized, checkable output    |
                    +-------------------------------------+
```

**Request flow:** form → agent → `get_weather` (MCP) → `select_skill` → `build_packing_list` →
rendered §4.4 list.

### Components

| Component | Where | Responsibility |
|---|---|---|
| **Web UI** | `packing-agent/app/static/index.html` | Dumb client. Collects trip facts, POSTs to `/generate`, renders the returned list. No business logic. |
| **User profile** | `packing-agent/profile.json` (gitignored) | Persistent personal facts. Read by the **agent** at reasoning time — never by the UI, never sent to the weather tool, never logged. |
| **Core agent (ADK)** | `packing-agent/app/agent.py` | The orchestrator and the **only** place reasoning happens. Calls the weather tool, picks one skill, and runs the deterministic merge. |
| **Weather MCP server** | `packing-agent/app/weather_server.py` | A single tool `get_weather` over **stdio MCP**, backed by keyless **Open-Meteo**. ADK spawns it as a subprocess — no extra terminal, no port. |
| **Trip skills** | `packing-agent/skills/{cold_weather,beach}/SKILL.md` | One folder per trip archetype: human guidance + a `## Packing items` list. Loaded **on demand** (progressive disclosure). |
| **Local web server** | `packing-agent/app/server.py` | GCP-free FastAPI entrypoint that drives the ADK agent for the local demo. |

---

## Course concepts demonstrated

| # | Concept | Where it lives |
|---|---|---|
| 1 | **Agent (ADK)** | `app/agent.py` — `root_agent` (Gemini 2.5 Flash) orchestrates three tools; all reasoning is here. |
| 2 | **MCP server** | `app/weather_server.py` — `get_weather` exposed via FastMCP over **stdio**, consumed through ADK's `McpToolset`. |
| 3 | **Agent Skills** | `skills/cold_weather/` and `skills/beach/`, selected on demand by the `select_skill` tool (progressive disclosure). |
| 4 | **Security / privacy** | Data minimization at the tool boundary, local-only gitignored profile, no secrets in repo, no PII in logs — see below. |

### The deterministic three-source merge (the agentic core)

`build_packing_list` in `app/agent.py` is where points are won. The LLM decides *to call it* and
hands over the trip + forecast, but the list itself is assembled by Python — never left to the model.

- Three sources are built separately: **profile** items (medications + always-pack), **weather**
  items (derived from the live forecast), and **skill** items (from the chosen archetype).
- They are merged by `_merge_by_precedence`, which dedupes by normalized label and keeps the
  **first** occurrence — so **precedence is encoded purely by order**.
- **Precedence: profile > weather > skill.** Medications occupy the **first** profile slot, so a
  medication is always the first occurrence of its label and can never be the copy a collision
  drops. **The meds-always guarantee is structural**, not an afterthought.

Each output item carries a `source ∈ {profile, weather, skill}` so the agent's reasoning stays
legible in the rendered list.

---

## Setup & run (from a clean clone)

**Prerequisites:** [`uv`](https://docs.astral.sh/uv/getting-started/installation/) (Python package
manager) and a free [Google AI Studio API key](https://aistudio.google.com/apikey).

```bash
# 1. Clone and enter the repo
git clone <repo-url> ai-travel-packing-agent
cd ai-travel-packing-agent

# 2. Create your local profile (gitignored personal data)
cp profile.example.json packing-agent/profile.json

# 3. Add your AI Studio key (gitignored secret)
cp .env.example packing-agent/app/.env
#    then edit packing-agent/app/.env and set GOOGLE_API_KEY=<your key>

# 4. Run the app (uv installs deps on first run; the MCP weather
#    server is auto-spawned — one command, no second terminal)
cd packing-agent
uv run python -m app.server
```

Open **http://127.0.0.1:8000**, fill in the form, and click **Generate**.

**The money demo:** change the destination from a warm place (e.g. *Dubai*) to a cold one (e.g.
*Reykjavik*) and watch the list change with the live forecast — while your medication and essentials
persist on **every** list.

> **Free-tier quota caveat:** the AI Studio free tier has a per-day request cap (each Generate makes
> ~3 model calls). Heavy testing can exhaust it; the per-minute cap clears in ~1 min and the daily
> cap resets at midnight Pacific. **Before a live demo, enable billing on the AI Studio key**
> (pay-as-you-go; Flash is fractions of a cent per request) to remove the daily cap. The app maps a
> 429 to a clean, honest message in the UI instead of failing opaquely.

---

## Privacy & security

This is a Concierge agent handling personal and medical data, so the boundaries are deliberate:

1. **Data minimization at the tool boundary** — the weather tool receives **only** destination +
   dates. Profile, medications, and preferences never cross into any external request.
   (`app/weather_server.py` documents and enforces this.)
2. **No secrets in repo** — Open-Meteo is keyless. The only secret is the AI Studio key, which lives
   in a **gitignored** `.env`; `.env.example` ships only the variable names.
3. **No sensitive data in logs** — the profile and medications are never logged.
4. **Local-only profile** — `profile.json` is gitignored, read locally by the agent only, and never
   uploaded or sent to third parties.

---

## Project status

Built incrementally, kept runnable end-to-end at every step:

- ✅ **A — hardcoded spine:** form → ADK agent → rendered list, profile medication present.
- ✅ **B — real MCP weather:** `get_weather` over stdio MCP, backed by Open-Meteo; destination
  changes the forecast changes the list.
- ✅ **C — trip skills:** two contrasting skills with on-demand `select_skill` loading.
- ✅ **D — the merge:** deterministic three-source dedupe with the structural meds-always guarantee.
- 🔜 **E — stretch:** further security hardening, Cloud Run deployment, polish.

---

## Tech stack

ADK (agent orchestration) · MCP / FastMCP (weather tool, stdio transport) · Open-Meteo (keyless
weather) · skill folders with `SKILL.md` · FastAPI + a minimal static front end · `profile.json`
(JSON file store, single demo user) · `uv` for dependency management.
