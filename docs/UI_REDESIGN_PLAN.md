# UI Redesign Plan — Trip Packing Agent

Bright, friendly-modern, flat-travel redesign of the web UI. Built in 5 phases,
each a single `/clear`-able session. **Every phase ends by printing the
paste-ready kickoff prompt for the next phase** (also stored at the bottom of
this file under "Resume prompts").

> **Status tracker** — update as you go:
> - [x] Phase 1 — Shell & identity ✅ (light-only mint tokens, Fredoka+Inter, hero band w/ dashed route + static plane & balloon; verified desktop render)
> - [x] Phase 2 — Form card ✅ (white card + inset mint fields + paired date frame + teal-tinted segmented purpose were already in from Phase 1; turned the Generate button mustard `--action` w/ dark `--action-ink` text, hover `--action-dk`, teal focus ring; verified desktop render)
> - [x] Phase 3 — Results & list ✅ (hero/toolbar/filters/groups/rows + plain badges already carried the new tokens from earlier phases; no index.html edits needed. **Verified against the running server** by replaying a real captured /generate payload — daily Gemini quota was exhausted, so the genuine response was intercepted to exercise the results UI: bright snow-blue weather hero w/ Fredoka place name, count pill, source-colored filter chips with active tinted state, uppercase category groups + hairlines, white teal-checkbox rows, plain source badges. Confirmed filtering (skill→7 items), grouping (CATEGORY_ORDER), and localStorage persistence (check 2 → reload+regenerate → still 2 packed). No console errors; mobile 360px clean. **Phase 5 follow-up:** privacy panel labels run into the text ("SENT OUTSent only…") — `.ch` needs trailing spacing; that panel is Phase 5's scope.)
> - [x] Phase 4 — Signature touches ✅ (all three ownable moments shipped in `index.html`. **① Sticker badges:** `.badge` is now a die-cut sticker — solid source-color fill, white 2px border, `--sticker-shadow`, per-item tilt via `--rot` (`STICKER_ROT [-4,3,-2,4,-3,2]` set on each `li` in `itemRow`, inherited by the badge), white text; hover straightens + scales 1.07. **② Flight track:** `showLoading` prepends a `.flight-track` (coral start dot → teal line that draws itself along a dashed rail → coral paper plane flying L→R → teal map pin). New `iconPlane()`/`iconPin()` helpers. Doubles as the loading affordance. **③ Passport stamp:** `.stamp` "Packed" (Fredoka, skill-green, double border, rotated −8°) added per row between label and badge, `display:none` until `.done`, then `stamp-in` thunks scale 1.7→1. **All three respect `prefers-reduced-motion`:** badges go flat + transitionless, the flight line shows fully-drawn with the plane parked at the pin (no animation), stamps appear without the thunk. **Verified** via Playwright over an http-served copy of the real `index.html` with `/generate` intercepted to replay a captured Reykjavik payload (Gemini quota exhausted — no live agent call). Probed computed styles in both normal + reduced-motion: badge fill `#c0392b`/white text/2px white border/rotated (vs `transform:none` under RM); 13 stickers + 13 stamps; checking 2 rows → stamps show green+rotated, pill reads "2 of 13 packed"; loading fill mid-draw 401px + plane mid-flight (normal) vs full 644px + plane at end (RM). **No console/page errors.** Harness in scratchpad: `shot.mjs` + `payload.json`. **Note for Phase 5 (already on its list):** privacy panel still shows the run-together "SENT OUTSent only…" label — `.ch` needs trailing spacing.)
> - [x] Phase 5 — States, privacy & Impeccable audit ✅ (**Privacy Vibe Diff fixed:** `.ch` eyebrow is now `display:flex` (own line) with body wrapped in `.cbody`, so it reads "SENT OUT ⏎ Sent only…" instead of the run-together "SENT OUTSent only…"; columns now carry subtle `--weather-soft`/`--skill-soft` tints so the split reads at a glance. **States** (empty/skeleton/error) already carried the new palette from Phases 1–4 — verified all three render on-brand. **Impeccable audit** (`npx impeccable install` → detector): flagged (a) **bounce/elastic easing** on the passport-stamp → swapped `cubic-bezier(.18,.9,.32,1.25)` for ease-out-quint `cubic-bezier(.22,1,.36,1)` (keeps the "thunk", drops the dated overshoot); (b) **overused font Inter** → kept as a *defended locked decision* (Inter is body/UI only, Fredoka display carries personality — a proper contrast-axis pairing; recorded a narrow `ignore-value overused-font=inter` in `.impeccable/config.json`). Detector now exits clean. **Own contrast audit (WCAG AA):** sticker-badge white text failed on skill-green (3.42) and weather-blue (4.30) → deepened *only the sticker fill* via `color-mix(var(--c) 85%, #000)` (all three now ≥4.58; pure source tokens still used by legend dots/chips/filters so docs' red/blue/green stay exact); darkened `--ink-3` #8a9794→#677470 (counts/hints/placeholder now ≥4.5 on both light grounds). **Real bug caught + fixed in QA:** the custom checkbox's `.box` overlay swallowed mouse clicks (only keyboard Space worked) — added `pointer-events:none` so clicks fall through to the input; verified real mouse click + keyboard Space both toggle → done + strikethrough + stamp + localStorage persist. **Full QA green:** single file; `/generate` contract + response shape untouched; localStorage persistence; robust error parse (verified error card); `esc()` intact; a11y (labels, `aria-live=polite` status, focus rings, keyboard toggle, filter `aria-pressed`); `prefers-reduced-motion` (stamp shows w/o thunk, flight line static); mobile 360 + desktop both clean; **no console/page errors.** Verified via Playwright over an http-served copy of the real `index.html` with `/generate` replaying a captured Reykjavik payload (Gemini quota exhausted). Harness recreated in scratchpad: `shot.mjs` + `payload.json`.)

---

## Locked design spec (decided via /grill-me — do not re-litigate)

| Decision | Choice |
|---|---|
| **Identity** | Bright, friendly-modern, flat-travel vibe (see reference image) |
| **Illustration** | Bright palette + accent icons + dotted route line — **not** a full scene, **not** a big illustrated suitcase |
| **Palette** | Mint/cream ground · **mustard** buttons · **teal** focus ring · badges keep **red/blue/green** semantics |
| **Theme** | **Light-only** — drop dark mode entirely (`color-scheme: light`) |
| **Type** | Rounded **display** (Fredoka) for wordmark/headings + clean **sans** (Inter) for body/UI |
| **Layout** | Single column + decorated mint **hero band** at top (dashed route line + a couple of *static* flat icons — **no floating/drifting animation**) |
| **Signatures** | ① Sticker-style source badges ② Dotted route line that animates on Generate ③ Passport-stamp feedback on check |

### Reference + source files
- **Reference image:** `/Users/oguzoral/Downloads/WhatsApp Image 2026-06-28 at 23.52.34.jpeg`
  (flat travel scene: mint ground, coral suitcase covered in stickers, mustard accents, hot-air balloon, dotted route lines, flat icons)
- **Target file (the real app, git-tracked, revertible):** `packing-agent/app/static/index.html`
- **Good JS base to reskin:** `/Users/oguzoral/Desktop/index.html` — a the assistant Design pass.
  Its *look* was rejected as bland, but its **JS structure is solid and worth keeping**:
  per-state rendering (empty / skeleton / error / result), source filter chips,
  category grouping, count pill, privacy "Vibe Diff" split panel, custom checkboxes.
  **Phase 1 step 1 is to copy this file into the repo target as the working base, confirm it runs, then reskin.**

### Hard constraints — never break these
1. **Stay one self-contained `index.html`** (inline `<style>` + `<script>`). No build step, no framework, no bundler. Served as a static file by the ADK/FastAPI backend.
2. **Network contract unchanged:** on submit, `POST /generate` with JSON `{ destination, start_date, end_date, purpose }` (dates ISO `YYYY-MM-DD`; `purpose ∈ leisure|business|beach|outdoors`).
3. **Response shape unchanged:** `{ trip{destination,...}, weather_summary, privacy_note, items[] }`, each item `{ label, source, category }`, `source ∈ profile|weather|skill`.
4. **Keep `source` visible on every item** — it's the product's "why is this on my list" story. Sticker badges carry it.
5. **Preserve behaviors:** per-item checkbox + strikethrough; check-state persisted in `localStorage` keyed `packed:${destination}`; "Thinking…" loading; robust error parsing (read body as text, try `JSON.parse(...).detail`, fall back to `statusText`); render `privacy_note` in the Vibe Diff panel; never inject error text as HTML (use `textContent` / `esc()`).
6. **Accessibility:** real `<label>`s tied to inputs, visible focus states, `aria-live` on results/status region, keyboard-operable controls, `prefers-reduced-motion` fallback for every animation.
7. **Offline-tolerant assets:** inline SVG only for icons; at most one Google Fonts `<link>` with a system-font fallback stack.

### Palette tokens (light-only) — target values, tune to taste
```
--bg:        #eaf5ef;   /* soft mint page ground            */
--surface:   #ffffff;   /* cards                             */
--surface-2: #f1f8f4;   /* inset fields                      */
--ink:       #1d2b2b;   /* near-black, slightly cool         */
--ink-2:     #52605d;   /* muted text                        */
--ink-3:     #8a9794;   /* faint text / hints                */
--line:      #dce9e3;   /* borders                           */
--line-2:    #e7f0eb;   /* faint dividers                    */

--action:    #f4b32f;   /* mustard button bg                 */
--action-ink:#3a2c0c;   /* dark text ON mustard (contrast)   */
--action-dk: #e0a31f;   /* mustard hover/active              */
--teal:      #13a394;   /* focus ring + secondary accent     */
--teal-dk:   #0c7a6f;
--coral:     #ef6e5b;   /* DECORATIVE only (illustrations)   */

/* semantic source colors — KEEP these hues (in docs/screenshots) */
--profile:   #c0392b;   --profile-soft: #c0392b1a;
--weather:   #2980b9;   --weather-soft: #2980b91a;
--skill:     #2e9e54;   --skill-soft:   #2e9e541a;

--shadow:        0 1px 2px rgba(20,50,40,.05), 0 8px 24px rgba(20,50,40,.08);
--shadow-sm:     0 1px 2px rgba(20,50,40,.07);
--sticker-shadow:0 2px 5px rgba(20,40,35,.18);
--radius: 20px;  --radius-sm: 13px;
```
> Note: `--coral` is decorative (balloon, plane, route). It must **not** be used as a source color — `profile` stays its own red so the three badges read as distinct.

### Fonts
```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Fredoka:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
```
- Display (wordmark, h1/h2/h3, section heads, stamp): `"Fredoka", system-ui, sans-serif`
- Body / UI / labels / list: `"Inter", system-ui, sans-serif`

### How to verify each phase
Run the app and look in a browser. Use the project's run path:
```
cd packing-agent && agents-cli playground   # or the documented run command
```
If the server isn't easily runnable in-session, open `packing-agent/app/static/index.html`
directly in a browser to check layout/styling (the `/generate` fetch will fail offline —
that's expected; it exercises the error state, which is fine for visual review of the form/header).
Prefer the real server when generating a list to review results/badges/stamps.

---

## Phase 1 — Shell & identity

**Goal:** establish the bright world. After this, the page background, fonts, and
header read as the new direction; everything below inherits the new tokens and
still functions (unstyled-but-working is OK for form/results this phase).

**Steps:**
1. Copy `/Users/oguzoral/Desktop/index.html` → `packing-agent/app/static/index.html` (the working JS base). Confirm it still loads and the form submits (or hits the error state offline).
2. Swap the font `<link>` to Fredoka + Inter.
3. Replace the `:root` token block with the **light-only** palette above; delete the `@media (prefers-color-scheme: dark)` block; set `color-scheme: light`.
4. Set `body` font to Inter + `--bg` mint ground; apply Fredoka to `h1`/headings/`.kicker`.
5. Build the **hero band**: a rounded mint container wrapping the masthead, with a decorative **dashed route line** + **2 static flat icons** (e.g. paper-plane in coral, hot-air balloon in teal/mustard) positioned at corners, `aria-hidden`. No drift animation. Keep the suitcase crest + `h1` "Trip Packing Agent" + kicker "It knows you." + lede.

**Done when:** the top of the page looks bright/friendly (mint band, rounded display wordmark, route + icons), the page ground is mint, and the form/results still render and the form still submits. No console errors.

**End the phase by printing the Phase 2 kickoff prompt (below).**

---

## Phase 2 — Form card

**Goal:** the trip form feels designed and on-brand.

**Steps:**
1. Restyle the form `.card`: white surface, soft `--shadow`, `--radius`.
2. Fields: inset `--surface-2` inputs, rounded `--radius-sm`, teal `:focus-visible` ring (`box-shadow: 0 0 0 3px color-mix(in srgb, var(--teal) 28%, transparent)`).
3. Date range: keep the paired single-frame control; teal focus-within ring.
4. Purpose segmented control: keep radios; selected segment uses a teal-tinted fill + teal border; keep icons; keyboard + `:focus-visible` intact.
5. Generate button: **mustard** (`--action`) bg with `--action-ink` dark text, rounded, hover `--action-dk`, active translate, teal focus ring. Keep the sparkle icon + label.

**Done when:** the form is clearly the new style, all controls keyboard-operable with visible teal focus, button is mustard with accessible contrast, and submit still works.

**End the phase by printing the Phase 3 kickoff prompt (below).**

---

## Phase 3 — Results & list

**Goal:** generated results read as the new style (no signature touches yet — those are Phase 4).

**Steps:**
1. Weather hero: keep the weather-aware accent (`--hx`) but restyle as a bright rounded card on the mint world; Fredoka place name.
2. Toolbar: count pill + legend filter chips restyled (white pills, source-colored dot, `aria-pressed` active state with tinted fill).
3. Category groups: clean uppercase group head + count + hairline.
4. Item rows: white `--surface` rows, `--radius-sm`, `--shadow-sm`, hover border; custom checkbox styled with teal checked fill; label strikethrough on `.done`.
5. Keep badges as **plain** (source-colored) for now — Phase 4 turns them into stickers. Keep filtering + grouping + count logic untouched.

**Done when:** generating a list shows a styled hero, working source filters, category groups, and checkable rows with persistence — all in the new palette.

**End the phase by printing the Phase 4 kickoff prompt (below).**

---

## Phase 4 — Signature touches

**Goal:** the three ownable moments.

**Steps:**
1. **Sticker badges:** restyle `.badge` to a die-cut sticker — solid source-color fill, **white 2px border**, `--sticker-shadow`, slight rotation via `--rot` set per item in `itemRow` (e.g. `[-4,3,-2,4,-3,2][i%6]`), straighten + slight scale on hover. White text for contrast. Keep `.btext` hidden on very narrow screens.
2. **Dotted route line on Generate:** in `showLoading`, prepend a **flight track** — a dashed rail with a plane that flies left→right and a teal "fill" line that draws beneath it (keyframes), coral start dot + teal end pin. This is the "route draws on generate" moment + the real loading affordance. `prefers-reduced-motion`: static line, no flight.
3. **Passport-stamp on check:** add a `.stamp` ("Packed", Fredoka, source/skill color, double border, rotated ~-8°) per row, `display:none` until `.done`, then animates in (`scale 1.7→1` thunk). Reduced-motion: appears without the thunk. Place it between label and badge.

**Done when:** badges look like tilted stickers, Generate shows the animated flight track, and checking an item stamps it "Packed". All three respect reduced-motion.

**End the phase by printing the Phase 5 kickoff prompt (below).**

---

## Phase 5 — States, privacy & Impeccable audit

**Goal:** finish the edges and quality-gate the whole thing.

**Steps:**
1. Polish the **empty**, **skeleton**, and **error** states to the new palette (skeleton can reuse the flight track + shimmer rows).
2. Restyle the **privacy "Vibe Diff" panel** (sent vs. kept private) on-brand — friendly, prominent (it's a judged story element). Keep the heuristic parse + whole-note fallback.
3. **Impeccable audit:** `npx impeccable install`, then run its critique/polish (`/impeccable audit`, `/impeccable critique`, `/impeccable polish`). Fix flagged AI-design smells (overused fonts, weak contrast, dated animation, over-nesting).
4. **Final QA pass against the hard constraints:** single file, `/generate` contract intact, localStorage persistence, robust error parsing, `esc()` on all dynamic text, a11y (labels, `aria-live`, focus, keyboard), `prefers-reduced-motion` everywhere, mobile (~360px) + desktop. Confirm no console errors and the money-demo (profile medication always present; changing destination changes forecast → list) still works.

**Done when:** all states look polished, Impeccable findings addressed, QA checklist green. Ship it. Commit only if Oguz asks.

**This is the last phase — no next prompt to print. Summarize what shipped + any follow-ups.**

---

## Resume prompts (paste after `/clear`)

### → Phase 1
```
Read docs/UI_REDESIGN_PLAN.md, then execute Phase 1 — Shell & identity. Follow the
locked spec and hard constraints exactly. When done, update the status tracker in the
plan, verify in a browser, and print the Phase 2 kickoff prompt.
```

### → Phase 2
```
Read docs/UI_REDESIGN_PLAN.md (Phase 1 is done — the new tokens/fonts/hero band are in
packing-agent/app/static/index.html). Execute Phase 2 — Form card. Follow the locked spec
and hard constraints. When done, update the status tracker, verify in a browser, and print
the Phase 3 kickoff prompt.
```

### → Phase 3
```
Read docs/UI_REDESIGN_PLAN.md (Phases 1–2 done). Execute Phase 3 — Results & list. Reskin
the hero, toolbar/filters, category groups, and item rows to the new palette; keep badges
plain (stickers come in Phase 4). Preserve all filter/group/persistence logic. When done,
update the status tracker, verify by generating a list in a browser, and print the Phase 4
kickoff prompt.
```

### → Phase 4
```
Read docs/UI_REDESIGN_PLAN.md (Phases 1–3 done). Execute Phase 4 — Signature touches:
sticker badges, the animated dotted route/flight-track on Generate, and passport-stamp
on check. Respect prefers-reduced-motion for all three. When done, update the status
tracker, verify in a browser, and print the Phase 5 kickoff prompt.
```

### → Phase 5
```
Read docs/UI_REDESIGN_PLAN.md (Phases 1–4 done). Execute Phase 5 — States, privacy &
Impeccable audit: polish empty/skeleton/error states, restyle the privacy Vibe Diff panel,
run the Impeccable audit (npx impeccable install → /impeccable critique + polish), then do
the final QA pass against the hard constraints. Update the status tracker. This is the last
phase — summarize what shipped and any follow-ups instead of printing a next prompt.
```
