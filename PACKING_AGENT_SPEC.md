# Project Specification: Personalized Trip Packing-List Agent

> **Audience of this document.** This file is written to be handed to an AI coding agent (or a human developer) as the single source of truth for building this project. It contains the full competition context, the product definition, the architecture, the exact build order, the data contracts between components, the work split, and the submission requirements. Read it top to bottom before writing any code. When in doubt, prefer the simplest version that keeps the whole system runnable end-to-end.

---

## 0. TL;DR (read this first)

Build a working AI **agent** that generates a **personalized, trip-specific packing list**. The user fills a short questionnaire in a web UI (destination, dates, trip purpose). A stored user profile holds persistent personal facts (medications, always-pack items, preferences). A core **ADK agent** reads both, calls a **weather MCP server** for the forecast, selects one or more **trip-archetype skills** (beach, cold-weather, etc.), merges everything, and returns a rendered checklist.

This is a capstone for a 5-day "AI Agents / Vibe Coding" course. The submission must demonstrate **at least three** named course concepts. This project demonstrates: **(1) Agent (ADK)**, **(2) MCP Server**, **(3) Agent Skills (Agents CLI)**, with **(4) Security/privacy** as a stretch concept.

**Golden rule of the build:** at every moment there must be a system that runs end to end. Build the full path with fake/stubbed data first, then replace each stub with a real implementation one at a time. A working fake beats a broken real.

---

## 1. Competition context and hard requirements

### 1.1 What the competition is
A capstone hackathon for a 5-day AI Agents / Vibe Coding course (run on Kaggle, sponsored by Google). Participants build a practical AI agent that solves a real-world problem and package it as a writeup + video + public code.

### 1.2 Track
**Concierge Agents.** This track is for individual/family/social challenges solved in a way that keeps personal information safe and secure. The packing agent fits because it handles personal data (notably medications) and must treat it carefully.

### 1.3 Team
Two people. Both registered individually for the competition, then officially merged into one team on the platform. One combined submission for the team.

### 1.4 Required course concepts (must demonstrate at least 3)
The full menu of concepts the course defines, and where each is meant to be shown:

| Concept | Demonstrated in | Used in THIS project? |
|---|---|---|
| Agent / Multi-agent system (ADK) | Code | YES — core agent |
| MCP Server | Code | YES — weather server |
| Antigravity | Video | Optional (used as the build IDE; mention in video) |
| Security features | Code or Video | YES (stretch) — PII/medication handling |
| Deployability | Video | Optional stretch — deploy to Cloud Run if time allows |
| Agent skills (e.g. Agents CLI) | Code or Video | YES — trip-archetype skills |

Minimum bar is three. This project comfortably clears it with Agent + MCP + Skills, plus Security as a fourth.

### 1.5 Submission deliverables (all required)
1. **Kaggle Writeup** — the project report. Max 2,500 words. Must have a title, subtitle, and a track selected. Must have the assets below attached.
2. **Media Gallery** — must include a **cover image** (required to submit) and the video.
3. **Video** — 5 minutes or less, published to YouTube, attached to the Media Gallery.
4. **Public project link** — a live demo URL, OR a public code repository (e.g. GitHub) with detailed setup instructions and a `README.md`. Must be publicly accessible, no login/paywall.

Then click **Submit** (a saved Writeup is not a submitted Writeup). One submission per team.

### 1.6 Deadline
**July 6, 2026, 11:59 PM PT.** Submit well before the final hour. Only one submission per team, so do not leave the submission click to the deadline.

### 1.7 Scoring (100 points total) — design the build to win points
**Category 1 — The Pitch (30 pts):**
- Core concept & value (10) — clear, meaningful, central use of agents; relevance to the Concierge track.
- YouTube video (10) — clarity, conciseness, quality within 5 minutes. Should cover: problem statement, why agents, architecture, demo, how it was built.
- Writeup (10) — how well it articulates problem, solution, architecture, and journey.

**Category 2 — The Implementation (70 pts):**
- Technical implementation (50) — quality of architecture and code; **meaningful use of agents**; clever tool use; code comments on implementation/design/behavior. Deployment is NOT required for judging; if deployed, include reproduction docs.
- Documentation (20) — `README.md` explaining problem, solution, architecture, setup instructions, with diagrams/images where appropriate.

