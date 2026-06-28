<!--
Kaggle Writeup — paste-ready. Concierge Agents track.
Constraints: ≤2,500 words, must include a title + subtitle.
Word count of the body (Title/Subtitle/Track lines excluded): ~1,950.
-->

# Title: The Packing Agent That Knows You

## Subtitle: A personal concierge that merges live weather, trip-type expertise, and your own medical essentials into one packing list — and guarantees the medication is never forgotten.

**Track: Concierge Agents**

---

## The problem

Everyone who travels has forgotten something that mattered. Usually it is not the obvious stuff — it is the things a generic checklist can never know about: the **daily medication** you take every morning, the specific charger you always need, or the rain layer that *those exact dates in that exact city* quietly demand.

The internet is full of packing lists. They all share the same flaw: they are static templates. A "beach trip" list does not know it will rain in Reykjavik next Tuesday. A "winter trip" list does not know you have asthma and carry an inhaler. None of them know **you**. The moment a list has to reason over more than one source of truth — live weather *and* trip type *and* your personal facts — a template breaks down, and a human ends up doing the reasoning in their head at 6 a.m. before a flight.

That is a concierge problem. A good concierge does not hand you a pamphlet; they combine what they know about the situation with what they know about *you*, and they never forget the thing that actually matters to your wellbeing. We built an agent that does exactly that.

## The solution — "it knows you"

The user fills in a short web form: destination, dates, and purpose. Behind the form sits a stored **profile** — a small JSON file holding persistent personal facts: medications, always-pack essentials, and preferences. The agent reads both, fetches the **live forecast** for those specific dates and that specific place, selects the right **trip-archetype skill**, and **merges** all three sources into a single, rendered, checkable list.

The headline value is **"it knows you."** Every medication and every always-pack essential survives into **every** list — regardless of trip type, destination, or weather. And we do not merely *hope* the model remembers them; the guarantee is **structural**, enforced by deterministic code, not by a prompt. That is the demo moment: change a warm destination to a cold one and watch the list transform with the forecast, while the inhaler appears every single time, unmoved.

## Why this needs an agent (and not a template)

The "why agents?" question has a sharp answer here. The value is not in *generating text* — it is in *orchestration*. Producing this list requires:

1. **Deciding what to call, and in what order.** Fetch live weather first (you cannot pick the right skill until you know if it is cold or hot), then select a trip skill, then assemble the list.
2. **Choosing the right domain knowledge** for the trip from a library of skills, loading only what is relevant.
3. **Merging multiple sources** that can disagree — and honoring a hard constraint (medications always survive) regardless of what the other sources say.

That sequence of *decide → call a tool → use the result to make the next decision* is precisely what an agent does and a template cannot. A static page cannot phone Open-Meteo, read the forecast, branch on it, pick a skill folder, and resolve collisions between three lists. The agent is not decoration here; it is the only thing that can produce the output at all.

## Architecture

The guiding principle: **only the agent is "smart."** Everything else is a dumb tool or a passive data source that the agent orchestrates. The UI has no business logic; the weather server only knows about weather; the skills are just folders of knowledge. All reasoning lives in one place.

```
  Web UI  ─────trip input────►┐                  ┌────read at runtime───  User profile
  (form + checklist)          ▼                  ▼                        (profile.json, local-only)
                       ┌──────────────────────────────────┐
                       │        Core Agent (ADK)           │   CONCEPT 1
                       │  weather → skill → merge          │   Gemini 2.5 Flash
                       └───────┬───────────────────┬───────┘
                  calls (MCP)  │                   │  loads on demand
                               ▼                   ▼
                   Weather MCP Server        Trip Skills (Agents CLI)
                   get_weather(dest,dates)   beach / cold_weather
                   keyless Open-Meteo        SKILL.md per archetype
                   CONCEPT 2                 CONCEPT 3
                               │                   │
                               └────────┬──────────┘
                                        ▼
                              Rendered packing list
                          (personalized · each item tagged by source)
```

**The components:**

- **Web UI** (`app/static/index.html`) — a dumb client. It collects the trip facts, POSTs them to `/generate`, and renders the returned list. It never sees the profile and contains no logic.
- **User profile** (`profile.json`, gitignored) — persistent personal facts, read by the **agent** at reasoning time. It is never read by the UI, never sent to the weather tool, and never logged.
- **Core agent (ADK)** — the orchestrator and the only place reasoning happens. It calls the weather tool, selects one skill, and invokes the deterministic merge.
- **Weather MCP server** (`app/weather_server.py`) — a single tool, `get_weather`, exposed over **stdio MCP** via FastMCP and backed by **keyless Open-Meteo**. ADK spawns it as a subprocess, so the whole app launches with one command — no second terminal, no port, no API key.
- **Trip skills** (`skills/cold_weather/`, `skills/beach/`) — one folder per archetype, each a `SKILL.md` with human guidance plus a `## Packing items` list. They are loaded **on demand** (progressive disclosure): the agent only ever reads the one skill it chose.

## The four course concepts

We set out to demonstrate at least three of the course's concepts meaningfully; we landed all four.

1. **Agent (ADK)** — `root_agent` in `app/agent.py`, a Gemini 2.5 Flash agent that orchestrates three tools. Its instruction encodes an explicit, ordered policy: call `get_weather` first, then `select_skill`, then `build_packing_list`. Crucially, it is told *"do not invent packing items yourself — the tools are the source of truth,"* which keeps the reasoning honest and the output reproducible.

