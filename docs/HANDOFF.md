# Session Handoff — resume point

> Newest entry on top. Read `docs/ADK_SETUP.md` (decisions + "Current build status")
> alongside this. This file is the "where we stopped / what's next" layer.

## 2026-06-28 (PM) — README.md written + verified (20-pt deliverable)

### Situation
Root `README.md` is DONE — the 20-pt deliverable per spec §9. Covers all 8 §9 points: problem,
"it knows you" solution, why-agents, architecture (ASCII diagram + component table), the 4 course
concepts mapped to exact file paths, verified clean-clone setup, §6 privacy/security, and an honest
A–D-done / E-pending status. Bold "no secrets committed" reminder sits near the top. The scaffold's
`packing-agent/README.md` (generic, auto-generated) was left untouched.

### Verified (/verify, no LLM quota burned)
Ran the documented launch verbatim: `cd packing-agent && uv run python -m app.server` → fresh
uvicorn bound to `http://127.0.0.1:8000`, GET `/` → 200 serving the "Trip Packing Agent" UI;
`/static/index.html` → 200. Setup-step source files exist (`profile.example.json`, `.env.example`
at root; targets gitignored). MCP weather server auto-spawns (single command, no 2nd terminal).
Deliberately did NOT drive `/generate` (live Gemini, burns free-tier daily cap) — generate-path
claims rest on the A–D verifications below.

### Decisions / notes
- README lives at REPO ROOT (the deliverable); `cp` sources are root-level, targets are
  `packing-agent/profile.json` + `packing-agent/app/.env` (where `server.py` load_dotenv reads).
- ASCII architecture diagram used instead of an exported image (version-controlled, accurate). Spec
  §9.4 nominally wants an image — a real diagram image is still TODO for README polish + the
  required cover image / Media Gallery.

### Pick up from here
1. **Still pending deliverables:** YouTube video ≤5 min (§10), cover image, Kaggle Writeup (≤2,500
   words, Concierge track), then Submit (not save) before July 6 2026 23:59 PT, team merged.
2. **Milestone E stretch** (only if time): security hardening (§6) → Cloud Run deploy → polish.
3. **Before any live demo/recording:** enable billing on the AI Studio key to kill the free-tier
   daily cap (the recurring live-demo risk). Then drive ONE real `/generate` end-to-end (warm→cold
   destination swap, meds persist) to confirm the generate path — the one thing /verify left unrun.

### Git state
- `main` is ahead of `origin/main` by 5 (incl. this README+HANDOFF commit) — NOT pushed (Oguz to
  decide). `profile.json` + `app/.env` remain gitignored/local, by design.

---

## 2026-06-28 (PM) — Milestone D complete (the merge — the agentic core)

### Situation
D is DONE and verified. `build_packing_list` no longer concatenates the three sources — it
MERGES them with a deterministic dedupe-by-label. The medication is bulletproof. **E (stretch:
security → Cloud Run → polish) is next, but `README.md` (20 pts) is the higher-value gap.**

### Changes (`app/agent.py` only)
- `_normalize_label(label)` — canonical collision key (lowercase + collapse whitespace).
  Intentionally conservative: no stemming/synonyms, so the merge never silently drops a
  distinct item. Near-synonyms ("sunglasses" vs "shades") stay separate by design.
- `_merge_by_precedence(ordered_sources)` — THE merge. Walks sources highest→lowest precedence,
  keeps the FIRST item per normalized label (first-seen-wins). Precedence is encoded purely by
  ORDER — heavily commented, since that's where impl points are won.
- `build_packing_list` assembly rewritten: builds `med_items`, `always_items`, `weather_items`,
  `skill_items` separately, then `items = _merge_by_precedence([profile, weather, skill])`.
  **Precedence: profile > weather > skill.** Meds occupy the FIRST profile slot, so a medication
  is ALWAYS the first occurrence of its label and can never be the copy a collision drops — the
  meds-always guarantee is now STRUCTURAL, not just an append.
- No tool signatures, agent wiring, instruction, or model touched.

### Verified
- Deterministic (no quota): cold + beach real builds have no dup labels & all meds present;
  unit test of `_merge_by_precedence` confirms profile beats weather beats skill on a forced
  3-way "sun hat"/"sunscreen" collision; FORCED-COLLISION test (a med whose label equals a
  weather+skill item) confirms the med survives exactly once as `source=profile,category=health`.
- ONE live generate (quota-aware): Reykjavik leisure → `cold, likely precip, 6-12C` → cold_weather
  items merged, no dup labels, `daily inhaler` survived. ✔

### Pick up from here — README.md, then Milestone E
1. **README.md (20 pts, not yet started)** — write per spec §9; highest-value remaining deliverable.
2. Milestone E stretch (only after README): security hardening (§6) → Cloud Run deploy → polish.
   Don't over-build; spine + B + C + D are solid.
