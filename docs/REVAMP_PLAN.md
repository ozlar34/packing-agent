# Revamp Plan — weather fix · richer lists · visible profile

> **Created 2026-06-29.** Outcome of a full design-tree grilling. Every decision below
> is **locked** — do not re-litigate without an explicit reason. Read this top-to-bottom
> once, then execute phase-by-phase. Each phase has a hard **DONE gate** and ends with a
> `/clear` + a paste-ready prompt for the next phase.
>
> Companion docs: `docs/HANDOFF.md` (session history), `docs/ADK_SETUP.md` (locked
> architecture), `AGENTS.md` (frozen scope + data contracts). This plan honors all three.

## Why this exists (the three complaints)
1. **Wrong weather.** "Bali" returned `12–20C, mild`. Root cause = **two** defects:
   - `_geocode('Bali')` → `(22.64859, 88.34115)` — a village near Kolkata, **India**, not
     Bali, Indonesia (−8.4, 115.2). `count=1` grabs the first name-match.
   - `12–20C, mild` is the **exact neutral fallback** (`weather_server.py:127`): on that run
     `get_weather` threw/returned nothing and the bare `except Exception` silently faked it.
2. **No personalization visible.** Profile is hardcoded (by frozen scope) but nothing in
   the UI shows it's *yours*, so the list reads as generic.
3. **Bare bones.** No universal items, no quantities. User wants toothbrush/toothpaste-class
   basics + "one t-shirt per day", weather-driven bottoms, etc.

## Framing (locked)
**Polish for submission, frozen scope holds.** Single local profile, no auth, JSON store.
Deadline **July 6 2026**. The weather fix is mandatory; #2/#3 are delivered *within* scope
(no editor, no accounts). Keep it runnable end-to-end the whole way (golden rule: one
unproven box at a time).