**Implication for the build:** the implementation is 70% of the score, and within it judges specifically reward *meaningful agentic work* and *clever tool use*. The agent must visibly reason and orchestrate (decide what to call, in what order, how to merge) — not just be an LLM that prints a list. The MCP weather call and the skill selection are the two most legible places to show this.

### 1.8 Critical rules / constraints
- **NEVER commit API keys or passwords.** Use environment variables / `.env` (gitignored). The competition explicitly flags this and judges look for it.
- Code repo must be **public** (or made public by the deadline).
- If you win, the submission + source is licensed CC-BY 4.0. Third-party commercially-available software you used (e.g. the model provider) does not need to be relicensed.
- External tools/models are allowed as long as they are reasonably accessible and low cost. Using a paid assistant subscription as a *development tool* is fine. The *demonstrated concepts* should still center on the course's stack (ADK, MCP, Agents CLI, Antigravity) to score well.

---

## 2. Product definition

### 2.1 One-sentence problem statement
> An agent that generates a personalized, trip-specific packing list by combining what it knows about the trip (destination, dates, purpose, weather) with what it knows about *you* (medications, recurring essentials, preferences) — so you never forget the things generic lists miss.

### 2.2 Why an agent (the "why agents?" answer for the pitch)
A static template can produce a generic list. The value here requires *reasoning over multiple sources and orchestrating tools*: fetch live weather for specific dates and place, choose the right domain knowledge (skill) for the trip type, and merge that against persistent personal facts that must always be honored (e.g. medication) regardless of trip. That orchestration — deciding what to call, when, and how to combine results — is exactly what an agent does and a template cannot.

### 2.3 Core value proposition
"It knows you." The persistent profile (especially medications and recurring essentials) survives into every list regardless of trip type. That personalization is the differentiator and the single best thing to highlight in the demo video.

### 2.4 Scope decisions already made (do not re-litigate)
- **Persistence:** a stored user profile (not re-entered each trip).
- **Output surface:** a small web UI (questionnaire form + rendered checklist), not chat-only.
- **One user** for the demo (single hardcoded profile). Multi-user is out of scope.

### 2.5 Explicit non-goals (do NOT build these for the capstone)
- No user accounts / auth / login.
- No database — a single JSON file is the profile store.
- No mobile app.
- No booking, payments, or calendar integration.
- No large skill library — two contrasting skills are enough to prove the concept.
- No production hardening beyond the security story described in §6.

---

## 3. Architecture

### 3.1 Component overview
The flow is top to bottom. Only the agent is "smart"; everything else is a tool or a data source it orchestrates.

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
        |  reads inputs -> calls weather tool -> selects skill(s)           |
        |  -> merges skill items + weather items + profile items            |
        |  CONCEPT 1: Agent (ADK)                                           |
        +----------------+----------------------------+---------------------+
                         |                            |
            calls (MCP)  |                            | loads on demand
                         v                            v
        +-----------------------------+   +-----------------------------+
        |     Weather MCP server      |   |   Trip skills (Agents CLI)  |
        |  get_weather(dest, dates)   |   |  beach / cold_weather / ... |
        |  CONCEPT 2: MCP Server      |   |  CONCEPT 3: Agent Skills    |
        +-----------------------------+   +-----------------------------+
                         \                            /
                          \                          /
                           v                        v
                    +-------------------------------------+
                    |        Rendered packing list        |
                    |   personalized, checkable output    |
                    +-------------------------------------+
