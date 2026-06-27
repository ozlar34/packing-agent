# ADK Setup & Decisions — read this first in any new session

This is the persistent build memory for the packing-list agent. It records (1) the ADK
tooling wired into this repo, (2) the architecture decisions already locked, and (3) the
ADK-specific build path. Product spec lives in `PACKING_AGENT_SPEC.md`; this file is the
*how we're actually building it* layer on top.

## Source of truth for ADK knowledge (don't guess from memory)
ADK moves fast. Two always-current sources are wired into this repo — use them instead of
training memory:

1. **ADK docs MCP server** (`.mcp.json`, project-scoped → shared via repo). Gives the assistant
   Code live, auto-updated ADK docs from `https://adk.dev/llms.txt`. Activates after a
   the agent CLI reload (project MCP servers require approval on next session start).
2. **Google Agents CLI skills** in `.agent/skills/google-agents-cli-*` (7 skills, authored
   by Google, Apache-2.0). Invoke the relevant one before writing ADK code:
   - `google-agents-cli-workflow` — dev lifecycle + coding rules (**activate first**)
   - `google-agents-cli-scaffold` — `agents-cli scaffold create/enhance` (project creation)
   - `google-agents-cli-adk-code` — Agent/tool/callback/state API patterns + cheatsheets
   - `google-agents-cli-eval` — evaluation loop
   - `google-agents-cli-deploy` / `-publish` — Cloud Run / GKE / Gemini Enterprise
   - `google-agents-cli-observability` — trace/logging

Both came from https://adk.dev/tutorials/coding-with-ai/.

## Tooling installed
- `agents-cli` — installed as a uv tool, on PATH at `~/.local/bin/agents-cli`
  (reinstall: `uv tool install google-agents-cli`). Workspace-scoped skill install was used
  so the ADK skills DON'T pollute global the assistant context.
- `uv` 0.10.10, Python 3.12.3, Node 22, `npx` — all present.
- `skills-lock.json` pins the installed skill versions (committed).

## Locked architecture decisions (from the design grill — do not re-litigate)
1. **Language/runtime:** Python end-to-end. FastAPI (or Flask) serves ONE static HTML/JS
   page; no front-end build step. Both teammates know Python.
2. **Model:** `gemini-2.5-flash` (alias `gemini-flash-latest`) via **Google AI Studio API
   key** (`GOOGLE_API_KEY` in gitignored `.env`). NOT Vertex — stay on the AI Studio key
   even after deploy. Constraint: maximize use of Google products.
3. **Orchestration model = LLM-orchestrated, tools deterministic.** Gemini genuinely drives:
   function-calling decides to call `get_weather`, reads the `summary`, chooses the skill.
   The **merge + the "medications always included" rule are deterministic, heavily-commented
   Python tools** the agent invokes — so the safety-critical part never depends on the model
   behaving. This satisfies both "visible agentic reasoning" (judges reward it) and the
   spec's "explicit commented merge".
4. **Skills = authored `SKILL.md` folders, loaded on demand.** Two contrasting trip
   archetypes (`skills/beach/`, `skills/cold_weather/`), each a `SKILL.md` with packing
   guidance + items. `select_skill(name)` reads ONLY the chosen folder (= progressive
   disclosure, demoable). Items are parsed **deterministically** (no LLM mis-parse); the
   `SKILL.md` prose is also surfaced to Gemini as rationale context. Selection rule: simplest
   first — `summary in [cold, freezing] → cold_weather`; `hot`/`beach` → beach; `purpose` is
   a secondary hint.
5. **MCP transport = stdio.** ADK's `MCPToolset` spawns `weather_server.py` as a subprocess
   (no port, no second terminal). Whole app = ONE launch command. Protects clean-clone
   reproducibility (20 doc points).
6. **Topology:**
   ```
   python app.py
     └─ FastAPI (serves index.html + POST /generate)
          └─ ADK agent (gemini-2.5-flash, AI Studio key)
               ├─ MCPToolset → spawns weather_server.py (stdio)  [Open-Meteo, keyless]
               ├─ select_skill tool → reads skills/<x>/SKILL.md
               └─ merge tool (deterministic: dedupe by label + meds-always)
   ```