## Locked decisions
| # | Decision | Locked choice |
|---|---|---|
| Personalization (#2) | UI treatment | **Read-only "Your profile" panel** (meds + always-pack). No editor; `profile.json` stays hand-edited. |
| Richness (#3) | Scope | **Base-essentials catalog + quantity engine.** New `base` source, new `quantity` field. |
| Quantities | Per-day items | tops/underwear/socks = **1×/day, cap 7** + a "plan to do laundry" hint past 7. |
| Quantities | Bottoms | qty **1 if ≤4 days else 2**; label by weather (see catalog). |
| Geocoding (#1) | Disambiguation | **Autocomplete dropdown.** Search-as-you-type; user picks the exact place; free-text submit blocked until a valid pick. |
| Geocoding | Location flow | Dropdown captures **lat/lon + canonical label**; trip payload carries them; `get_weather` takes **optional lat/lon and skips re-geocode** (geocodes only as fallback). |
| Geocoding | Search call site | **Server proxy `GET /geocode?q=`.** UI stays a dumb client (honors the graded "no business logic / no external calls in UI" principle). |
| Weather integrity | Forecast fetch fails | **Honest flag, no fake numbers.** Never present invented mild temps as a real forecast. |
| Item shape | `quantity` field | int, default 1. UI shows `×N` only when N>1 (passport/inhaler stay clean). |
| Merge | Precedence | `profile > weather > skill > base`. Base is the generic floor; meds stay structurally first (unconditional). Quantity rides with the surviving item. |
| UI | New badge | 4th badge **"Basics"** alongside Your essentials / Trip type / weather. |
| Trip contract | Additive only | add `latitude`/`longitude`; items gain `quantity`. `items[]`'s existing keys untouched. |

## The base-essentials catalog (locked)
**Class A — fixed ×1, always included**
- *Toiletries:* toothbrush · toothpaste · deodorant · shampoo (travel size) · soap/body wash · razor · hairbrush/comb · toiletry bag
- *Essentials:* wallet · travel power adapter · power bank · headphones/earbuds · reusable water bottle · **phone charger · passport** (generic fallbacks — dedupe to "Your essentials" when the profile owns them)
- *Health* (generic, sits alongside profile meds, distinct badge): pain reliever · adhesive bandages · hand sanitizer
- *Footwear:* comfortable walking shoes (×1 pair)

**Class B — qty by trip length (1×/day, cap 7)**
- top → `t-shirt` (hot/warm/mild) or `long-sleeve top` (cold/freezing)
- underwear
- socks

**Class C — qty + label by weather**
- bottoms → `shorts` (hot/warm) · `pants` (mild) · `warm pants` (cold/freezing); qty 1 if ≤4 days else 2
- sleepwear → `pajamas` (mild+) or `warm pajamas` (cold/freezing); ×1

Excluded by design (come from weather/skill): sunscreen, sun hat, swimwear, flip-flops,
warm insulated jacket, waterproof jacket/boots.

## Data-contract changes (additive; freeze before coding each phase)
- **Trip input (UI→server→agent):** `{ destination, start_date, end_date, purpose, latitude, longitude }` — lat/lon optional; when present, `get_weather` uses them and skips geocode.
- **Weather (MCP→agent):** `get_weather(destination, start_date, end_date, latitude=None, longitude=None)` → §4.3 plus a `forecast_ok: bool` (false = honest-fail path; UI shows the flag, no fake temps presented as real).
- **Item (agent→UI):** `{ label, source, category, quantity }` — `source ∈ {weather, skill, profile, base}`, `quantity` int ≥ 1.
- **New endpoint:** `GET /geocode?q=<text>` → `{ results: [{ name, admin1, country, latitude, longitude, population }] }` (Open-Meteo passthrough, deduped/ranked for the dropdown).

---

# Execution phases

Each phase: **build → verify the DONE gate → commit → `/clear` → paste the next prompt.**
Verify deterministically where possible; spend **at most one** live `/generate` per phase
(free-tier Gemini daily cap ≈ 20 calls/model — see HANDOFF). Run the server from
`packing-agent/` so `.env` loads. If `.env` is missing, recreate from Keychain:
`cd packing-agent && { printf 'GOOGLE_API_KEY='; get-secret google-api-key; } > .env`.

## Phase 1 — Geocoding dropdown + lat/lon passthrough
**Goal:** typing a place shows a disambiguated dropdown; picking one drives the forecast for
the *right* location. Kills the Bali bug.

**Build**
1. `app/server.py`: add `GET /geocode?q=` → calls Open-Meteo geocoding (`count≈10`), returns
   ranked candidates `{name, admin1, country, latitude, longitude, population}`. Reuse the
   geocode URL/logic from `weather_server.py` (or a shared helper). UI talks only to us.
2. `app/static/index.html`: replace the free-text destination input with a **search-as-you-type
   autocomplete** — debounced (~250ms) fetch to `/geocode`, dropdown listing
   "Name, Admin1, Country". On pick: set the visible label, stash `latitude`/`longitude` in
   hidden fields, mark selection valid. **Block submit until a valid pick** (editing the text
   after picking invalidates it). Keyboard nav + click both work; `aria-` roles for a11y.
3. `app/server.py` `TripInput`: add optional `latitude`/`longitude`; pass through to the agent
   message.
4. `app/agent.py`: thread `latitude`/`longitude` from the trip into the `build_packing_list`
   path is NOT needed yet — they go to `get_weather`. Update the agent instruction so it passes
   lat/lon to `get_weather` when present. (`get_weather` signature change lands in Phase 2; for
   Phase 1 you may stub the params as accepted-but-ignored to keep things runnable, OR do the
   tiny signature add here — your call, but keep ONE unproven box: prefer wiring UI→server here
   and leave the tool's use of lat/lon to Phase 2.)

**DONE gate**
- `GET /geocode?q=Bali` returns Indonesia as a top candidate (verify with `curl`/TestClient).
- In the browser, typing "Bali" shows a dropdown; picking "Bali, Bali, Indonesia" populates
  hidden lat/lon ≈ (−8.4, 115.2); Generate is disabled until a pick.
- Server boots, `/` → 200, no console errors (Playwright or manual).
- **No live `/generate` needed this phase** (pure plumbing) — save the quota.

**End of phase:** commit (`feat(geo): disambiguating place autocomplete + lat/lon passthrough`).
Then **`/clear`** and paste the Phase 2 prompt.

## Phase 2 — `get_weather` uses lat/lon + honest forecast-failure
**Goal:** the forecast is fetched for the picked coordinates; failures are honest, never faked.

**Build**
1. `app/weather_server.py`: `get_weather(destination, start_date, end_date, latitude=None,
   longitude=None)`. If lat/lon present → use directly, **skip `_geocode`**. Else geocode as
   today (fallback for any non-dropdown path).
2. Replace the silent neutral fallback: add `forecast_ok: bool` to the §4.3 return. On a real
   forecast → `true`. On geocode-miss/network/HTTP error → `false` and **do not** emit invented
   `12–20 mild` as if real (either omit temps or clearly mark them an estimate downstream).
   Keep the run from hard-failing, but stop lying.
3. `app/agent.py`: pass `forecast_ok` through `build_packing_list` into the §4.4 return so the
   UI can show the honest flag. Weather-driven quantity logic (Phase 3) should treat
   `forecast_ok=false` as "unknown weather" (neutral, clearly labeled).

**DONE gate**
- Deterministic: `get_weather('Bali', <near dates>, latitude=-8.4, longitude=115.2)` → `hot`,
  ~27–31C, `forecast_ok=true`. With a bogus lat/lon or forced network error → `forecast_ok=false`
  and no fake temps presented as real.
- Out-of-range dates (>16 days) → still produces a sane labeled result (proxy or honest flag),
  not a silent lie.
- **One** live `/generate` (Bali, picked from dropdown) → list reflects hot Bali weather, meds
  persist. Confirm the Bali bug is dead end-to-end.

**End of phase:** commit (`fix(weather): use picked lat/lon, honest forecast-failure flag`).
Then **`/clear`** and paste the Phase 3 prompt.

## Phase 3 — Base-essentials catalog + quantity engine + merge
**Goal:** lists are no longer bare bones — universal items + per-day/weather quantities, merged
with correct precedence, meds still unconditional.

**Build** (`app/agent.py` only)
1. Add `_trip_days(start_date, end_date)` → inclusive day count (same-day = 1).
2. Add `_base_items(summary, days, forecast_ok)` → the locked catalog. Class A fixed ×1; Class B
   `min(days, 7)` with a laundry hint when `days > 7`; Class C qty+label by weather. Every item
   `source="base"`, `quantity` set, correct `category`. When `forecast_ok=false`, pick neutral
   labels (e.g. `pants`, `t-shirt`) and skip weather-only choices.
3. Give existing items a `quantity` (default 1) so the shape is uniform.
4. Merge: extend precedence to `profile > weather > skill > base` (append `base_items` last in
   `_merge_by_precedence`). Confirm meds remain first → unconditional + never deduped away.
5. Surface the laundry hint + `forecast_ok` in the §4.4 return (new fields are additive).

**DONE gate**
- Deterministic build (no quota): a 4-day hot trip → `shorts ×1`, `t-shirt ×4`, `underwear ×4`,
  `socks ×4`, toiletries ×1, walking shoes ×1; a 9-day cold trip → counts cap at 7 + laundry hint,
  `warm pants ×2`, `long-sleeve top ×7`. No duplicate labels. **Every medication present exactly
  once, `source=profile`.** `phone charger`/`passport` dedupe to profile (`source=profile`), not
  base.
- Unit-check `_trip_days` edge cases (same-day, multi-day, >7).
- **At most one** live `/generate` to sanity-check the assembled list.

**End of phase:** commit (`feat(list): base-essentials catalog + quantity engine + 4-source merge`).
Then **`/clear`** and paste the Phase 4 prompt.

## Phase 4 — UI: quantities · Basics badge · profile panel · forecast-fail note
**Goal:** the new data renders cleanly and "it knows you" is visible.

**Build** (`app/static/index.html`; small server route if needed for the profile panel)
1. Render `quantity` as `×N` only when N>1.
2. Add a **"Basics"** badge style for `source="base"` (4th color; keep contrast/a11y).
3. **"Your profile" panel** (read-only): show profile meds + always-pack so the list visibly
   "knows you". Source the data via a small `GET /profile` route returning **non-sensitive
   display data** — confirm it's fine to surface med *names* in the user's own local UI (it is
   local-only per §6.4; the *external* boundary is what's protected). Keep the Vibe Diff line.
4. Show the **honest forecast-fail note** when `forecast_ok=false` (e.g. "couldn't fetch a live
   forecast for these dates — packed a neutral baseline").
5. Surface the **laundry hint** when present.

**DONE gate**
- Browser (Playwright vs live server): quantities show correctly, Basics badge renders, profile
  panel shows meds + always-pack, 0 console/page errors.
- A forced `forecast_ok=false` run shows the honest note, no fake temps.
- Re-confirm the Vibe Diff still names meds **by count only** in the privacy line (no med name in
  the *generated list text*; the profile panel showing them locally is fine).

**End of phase:** commit (`feat(ui): quantities, Basics badge, read-only profile panel, fail note`).
Then **`/clear`** and paste the Phase 5 prompt.

## Phase 5 — Full live verify + docs + ship
**Goal:** prove the whole revamp end-to-end and update the deliverables.

**Build/verify**
1. One clean live run from a fresh dropdown pick (Bali) → right weather, rich quantified list,
   meds persist, profile panel + Vibe Diff + Basics badge all present. Screenshot.
2. A contrasting run (a cold city) → bottoms/top labels flip, cap/laundry behavior correct.
3. Update `README.md` + `docs/KAGGLE_WRITEUP.md` where the revamp changes the story (geocoding
   disambiguation, base catalog, quantities, honest weather). Refresh `docs/HANDOFF.md` top entry.
4. Push `main`.

**DONE gate**
- Two live runs green; docs reflect reality; repo clean-cloneable; `main` pushed.
- Then the only remaining deliverables are external: **YouTube video ≤5 min** + **Kaggle Submit
  (not Save), team merged**, before July 6 2026 23:59 PT.

---

## Risk / watch-list
- **Free-tier Gemini daily cap** (~20 calls/model). Budget ≤1 live `/generate` per phase; enable
  billing on the AI Studio key before recording the video.
- **One unproven box at a time.** If a phase feels like it's touching two unproven things, split
  it. A working fake beats a broken real.
- **Don't weaken the privacy story.** Profile panel surfaces meds *locally only*; the external
  weather boundary still gets just location + dates; the Vibe Diff still counts, never names.
- **Contracts are additive only.** Never break existing `items[]` keys or the §4.4 shape.
</content>
</invoke>