```

### 3.2 Component responsibilities
- **Web UI** — collect trip facts; POST them to the agent; render the returned list as a checklist. Dumb client; no logic.
- **User profile (`profile.json`)** — persistent personal facts. Read by the *agent* (not the UI) at reasoning time. Never sent to the weather tool, never written to logs.
- **Core agent (ADK)** — the orchestrator and the only place reasoning happens. Receives trip input, loads the profile, calls the weather tool via MCP, selects the matching skill(s), and merges three sources into the final list.
- **Weather MCP server** — exposes a single tool `get_weather`. Returns a normalized forecast for the destination + date range. This is the real tool integration and the most visible proof of agentic tool use.
- **Trip skills** — each skill is a folder with a `SKILL.md` plus a packing list / packing logic for one trip archetype. The agent loads only the relevant skill(s) on demand (progressive disclosure).
- **The merge** — explicit, commented logic combining: matched skill items + weather-driven additions + profile always-pack & medication items. This is the core agentic reasoning; keep it readable and well-commented because it is where points are won.

---

## 4. Data contracts (lock these before parallel work)

These shapes are the contract that lets two people work in parallel without blocking each other. Agree on them first; do not change them unilaterally.

### 4.1 Trip input (Web UI -> agent)
```json
{
  "destination": "Reykjavik, Iceland",
  "start_date": "2026-07-10",
  "end_date":   "2026-07-14",
  "purpose":    "leisure"
}
```
- `destination`: free-text place name (string).
- `start_date` / `end_date`: ISO `YYYY-MM-DD` strings.
- `purpose`: one of a fixed dropdown set, e.g. `leisure`, `business`, `beach`, `outdoors`. (Used as a hint for skill selection alongside weather.)

### 4.2 User profile (`profile.json`, read by agent)
```json
{
  "medications": ["daily inhaler"],
  "always_pack": ["phone charger", "reading glasses", "passport"],
  "preferences": {
    "avoids": ["checked luggage"],
    "notes": "prefers merino layers"
  }
}
```
- `medications`: array of strings. ALWAYS included in the final list regardless of trip. Treat as sensitive (see §6).
- `always_pack`: array of strings always added.
- `preferences`: free-form hints the agent may use to adjust the list.

### 4.3 Weather tool response (MCP server -> agent)
```json
{
  "destination": "Reykjavik, Iceland",
  "start_date": "2026-07-10",
  "end_date":   "2026-07-14",
  "summary":    "cold",
  "temp_c_min": 7,
  "temp_c_max": 13,
  "precipitation": "likely",
  "conditions": ["rain", "wind"]
}
```
- `summary`: a coarse bucket the agent can branch on: one of `hot`, `warm`, `mild`, `cold`, `freezing`.
- `conditions`: array of notable conditions, e.g. `rain`, `snow`, `wind`, `sun`.

### 4.4 Final packing list (agent -> Web UI)
```json
{
  "trip": { "destination": "Reykjavik, Iceland", "start_date": "2026-07-10", "end_date": "2026-07-14" },
  "weather_summary": "cold, rain likely, 7-13C",
  "items": [
    { "label": "waterproof jacket", "source": "weather",  "category": "clothing" },
    { "label": "warm layers",       "source": "skill",    "category": "clothing" },
    { "label": "daily inhaler",     "source": "profile",   "category": "health" },
    { "label": "phone charger",     "source": "profile",   "category": "essentials" }
  ]
}
```
- Each item carries a `source` (`weather` | `skill` | `profile`) so the UI can group/annotate and so the demo can visibly show *why* each item is there. The `source` field is what makes the agent's reasoning legible — keep it.

---

## 5. Build plan — exact order

Build the spine first (UI -> agent -> output, all stubbed). Prove it runs. Only then replace stubs with real implementations, one at a time, never more than one unproven box at once.

### 5.1 Milestone A — the hardcoded spine (do this jointly, first)
**Goal:** a request flows from the form to a rendered list with everything faked.
1. **Web UI (stub):** one page, a form (destination, start date, end date, purpose dropdown), a Generate button, and an empty results area. On submit, POST the trip input (§4.1) to the agent and render whatever comes back.
2. **User profile (stub):** create `profile.json` (§4.2) with one hardcoded person. The agent loads it at run start.
3. **Core agent (stub):** an ADK agent that receives the trip input, loads `profile.json`, and returns a **hardcoded** list in the §4.4 shape. No weather, no skills yet.

**Done when:** typing into the form and hitting Generate shows a list that includes at least one profile-derived item (e.g. the medication). This is the most important milestone of the project — once it works you always have a demoable system.

### 5.2 Milestone B — real MCP weather tool
1. **Weather MCP server (stub):** stand up an MCP server exposing `get_weather(destination, start_date, end_date)` that returns a **hardcoded** response (§4.3). Wire the agent to actually call it through MCP.
   - **Done when:** the agent calls the tool over MCP and receives a response. The hardest concept is now proven with zero external dependency.
2. **Weather MCP server (real):** replace the hardcoded return with a real call to a **free, no-key** weather API. Use **Open-Meteo** (no API key required) to avoid setup pain and keep "no secrets in repo" trivially true. Normalize its response into the §4.3 shape (map raw temps into the `summary` bucket).
   - **Done when:** changing the destination changes the forecast which changes the list. This is the money demo moment — capture it on video.

### 5.3 Milestone C — trip skills
1. Create **two** skill folders, each with a `SKILL.md` and a packing list: e.g. `skills/beach/` and `skills/cold_weather/`.
2. Agent selects a skill with the **simplest possible rule first** (e.g. `weather.summary in [cold, freezing] -> cold_weather`; `beach`/`hot` -> beach). Use `purpose` as a secondary hint.
3. The selected skill's items flow into the merge.
   - **Done when:** a cold trip loads the cold-weather skill and its items appear; a warm/beach trip loads the other. Two contrasting skills with a visible switch fully demonstrates progressive disclosure. Add more skills only if time remains.

### 5.4 Milestone D — the merge (the agentic core)
Combine three sources into the final `items` array:
- skill items (`source: "skill"`)
- weather-driven additions (`source: "weather"`) — e.g. `rain` in conditions -> add waterproof jacket / umbrella; `freezing` -> add thermals.
- profile items (`source: "profile"`) — `always_pack` plus EVERY `medication`, unconditionally.

Deduplicate by label. Keep this function explicit and heavily commented — it is the reasoning judges most want to see. The medication surviving into every list regardless of trip is the headline value moment.

### 5.5 Milestone E — stretch (only if spine + B + C + D are solid)
- **Security/privacy hardening (§6).** This is the highest-value stretch because it is a 4th concept and reinforces the Concierge framing. Even a light implementation plus a clear video explanation counts.
- **Deployability.** Deploy the UI + agent (e.g. to Cloud Run) and document reproduction steps. Not required for judging; a bonus concept if time allows.
- **More skills**, nicer UI styling, checkbox state. Pure polish; lowest priority.

---

## 6. Security & privacy (the stretch concept and the Concierge story)

Treat the profile — especially `medications` — as sensitive. Minimum viable, demonstrable measures:
1. **Data minimization at the tool boundary.** The weather tool receives ONLY destination + dates. Never pass profile data, medications, or preferences into the weather call or any external request. (Mirrors the course's "context-as-a-perimeter" / policy-server idea: tools get only what they need.)
2. **No secrets in the repo.** No API keys (Open-Meteo needs none); any future keys live in `.env`, which is gitignored.
3. **No sensitive data in logs.** Do not log the full profile or medication contents. If you log for debugging, redact medications (e.g. replace with `[[MEDICATION]]` placeholders, echoing the course's PII-placeholder pattern).
4. **Local-only profile.** The profile file stays local to the running app; it is not uploaded anywhere or sent to third parties.
5. **(Optional, strong for video)** Add a one-line "Vibe Diff"-style summary the agent shows before finalizing — a plain-English note of what it used and what it deliberately kept private ("Used your destination and dates for weather; kept medications local and added them privately to your list").

Document these in the README under a "Privacy & security" heading and narrate measure (1) and (3) in the video — they are concrete, legible, and on-theme.

---

## 7. Work split (two people)

**Phase 1 — together (~30-60 min):** build Milestone A (the hardcoded spine) jointly so both share the same mental model and the §4 data contracts are agreed and frozen.

**Then split behind the frozen contracts:**
- **Person A — tool side:** Milestone B (MCP server: stub then real Open-Meteo) and Milestone D (the merge logic inside the agent).
- **Person B — knowledge side:** Milestone C (the two skills + selection rule), the profile (§4.2 shape + loader), and start the README (§9) + video script (§10) in parallel.

Because the stub agent (Milestone A) already returns a valid list, neither person is ever blocked: each swaps a stub for a real implementation behind a stable contract. Commit to the shared public repo frequently.

---

## 8. Tech stack & environment notes

- **Agent framework:** ADK (the course's agent toolkit). The agent is the orchestrator and the only reasoning component.
- **Tool protocol:** MCP. The weather tool is exposed as an MCP server the agent connects to.
- **Skills:** structured as folders with a `SKILL.md` each, loaded on demand (Agents CLI / skills pattern).
- **Weather API:** Open-Meteo (free, no API key). Normalize to the §4.3 shape.
- **Web UI:** a minimal web front end (a single page with a form and a results area). Keep it dumb; no business logic in the client.
- **Profile store:** a single `profile.json` file. No database.
- **Build IDE:** Antigravity may be used as the development environment; if so, mention it in the video to optionally claim that concept.
- **Secrets:** `.env` (gitignored). None needed for the core build since Open-Meteo is keyless.

---

## 9. README.md requirements (worth 20 points — write as you build)

The repo README must include, with diagrams/images where helpful:
1. **Problem** — the one-sentence statement (§2.1) and why it matters.
2. **Solution** — what the agent does and the "it knows you" value (§2.3).
3. **Why agents** — the §2.2 reasoning.
4. **Architecture** — the §3 diagram (export the diagram image and embed it) and a short description of each component.
5. **Course concepts demonstrated** — explicitly list Agent (ADK), MCP server, Skills, and Security, pointing to where each lives in the code.
6. **Setup & run instructions** — exact, reproducible steps to run the UI + agent + MCP server locally from a clean clone. Test these on a fresh checkout.
7. **Privacy & security** — the §6 measures.
8. **(If deployed)** reproduction/deployment steps.

Reminder in bold near the top of the README: no API keys or secrets are committed.

## 10. Video requirements (≤5 min, YouTube — worth 10 points)

Loosely script it; do not wing it. Cover, within 5 minutes:
1. **Problem** — the forgotten-essentials problem; who it's for (Concierge framing).
2. **Why agents** — the §2.2 point.
3. **Architecture** — show the §3 diagram on screen and narrate the flow.
4. **Demo** — the money moment: change the destination from a warm place to a cold place and show the list visibly change (weather-driven), while the medication/essentials persist every time (profile-driven). Show one skill switch.
5. **The build** — tools/tech used (ADK, MCP, skills; mention Antigravity if used), and the privacy measures (§6).

Also produce a **cover image** for the Media Gallery (required to submit) — the architecture diagram or a clean title card works.

---

## 11. Definition of done (submission checklist)

- [ ] Public repo with all code, runnable from a clean clone.
- [ ] `README.md` complete per §9, setup steps verified on fresh checkout.
- [ ] No API keys / secrets committed; `.env` gitignored.
- [ ] End-to-end demo works: form -> agent -> MCP weather -> skill -> merged list, with profile items (incl. medication) always present.
- [ ] At least 3 course concepts clearly demonstrated and pointed to in README (Agent, MCP, Skills [+ Security]).
- [ ] YouTube video ≤5 min, public, attached to Media Gallery.
- [ ] Cover image attached to Media Gallery.
- [ ] Kaggle Writeup (≤2,500 words) with title, subtitle, Concierge track selected; assets attached.
- [ ] Project link (live demo or the public repo) attached.
- [ ] **Submit clicked** (not just saved) — well before July 6, 2026, 11:59 PM PT.
- [ ] Team officially merged on the platform (both members registered individually first).

---

## 12. Operating principles for the building agent

- Keep the system runnable end to end at all times. Replace one stub at a time.
- Put all reasoning in the agent; keep the UI and tools dumb.
- Tools receive only what they need; profile/medication data never leaves the agent's local reasoning.
- Comment the merge logic and the skill-selection logic thoroughly — that is where implementation points are won.
- Prefer the keyless Open-Meteo API; never introduce a secret unless unavoidable, and if so, gitignore it.
- Two contrasting skills are sufficient — do not over-build the skill library before the spine and merge are solid.
- Favor a complete, coherent, demoable agent over an ambitious half-wired one.