3. Live-demo risk unchanged: enable billing on the AI Studio key before the demo to kill the
   free-tier daily cap.

### Not committed yet
This D work is on disk but NOT committed — waiting on Oguz's go.

---

## 2026-06-28 (PM) — Milestone C complete (trip skills + progressive disclosure)

### Situation
Milestone C is DONE and verified. The agent now picks ONE of two contrasting trip skills and
its items flow into the list — a visible cold↔beach switch. **D (the merge) is next.**

### Changes
- New `packing-agent/skills/cold_weather/SKILL.md` + `.../beach/SKILL.md` — guidance prose +
  a `## Packing items` list, each bullet `- <label> :: <category>`.
- `app/agent.py`:
  - `_parse_skill_items` — deterministic parse of the items list (decision 4: no LLM mis-parse).
  - `_load_skill(name)` — allowlist (`SKILL_NAMES = (cold_weather, beach)`), reads ONLY the one
    chosen `skills/<name>/SKILL.md` (progressive disclosure), returns `{name, guidance, items}`
    or `{error}` (never crashes on bad name / missing file).
  - `select_skill(name)` — new agent-facing tool = the progressive-disclosure surface; returns
    guidance (rationale for the model) + items.
  - `build_packing_list` gained `skill_name`; it re-reads items via `_load_skill` so only the
    short skill *name* is threaded through the model, never the item list. `general toiletries`
    stub removed.
  - Instruction: 3-step → 4-step (get_weather → select_skill → build_packing_list w/ skill_name).
    Rule: `summary in [cold,freezing] → cold_weather`; `hot` OR `purpose==beach` → beach;
    purpose secondary.

### Verified
- Deterministic (no quota): both skills parse; unknown name → graceful no-items; cold build →
  cold_weather items, beach build → beach items; medication in both.
- ONE live generate (quota-aware): Reykjavik leisure → agent chained get_weather → select_skill
  → build_packing_list, loaded cold_weather items, `daily inhaler` survived. ✔

### Pick up from here — Milestone D (the merge, the agentic core)
1. Re-read spec §5.4 + decision 3. The three sources already land in `build_packing_list`'s
   `items` (weather via `_weather_items`, skill via `_load_skill`, profile meds+always_pack).
2. Add the **deterministic dedupe by label** + keep the meds-always rule explicit and HEAVILY
   commented (that's where impl points are won). Watch real overlaps: beach skill vs weather
   both can imply sun items; cold skill vs weather both imply warm layers.
3. Done-when: no duplicate labels in output; every medication still unconditionally present.

### Still not done
- No `README.md` yet (20 pts). E (security hardening → Cloud Run → polish) pending. Free-tier
  daily quota still the live-demo risk — enable billing before the demo (see constraint below).

---

## 2026-06-28 (PM) — B re-verified + hardening + model switch

### What happened
Re-verified Milestone B end-to-end, hit the free-tier quota mid-testing, fixed two
error-handling bugs it surfaced, and switched the model. **B is still DONE; Milestone C is
still next** (pickup steps unchanged — see the entry below).

### Changes (this session)
- **Model `gemini-2.5-flash-lite` → `gemini-2.5-flash`** (`app/agent.py`). flash-lite's
  free-tier **daily** cap is only **20 req/day**
  (`GenerateRequestsPerDayPerProjectPerModel-FreeTier`); a day of testing exhausted it
  (~2–3 model calls per Generate → ~7 clicks burns it). Tested live: `2.0-flash`/`flash-latest`
  were also exhausted that day, `2.5-flash` had headroom and ran the full path cleanly. Decision
  2 in `docs/ADK_SETUP.md` updated with the model history + lesson.
- **Front-end error handling** (`app/static/index.html`): the catch called `res.json()` on the
  error body, but an unhandled 500 returns plain-text "Internal Server Error" → threw
  `Unexpected token 'I'…` that masked the real error. Now reads the body as text and parses JSON
  only when it is JSON, so the real message shows.
- **Server 429 mapping** (`app/server.py`): `/generate` catches `google.genai.errors.ClientError`;
  on `code==429` returns a clean JSON 429 with an honest detail (per-minute cap clears in ~1 min;
  per-day resets at midnight Pacific). Non-429 ClientErrors re-raise (still 500) so real faults
  aren't masked — verified via a TestClient monkeypatch (429 → clean JSON, 400 → 500).

### Known constraint (NOT a bug)
The bottleneck is free-tier **daily** quota, per-project-per-model — `2.5-flash` can also be
exhausted by heavy testing. **Durable fix before the demo: enable billing on the AI Studio key**
(pay-as-you-go; flash ≈ fractions of a cent/request) → removes the daily cap. Not yet done.

---

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
