# Session Handoff — resume point

> Newest entry on top. Read `docs/ADK_SETUP.md` (decisions + "Current build status")
> alongside this. This file is the "where we stopped / what's next" layer.

## 2026-06-28 — Milestone B complete (real MCP weather)

### Situation
Milestone B is DONE and verified end-to-end. The agent now calls a real weather tool over
**stdio MCP** and the list changes with the destination (the money-demo moment).

- New file `packing-agent/app/weather_server.py` — FastMCP **stdio** server exposing
  `get_weather(destination, start_date, end_date)` → §4.3. Real **Open-Meteo** (keyless):
  geocode → daily forecast → normalized `summary`/`conditions`. Out-of-range dates (Open-Meteo
  only forecasts ~16 days) fall back to the location's next-7-day forecast; geocode/network
  failure → neutral "mild" so the run never hard-fails. §6.1 holds: only destination + dates
  cross the boundary, nothing logged.
- `app/agent.py` — added `McpToolset(StdioConnectionParams(StdioServerParameters(...)))`
  spawning `python -m app.weather_server`; instruction calls `get_weather` first, then relays
  §4.3 fields into `build_packing_list`. `build_packing_list` gained weather params + a
  `_weather_items` helper (deterministic weather→items) and now builds the real
  `weather_summary` string. The `general toiletries` **skill stub remains** (that's Milestone C).
- Added `mcp==1.28.1` (`uv add mcp`) — needed by ADK's MCP client AND the FastMCP server.

### Decision changed this session
- **Model → `gemini-2.5-flash-lite`** (was `gemini-2.5-flash`). Free-tier rate limits: 2.5-flash
  503s, flash-latest/2.0-flash 429. Lite has open quota and ran the demo cleanly. Oguz approved.
  decision 2 in `docs/ADK_SETUP.md` updated. Revisit on a paid tier.

### Verified
Reykjavik → `cold, likely precip, 6-14C` → warm insulated jacket + waterproof jacket.
Dubai → `hot, 28-42C` → sun hat + sunscreen. Both keep `daily inhaler` + always_pack. ✔

### Pick up from here — Milestone C (trip skills)
1. **Re-read:** spec §5.3 + decision 4 in `docs/ADK_SETUP.md`; `app/agent.py` (the
   `general toiletries` skill stub to replace).
2. Create two skill folders `skills/beach/` + `skills/cold_weather/`, each a `SKILL.md` +
   packing items. Add a `select_skill(name)` tool that reads ONLY the chosen folder
   (progressive disclosure). Selection rule simplest first: `summary in [cold,freezing] →
   cold_weather`; `hot`/`beach` → beach; `purpose` secondary hint.
3. The agent (which already has the §4.3 `summary`) picks the skill and feeds its items into
   `build_packing_list`. **Done-when:** a cold trip loads cold_weather items, a hot/beach trip
   loads beach items — visible switch.

### Still not done
- No `README.md` yet (20-pt deliverable). adk-docs MCP still ⏸ pending approval (needs a
  `the assistant` restart) — fell back to skill refs + reading the installed ADK source, fine.
  Milestones C/D/E pending. Scaffold's live-LLM integration tests not run (would burn free
  quota / 503).

---

## 2026-06-27 — Milestone A complete (commit `8065f0f`)

### Situation
Milestone A (hardcoded spine) is DONE and verified end-to-end. The ADK project was
scaffolded into the **`packing-agent/`** subdir (nested layout, chosen over flat).
Form → ADK agent (gemini-2.5-flash via AI Studio key) → §4.4 packing list containing the
profile medication ("daily inhaler"), HTTP 200. The spine is the REAL architecture (the LLM
function-calls a deterministic tool that is the source of truth), not a throwaway fake — so
B–E slot in by replacing stubs, one at a time.

### Decisions locked this session (full list in docs/ADK_SETUP.md — don't re-litigate)
- **Layout:** ADK project nested in `packing-agent/`; repo root keeps spec/docs/AGENTS.md.
- **Local entrypoint** is our own `packing-agent/app/server.py` (GCP-free, decision 6). The
  scaffold's `app/fast_api_app.py` is GCP-coupled (`google.auth.default()` + Cloud Logging at
  import) and is kept ONLY for the Cloud Run stretch (E). Do not use it for local dev.
- §4.4 list is extracted from the tool's `function_response`, NOT model prose (reliable).
- Model `gemini-flash-latest` preserved as scaffolded — never change unless asked.

### State on disk
- Code committed/pushed to `main`. `packing-agent/profile.json` and `packing-agent/app/.env`
  are **gitignored** (PII + secret) — NOT in the repo, by design.
- Clean-clone setup: `cp profile.example.json packing-agent/profile.json`, then put a real
  AI Studio key in `packing-agent/app/.env` (`GOOGLE_API_KEY`). Then:
  `cd packing-agent && uv run python -m app.server` → http://127.0.0.1:8000.
- adk-docs MCP server was **⏸ Pending approval** this session (project MCP needs a `the assistant`
  restart to approve). Fell back to `.agent/skills/.../references/*.md` — fine. Re-check next.

### Pick up from here — Milestone B (real MCP weather)
1. **Re-read first:** `docs/ADK_SETUP.md` ("Current build status"); `packing-agent/app/agent.py`
   (the stub items to replace); spec §4.3 + §5.2.
2. Confirm adk-docs MCP connected (`the assistant mcp list`); load skills `google-agents-cli-workflow`
   then `google-agents-cli-adk-code` before writing ADK code. Use `MCPToolset` over **stdio**
   (decision 5).
3. **Next action:** create `weather_server.py` MCP server (stdio) exposing
   `get_weather(destination, start_date, end_date)` returning a **stubbed** §4.3 response first;
   wire the agent via `MCPToolset` and verify the call works; THEN swap the stub body for real
   **Open-Meteo** (keyless) normalized to §4.3 (map temps → `summary` bucket). Replace the
   "weather-appropriate jacket" stub item in `build_packing_list` accordingly. One stub at a
   time (golden rule). **Done-when:** changing destination changes the forecast changes the list.

### Not yet done
- No `README.md` yet (20-pt deliverable — write as you build). Milestones C/D/E pending.
- Deps added to `packing-agent/pyproject.toml`: fastapi, uvicorn, python-dotenv. `uv.lock` committed.
