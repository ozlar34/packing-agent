# Session Handoff — resume point

> Newest entry on top. Read `docs/ADK_SETUP.md` (decisions + "Current build status")
> alongside this. This file is the "where we stopped / what's next" layer.

## 2026-06-29 (later) — REVAMP COMPLETE (Phases 1–5): geocoding fix · quantities · profile panel · docs · ship

### What this session did (Phase 5 of `docs/REVAMP_PLAN.md` — the final verify+docs+ship phase)
Phases 1–4 of the revamp were already built+committed (4 commits ahead of origin at session start:
geo autocomplete, honest weather, base catalog/quantity engine, UI). This session executed **Phase 5**:
- **Deterministic verify (no quota):** hot 4-day → `t-shirt ×4, shorts, underwear/socks ×4`; cold
  9-day → caps at 7 + laundry hint, `long-sleeve top ×7, warm pants ×2`. No dup labels, med present
  exactly once `source=profile`, `phone charger`/`passport` dedupe to profile (not base). `_trip_days`
  edges correct (same-day=1).
- **Weather path verify (keyless, no Gemini quota):** `forecast_ok` honest (True for real, False+no
  temps for bogus lat/lon). NOTE: the `_geocode('Bali')` *fallback* still returns the Kolkata village
  (22.6, 88.3) — **by design** the dropdown passes lat/lon so `get_weather` skips geocode. `/geocode?q=Bali`
  returns "Bali, Indonesia" (pop 4.2M) as a clear candidate. Bug is dead via the dropdown path.
- **2 LIVE `/generate` runs GREEN:** Bali Indonesia (−8.33,115.0) → `warm, 17–24C`, 33 items, med
  persists, 4-source merge. Reykjavík (64.1,−21.9) → `cold, 6–12C`, long-sleeve ×7 / warm pants ×2 /
  laundry hint. Contrast = the money moment.