7. **Deploy = local-first, then Cloud Run as the FIRST stretch** (not "if time allows") —
   single container (FastAPI + agent + stdio MCP subprocess in one image). Gemini key as a
   Cloud Run secret/env var, never in the image. Reason: live URL is the strongest "public
   project link"; Cloud Run is a Google product.

## Data contracts (frozen — see spec §4 for full shapes)
Trip input `{destination, start_date, end_date, purpose}` · Profile
`{medications[], always_pack[], preferences{}}` · Weather `{..., summary∈{hot,warm,mild,cold,
freezing}, conditions[]}` · Final `{trip, weather_summary, items[]}` where each item has
`source∈{weather,skill,profile}` (keep `source` — it makes reasoning legible).

## ADK build path (revised now that we have the real tooling)
The grill's Milestone A "hand-roll an ADK stub" is superseded by the scaffold tool:
1. **Scaffold:** `agents-cli scaffold create <name>` (via `google-agents-cli-scaffold` skill)
   to generate a correct ADK project skeleton — don't hand-write boilerplate.
2. Then follow spec Milestones A→E behind the frozen §4 contracts:
   - A: spine (form → agent → hardcoded §4.4 list incl. a profile/medication item)
   - B: MCP weather (stub `get_weather` over stdio → real Open-Meteo)
   - C: two trip skills + `select_skill` selection rule
   - D: deterministic merge (dedupe + meds-always) — the agentic core, heavily commented
   - E stretch: security hardening (§6) → Cloud Run deploy → polish
3. **Golden rule:** keep it runnable end-to-end; replace ONE stub at a time.
4. **Eval (optional, Google bonus):** `agents-cli eval` exists — a few eval cases would be
   "clever tool use" evidence for the writeup if time allows.

## Auth note
Agents CLI `setup` ran with `--skip-auth`. When we deploy (or want `agents-cli login`):
`agents-cli login` supports AI Studio or GCP. For local dev all we need is `GOOGLE_API_KEY`
in `.env`.

## Work split (two people, via the agent CLI on this shared repo)
Phase 1 together: learn ADK + stand up the real agent skeleton (scaffold + one real tool
call returning §4.4). Then: Person A = MCP server + merge + Cloud Run; Person B = the two
skills + profile + README/video/cover/writeup (continuously, not at the end — that's 50 pts).

## Current build status (update as milestones land)
- **Milestone A — DONE** (commit `8065f0f`). Hardcoded spine works end-to-end:
  form → ADK agent (gemini-2.5-flash, AI Studio key) → §4.4 list with the profile
  medication. Layout: the ADK project lives in the **`packing-agent/`** subdir.
  - `packing-agent/app/agent.py` — `build_packing_list` deterministic tool (source of
    truth; meds + always_pack added unconditionally) + `root_agent` that calls it.
    Weather + skill items are **stubs** (two placeholder items) to be replaced in B/C.
  - `packing-agent/app/server.py` — **our** GCP-free local entrypoint (decision 6):
    serves the form + `POST /generate`, returns the §4.4 list extracted from the tool's
    `function_response` (not model prose). Run: `cd packing-agent && uv run python -m app.server`
    → http://127.0.0.1:8000.
  - The scaffold's `packing-agent/app/fast_api_app.py` is **GCP-coupled** (calls
    `google.auth.default()` + Cloud Logging at import) — left untouched for the Cloud Run
    stretch (E). Don't use it for local dev; use `app/server.py`.
  - Clean-clone setup: `cp profile.example.json packing-agent/profile.json` (gitignored),
    then put a real AI Studio key in `packing-agent/app/.env` (`GOOGLE_API_KEY`, gitignored).
- **Milestone B — NEXT.** Stub `get_weather` over **stdio MCP** (`MCPToolset`, decision 5),
  wire the agent to call it, then swap in real Open-Meteo. Replace the weather stub item in
  `build_packing_list`. One stub at a time (golden rule).