2. **MCP server** — `get_weather` is not a local Python function bolted onto the agent; it is a genuine MCP server in its own process, consumed through ADK's `McpToolset` over stdio. This is the most visible piece of real tool use, and it doubles as our cleanest privacy boundary (below).

3. **Agent Skills** — two contrasting skills, selected on demand by a `select_skill` tool. `select_skill` returns the skill's *guidance prose* (so the model can reason about the choice) and the item list. The model only ever passes the short skill **name** onward — never the items — so its choice cannot corrupt the actual contents of the list.

4. **Security / privacy** — the Concierge story. Covered in its own section below.

## The agentic core: a deterministic three-source merge

This is where the implementation points are won, so we treated it with care. The function `build_packing_list` is the heart of the system, and the design tension it resolves is this: **the LLM should decide *to* build the list, but should never be trusted to *assemble* it.** Medical data is too important to leave to a model that might paraphrase, drop, or hallucinate an item.

So the division of labor is strict. The agent reads the forecast, picks the skill, and calls `build_packing_list` with the trip facts and the skill *name*. From there, **pure Python takes over.** It builds three separate lists:

- **profile items** — every medication (unconditionally) plus every always-pack essential, read fresh from `profile.json`;
- **weather items** — derived from the live forecast by a fixed mapping (`cold/freezing → warm insulated jacket`, rain → waterproof jacket, etc.) so the mapping cannot drift;
- **skill items** — re-read directly from the chosen `SKILL.md`, *not* relayed by the model.

Then it merges them with `_merge_by_precedence`, which dedupes by a normalized label (lowercased, whitespace-collapsed) and keeps the **first** occurrence of each label. The elegant part: **precedence is encoded purely by order.** The caller passes the sources highest-to-lowest, and the merge keeps whoever it sees first. We chose **profile > weather > skill**:

- **Profile first** means the medication/essential copy of any colliding label always wins — and because medications occupy the very first slot, a medication is *always* the first occurrence of its label and can therefore *never* be the copy a dedupe drops. **The meds-always guarantee is structural, not a hopeful append.**
- **Weather second** means the real, trip-specific forecast beats the generic archetype baseline when both imply the same item.
- **Skill last** fills in the rest.

Order is the only knob. There are no special cases, no synonym-guessing, nothing to reason about at runtime — which is exactly what you want for a function that must be trustworthy with someone's health data. Every output item also carries a `source ∈ {profile, weather, skill}` tag, so the agent's reasoning stays *legible* in the rendered list: you can see at a glance which items came from you, which from the sky, and which from the trip type.

## Privacy & security — the Concierge boundary

A concierge handling medical and personal data has to be trustworthy by construction, so the boundaries are deliberate:

1. **Data minimization at the tool boundary.** The weather tool receives **only** destination and dates. The profile, medications, and preferences never cross into any external request. Because `get_weather` is a separate MCP process, this is not a convention we hope to remember — it is a hard architectural seam. The medical data physically cannot leak through it.
2. **No secrets in the repo.** Open-Meteo is keyless, so there is nothing to leak there. The only secret is the AI Studio key, which lives in a gitignored `.env`; the committed `.env.example` ships only variable names.
3. **No sensitive data in logs.** The profile and medications are never written to logs.
4. **Local-only profile.** `profile.json` is gitignored, read locally by the agent only, and never uploaded or sent to a third party.

The structure of the system *is* the privacy story: reasoning is centralized in the agent, sensitive data is read only there, and the one external call is walled off in its own process that sees nothing but a city name and two dates.

## The journey — how it was built

We followed one rule above all others: **keep it runnable end-to-end at all times, and replace one stub at a time.** A working fake beats a broken real.

- **Milestone A — the hardcoded spine.** Form → ADK agent → rendered list, everything faked, but built as the *real* architecture: the LLM function-calls a deterministic tool that is the source of truth. The "done" bar was simply: Generate shows a list containing the profile medication. Getting this thin slice working end-to-end first meant every later step was a swap, never a rewrite.
- **Milestone B — real MCP weather.** We stubbed `get_weather`, wired the agent to it over MCP, *then* replaced the stub body with real Open-Meteo. The payoff moment: changing the destination changed the forecast, which changed the list.
- **Milestone C — trip skills.** Two contrasting skills with on-demand loading and a deliberately simple selection rule (cold/freezing → cold_weather; hot/beach → beach), with purpose as a secondary hint.
- **Milestone D — the merge.** We turned three concatenated lists into a real deduped merge with the structural meds-always guarantee described above.

The most valuable engineering lessons were unglamorous. **Quota discipline:** the AI Studio free tier has a per-day request cap, and a single Generate makes ~3 model calls — a day of clicking exhausts it. We learned to verify deterministic logic with plain unit tests (no model calls) and spend our scarce live runs only on true end-to-end checks. We also hardened the failure paths this surfaced: the server now maps a 429 to a clean, honest message in the UI instead of failing opaquely, and an out-of-range forecast date falls back gracefully so a run never hard-crashes.

The deepest design decision was **where to draw the line between the model and the code.** Our answer — *the model decides what to do; deterministic Python decides what is in the list* — is what makes a medical-data concierge trustworthy. The agent is genuinely agentic (it chooses tools, orders them, and branches on results), but the part a user's health depends on is provably correct.

## What we would do next

The spine is solid, so the natural next steps are the stretch goals: deeper security hardening, a Cloud Run deployment for a public live demo, and a richer skill library. But we deliberately resisted over-building. A complete, coherent, demonstrable agent that *always remembers your medication* is worth more than an ambitious half-wired one — and that focus is, fittingly, exactly what a good concierge would choose.