- **2 browser screenshots (Playwright vs live server, 0 console errors)** saved to
  `docs/assets/demo-bali.png` + `docs/assets/demo-reykjavik.png` — embedded in README. Confirmed all
  4 badges (Your essentials/Weather/Trip type/**Basics**), quantities `×N`, profile panel, honest
  forecast line, laundry hint.
- **Docs updated to match the revamp:** `README.md` (four-source merge + quantity engine, geocoding
  disambiguation, honest forecast flag, profile panel, screenshots, money demo) and
  `docs/KAGGLE_WRITEUP.md` (four-source merge section, revamp milestone — ~2,350 words, under 2,500).

### Live-run nuance worth knowing for the video
Open-Meteo's "Bali, Indonesia" centroid (−8.33, 115.0) lands in Bali's central **highlands**, so the
honest forecast is `warm, 17–24C`, not tropical-coast `hot, 27–31C`. Still produces a coherent warm
list (t-shirts/shorts). If a more obviously *hot* contrast is wanted for the video, pick a coastal hot
city (e.g. Dubai, Phuket town) — Oguz's call, not changed here.

### Pick up from here — only EXTERNAL deliverables remain (no code/docs left)
1. **Commit + push** this session's work (docs + screenshots) — see below; then `main` is clean & current.
2. **Record YouTube video ≤5 min** (Oguz). Enable billing on the AI Studio key first to kill the
   free-tier daily cap mid-recording (~20 calls/model/day).
3. **Submit on Kaggle** (Oguz): project link + Writeup, Concierge track, **merge team**, **Submit (not Save)**
   before July 6 2026 23:59 PT.
4. **Optional bonus:** Cloud Run deploy (deferred — needs interactive gcloud auth + billing).

---

## 2026-06-29 — UI redesign shipped + committed + pushed + LIVE verify GREEN

### Done this session (commits `1debaaa` + `d5ae612`, **both pushed**; `main` in sync with origin)
- **Committed the full 5-phase UI redesign** (`1debaaa`): bright flat-travel reskin of the single
  self-contained `packing-agent/app/static/index.html` + the plan doc `docs/UI_REDESIGN_PLAN.md`
  (all 5 phases were already built/verified in prior sessions — this session committed them).
  `/generate` contract + response shape untouched.
- **Tooling hygiene** (`d5ae612`): gitignored the Impeccable dev artifacts
  (`.agent/skills/impeccable/`, `.impeccable/`) so the clean-clone surface stays minimal; added
  `.filesizeignore` exempting `index.html` from the size tripwire (spec mandates one self-contained
  file, can't be split). Working tree clean.
- **LIVE end-to-end re-verify — GREEN (quota was healthy, not exhausted).** Prior sessions only ever
  tested the redesign with a *replayed* payload; this session ran the **real agent**:
  - Ran `cd packing-agent && uv run python -m app.server` (127.0.0.1:8000) with the key loaded.
  - **Money demo proven:** Reykjavik `cold, 8-13C` (13 items) vs Dubai `hot, 29-45C` (12 items) →
    forecast differs → list differs (9 cold-only / 8 hot-only / 4 shared). Destination→forecast→list.
  - **"It knows you":** profile medication present in BOTH lists regardless of trip type.
  - **Real-browser pass (Playwright vs live server, no interception):** 13 items + 13 sticker badges,
    **0 console/page errors**, Vibe Diff renders from the real `privacy_note` (eyebrows on own lines —
    Phase 5 fix confirmed; meds counted not named). Screenshot at scratchpad `live_ui.png` (ephemeral).
- **README/Writeup freshness check:** nothing stale — no UI screenshots are embedded anywhere; both
  docs describe the UI functionally, so the redesign invalidates no wording. Only image in repo is
  `architecture.png` (flow diagram / cover, still accurate).

### Key/secret setup (important for next live run)
- The Gemini key now lives in **macOS Keychain as secret `google-api-key`** (added via `add-secret`).
- `packing-agent/.env` was written this session as `GOOGLE_API_KEY=<from get-secret google-api-key>`
  (gitignored, 69 bytes). If `.env` is missing in a future session, recreate it from the Keychain:
  `cd packing-agent && { printf 'GOOGLE_API_KEY='; get-secret google-api-key; } > .env`
  (the secret-exposure hook blocks reading the value into chat, but writing to a gitignored `.env`
  is fine). Run the server FROM `packing-agent/` so it loads that `.env`.

### Pick up from here — critical path is now SHORT (all code/docs done; only platform actions remain)
1. **Record the YouTube video ≤5 min** (Oguz — physical-world action). UI is demo-ready. Best to enable
   billing on the AI Studio key first to kill the free-tier daily cap mid-recording (~20 calls/model/day).
2. **Submit on Kaggle** (Oguz — no tool for the web UI): paste project link + Writeup, select Concierge
   track, **merge team**, click **Submit (not Save)** before July 6 2026 23:59 PT.
3. **Optional (offered, not done):** drop scratchpad `live_ui.png` into the README under the intro to
   strengthen the 20-pt README (held off — "don't rewrite prose unasked"). Re-screenshot if wanted.
4. **Optional bonus:** Cloud Run deploy (still deferred — needs interactive gcloud auth + billing).

### Preview the app (quick reference)
```
cd /Users/oguzoral/Desktop/ai-travel-packing-agent/packing-agent
uv run python -m app.server        # wait for "Uvicorn running on http://127.0.0.1:8000"
# open http://127.0.0.1:8000 ; pick dates within ~16 days (Open-Meteo forecast limit) ; Generate
# Ctrl+C to stop. Port busy? lsof -nP -iTCP:8000 -sTCP:LISTEN then kill <PID>
```

---

## 2026-06-28 (later) — Milestone E (parts 1–3) done: Vibe Diff + logging audit + checkbox UI

### Done this session (commit `adb1cde`, NOT yet pushed)
- **§6.5 "Vibe Diff" privacy line (part 1, highest value).** `_privacy_note()` in `agent.py`
  derives a deterministic plain-English note inside `build_packing_list` — what crossed the tool
  boundary (destination + dates) vs. what stayed local (meds + always-pack, named **by count only**
  so no medication name appears in output text). Added as a new `privacy_note` field on the §4.4
  return (`items[]` untouched — contract holds). Rendered on screen in `index.html` as a 🔒 banner.
- **§6.3 logging audit (part 2).** Audited all demo code paths: `server.py` → `agent.py` →
  `weather_server.py` emit **zero logging** — nothing sensitive can leak. The only logging in the
  repo is the scaffold's Cloud Run entrypoint (`fast_api_app.py`/`telemetry.py`), which the demo
  doesn't import and which defaults prompt capture to `NO_CONTENT`. Conclusion: clean by
  construction → documented in README (no dead redaction helper added — nothing logs profile data).
- **UI polish (part 3).** Real checkboxes per item; check state persisted per-destination in
  `localStorage` (survives re-generate/reload); strike-through when done. Color-by-source tags
  already existed. README "Privacy & security" + "Project status" updated; E marked ✅.
- **Verified deterministically (no LLM quota):** imports clean; server boots → `/` 200; both skills
  (cold/beach) build with no dup labels, all meds present, `privacy_note` populated, no med-name
  leak in the note. Did NOT drive a live `/generate` (saves free-tier daily cap).

### Pick up from here
1. **Part 4 — Cloud Run deploy (BONUS, not required for judging).** Handoff to Oguz for interactive
   `! gcloud auth login` + **enable billing**; then `agents-cli deploy` via the scaffold's
   `fast_api_app.py` (see steps in the older entry below). Optional.
2. **Push `main`** (this E commit is local-only) when ready.
3. **Remaining deliverables (platform/external):** YouTube video ≤5 min, paste Kaggle Writeup +
   select Concierge track, **Submit (not save)** before July 6 2026 23:59 PT, team merged.
4. **Before recording:** enable billing on the AI Studio key to kill the free-tier daily cap, then
   drive ONE real `/generate` (warm→cold swap, meds persist, Vibe Diff line shows). The one path
   `/verify` still hasn't exercised live.

---

## 2026-06-28 (late PM) — pushed + cover image/diagram + Kaggle Writeup draft

### Done this session
- **Pushed `main` to `origin/main`.** Repo is now public/clean-cloneable for judges; origin
  is current through this session's commits.
- **Architecture diagram image (spec §9.4) — `docs/assets/architecture.{svg,png}`.** A
  version-controlled SVG source rendered to a 1600x900 PNG via Chrome headless. It is accurate to
  the actual code (agent.py / weather_server.py / skills) and **doubles as the required Media
  Gallery cover image** (16:9, branded title card + flow). The README's ASCII diagram was replaced
  by an embed of this PNG (component table + request-flow line retained). Commit `4a05eed`.
  - To re-render after editing the SVG: `cd docs/assets && "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu --screenshot=architecture.png --window-size=1600,900 "file://$PWD/architecture.svg"`
- **Kaggle Writeup draft — `docs/KAGGLE_WRITEUP.md`.** Paste-ready, Concierge track, title +
  subtitle, ~2,080 words (well under the 2,500 limit). Covers problem, solution, why-agents,
  architecture, the 4 concepts, the deterministic merge, the privacy boundary, and the build
  journey. Commit `437ab2b`. **Not yet pasted/submitted on the Kaggle platform** — that's a
  platform action for Oguz.

### Pick up from here — Milestone E (Oguz wants ALL four; do next session)
Spine + A–D + README + diagram + writeup are solid, so E is the remaining build work. Order by
value (do top-down; first two are fully doable locally, no external accounts):
1. **§6.5 Privacy summary line ("Vibe Diff") — HIGHEST value, do first.** Have the agent/UI show a
   plain-English note before/with the list, e.g. *"Used your destination and dates for weather;
   kept your medications local and added them to your list privately."* Makes the 4th concept
   (security) visible on screen and is great for the video. Cleanest spot: derive it
   deterministically in `build_packing_list` (it knows what crossed the tool boundary vs. what came
   from profile) and add a field to the §4.4 return, then render it in `app/static/index.html`.
   Watch the data contract: adding a field to the agent→UI shape is fine, but keep `items[]` intact.
2. **§6.3 Logging audit + redaction.** Grep all code paths (`app/server.py`, `app/agent.py`,
   `app/weather_server.py`) for any logging that could touch the profile/medications. Add a small
   redaction helper that replaces medication strings with `[[MEDICATION]]` if anything logs profile
   data; otherwise document that nothing sensitive is logged. Mostly an audit — likely already clean.
3. **UI polish.** Checkbox state persistence, cleaner styling, color-code items by `source`
   (profile/weather/skill) so "it knows you" reads at a glance. Lowest-priority per spec §5.5.
4. **Cloud Run deploy (bonus, NOT required for judging).** Needs: a GCP project, **billing
   enabled**, and **interactive `gcloud auth`** (Oguz runs the auth step — `! gcloud auth login`).
   The scaffold's `app/fast_api_app.py` (kept since Milestone A, GCP-coupled) is the deploy
   entrypoint; our local `app/server.py` stays for local dev. Use `agents-cli deploy` /
   `scaffold enhance` (see `packing-agent/AGENTS.md`). Document reproduction steps in the README.

### Still-pending deliverables (mostly external/platform)
- **YouTube video ≤5 min** (spec §10, worth 10 pts) — script + record. Cover: problem, why-agents,
  architecture (show `docs/assets/architecture.png` on screen), the money demo (warm→cold swap,
  meds persist, one skill switch), the build + privacy (§6.1 + §6.3).
- **Cover image** — DONE: use `docs/assets/architecture.png` for the Media Gallery.
- **Kaggle Writeup** — DRAFTED (`docs/KAGGLE_WRITEUP.md`); paste into the platform + select Concierge.
- **Submit (not save)** before **July 6 2026 23:59 PT**, **team merged** on the platform.

### Live-demo gate (unchanged, blocks the video)
Before recording: **enable billing on the AI Studio key** to kill the free-tier daily cap, then
drive ONE real `/generate` end-to-end (warm→cold destination swap, confirm meds persist) — the one
path `/verify` has left unrun. Per-day free cap = ~3 model calls/Generate.

### Paste-ready resume prompt (next session)
> Read `docs/HANDOFF.md` (top entry) and `AGENTS.md` first. Status: A–D + README + architecture
> diagram/cover image + Kaggle Writeup draft all done, committed, and pushed to origin. Now build
> **Milestone E** — all four parts, in value order: (1) §6.5 privacy-summary line, (2) §6.3 logging
> audit + redaction, (3) UI polish, (4) Cloud Run deploy (bonus; I'll run `gcloud auth` and enable
> billing — that part's a handoff). Keep it runnable end-to-end; one stub at a time. The §4.4
> agent→UI contract may gain a privacy-summary field but `items[]` stays intact. App runs via
> `cd packing-agent && uv run python -m app.server` → http://127.0.0.1:8000.

---

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
