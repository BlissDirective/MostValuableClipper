# VoiceForge — Complete Build Specification

> **Drop-in development brief for Claude Code.**
> This file is the single source of truth for building VoiceForge, a voice-first content-repurposing studio. It contains the app concept, architecture, repo structure, agent design, model-routing strategy, and a phased build plan. Hand this to Claude Code as the project's foundational context (e.g. as `CLAUDE.md` or `/docs/SPEC.md`).

---

## Part 1 — App Concept Summary

### One-liner
VoiceForge turns any source — a blog post, a transcript, an uploaded video/audio file, or a raw idea — into a full set of platform-native content (LinkedIn posts, X threads, newsletter sections, short-form video scripts, captions) that actually sounds like the creator wrote it.

### The core thesis
The market is saturated with "AI that generates social posts." That is a commodity. **The differentiator and the entire moat is the voice engine**: a persistent, per-creator style model that gets measurably better the more the creator uses it, and is painful to recreate on a competing tool. Everything else (ingestion, format fan-out) is plumbing.

The strategic framing: this is a **vertical, voice-embedded** tool, not a horizontal generator. The accumulating per-creator voice profile is the switching cost. The longer a creator uses VoiceForge, the more it sounds like them, the less likely they leave.

### Target personas (multi-persona by design)
1. **B2B founders / thought-leaders** — LinkedIn-first, want consistent personal-brand output without a ghostwriter.
2. **Content creators** — newsletter/short-form, want to repurpose one piece across many channels.
3. **Agencies** — manage many clients, each needing an isolated voice profile and workspace. This persona drives the multi-tenant requirement (data isolation is non-negotiable).

### Primary input: any source
The ingestion layer must normalize all of: pasted long-form text, a URL, an uploaded audio/video file (transcribe first), or a single raw idea/prompt.

### What makes it defensible
- **Voice profile as accumulating asset** — structured profile + embeddings, refined on every user edit via a feedback loop.
- **Multi-tenant voice isolation** — agencies store one profile per client/brand; this is also the natural metering axis.
- **Not a thin wrapper** — the orchestration logic + accumulated per-creator voice data is the IP, not any single prompt.

### Monetization
- **Creators / founders:** flat monthly subscription.
- **Agencies:** per-workspace or per-client-profile tier (profiles = metering axis).
- Lean toward outcome/value framing where possible; the market is shifting away from flat per-seat access toward paying for results.

---

## Part 2 — Architecture Overview

### High-level shape
A **hierarchical fan-out/fan-in** orchestration, NOT a free-for-all agent mesh. One orchestrator (strategy agent) coordinates parallel format workers, all conditioned on a shared read-only voice profile. This keeps the system debuggable and cost-bounded — free-form agent-to-agent chatter can trigger runaway LLM-call loops and is notoriously hard to debug.

```
                    ┌─────────────────────┐
   any source  ───► │  Ingestion Agent    │  normalize → source doc + themes
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
   (onboarding)     │  Voice Profile      │  ◄─── persistent asset (pgvector + JSON)
   samples ───────► │  Engine (the MOAT)  │  ◄─── refined by edit-feedback loop
                    └──────────┬──────────┘
                               │ (profile injected as shared context)
                    ┌──────────▼──────────┐
                    │  Strategy Agent     │  decides which formats + angle each
                    │  (orchestrator)     │
                    └──────────┬──────────┘
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
        ┌──────────┐    ┌──────────┐    ┌──────────┐
        │ LinkedIn │    │ X thread │    │Newsletter│   ... (parallel format agents)
        │  Agent   │    │  Agent   │    │  Agent   │
        └────┬─────┘    └────┬─────┘    └────┬─────┘
             └───────────────┼───────────────┘
                             ▼
                    ┌─────────────────────┐
                    │  QA / Consistency   │  voice-match check + platform limits
                    │  Agent              │
                    └──────────┬──────────┘
                               ▼
                    editable multi-format board (UI)
                               │
                     user edits ──► feed back into Voice Profile Engine
```

### The five agent roles

| # | Agent | Complexity | Runtime model | Purpose |
|---|-------|-----------|---------------|---------|
| 1 | **Ingestion** | Commodity | Kimi K2.6 | Accept any source, transcribe A/V, normalize to a clean source doc + extracted themes/claims. |
| 2 | **Voice Profile Engine** | **Hard — the moat** | Claude (quality-critical) | Extract structured voice profile from samples; refine from edit-diffs. Persistent, not per-request. |
| 3 | **Strategy / Planning** | Light | Kimi K2.6 | Given source + connected channels, choose formats + per-format angle. Orchestrator of the fan-out. |
| 4 | **Format agents (N)** | Commodity, parallel | Kimi K2.6 | One per output type; each conditioned on the voice profile. Run in parallel, streamed. |
| 5 | **QA / Consistency** | Light | Kimi K2.6 | Check each output against voice profile; enforce platform constraints (char limits, hashtag norms). |

### Model-routing strategy

**At build time (your dev loop):**
- **Claude Code** → architecture, the voice engine, multi-tenant RLS, billing — anywhere correctness compounds.
- **Kimi K2.6 (via Kimi Code)** → bulk generation, the format-agent boilerplate, repetitive scaffolding. K2.6 delivers ~80–90% of Claude Code's quality at roughly 12% of the cost on standard tasks (code gen, tests, refactors, UI prototyping).

**At runtime:**
- **Voice analysis → Claude.** This is the moat; do not cheap out on the conditioning step.
- **Format fan-out → Kimi K2.6**, parallelized. K2.6 has a 256K context window and a swarm architecture suited to cheap parallel generation.

**Kimi runtime caveats (design around these):**
- K2.6 is slow (~44 tok/s) and verbose → **parallelize format agents, don't chain them; stream output.**
- The voice profile is re-sent on every generation → **route Kimi through a provider with cached-token pricing (e.g. DeepInfra ~$0.15/1M cached, or Parasail for lowest blended) and use prompt caching for the profile.** Do not use the naive native endpoint for this resend pattern.

---

## Part 3 — Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| **Framework** | Next.js 15 (App Router) on Vercel | Already your home turf; v0 outputs straight into it; one-click deploy. |
| **Orchestration** | TypeScript in Next.js server actions / API routes | One repo, one deploy, easy for Claude Code + Kimi to reason about. Direct LLM calls on the hot path. |
| **n8n** | Side-channel only | Scheduled re-ingestion, webhook publishing fan-out. **NOT** the realtime orchestration brain (latency + couples IP to a workflow tool + hard to debug the voice loop). |
| **DB / Auth** | Supabase (Postgres + pgvector + RLS + Auth) | Covers vectors for voice embeddings, multi-tenant isolation via RLS, and auth in one dependency. |
| **Billing** | Stripe | Per-workspace / per-profile metering for agencies; flat tier for solos. |
| **Transcription** | Whisper-class API | A/V → text in the ingestion agent. |
| **Design pipeline** | Google Stitch (explore) → v0 (component code) → Claude Code/Kimi (assembly) | Stitch free for exploration; v0 emits clean shadcn/ui React that copy-pastes into the real repo. Let the design tools build static shells only; Claude Code wires the stateful/interactive logic. **Never let the design tool touch the orchestration layer.** |

**Design-tool caution:** all vibe-coding tools nail ~80% (initial layout) but the final 20% (interactions, error handling) degrades code quality. Use v0/Stitch for the static shells — multi-format board, onboarding, voice-profile editor — then hand interactivity to Claude Code.

---

## Part 4 — Repo Structure

A single Next.js monorepo-lite. Keep the orchestration core isolated from the UI so the IP is portable and testable.

```
voiceforge/
├── CLAUDE.md                      # ← drop this spec (or a pointer to it) here
├── README.md
├── .env.example                   # all keys documented, no secrets committed
├── next.config.ts
├── package.json
├── tsconfig.json
│
├── /src
│   ├── /app                       # Next.js App Router
│   │   ├── /(marketing)           # public landing, pricing
│   │   ├── /(auth)                # login, signup, workspace select
│   │   ├── /(app)                 # authenticated app shell
│   │   │   ├── /onboarding        # voice-sample intake + profile confirm screen
│   │   │   ├── /create            # source drop → plan → multi-format board
│   │   │   ├── /profiles          # voice profile management (agency: per client)
│   │   │   └── /settings          # workspace, billing, channels
│   │   └── /api                   # route handlers (thin; delegate to /core)
│   │       ├── /ingest
│   │       ├── /generate
│   │       └── /voice
│   │
│   ├── /core                      # ◄── THE IP. Framework-agnostic, unit-tested.
│   │   ├── /orchestration
│   │   │   ├── strategy.ts        # planning agent: source → content plan
│   │   │   ├── graph.ts           # fan-out/fan-in coordinator
│   │   │   └── qa.ts              # consistency agent
│   │   ├── /voice                 # ◄── THE MOAT. Build this first.
│   │   │   ├── extract.ts         # samples → structured voice profile
│   │   │   ├── feedback.ts        # edit-diff → profile refinement
│   │   │   ├── schema.ts          # VoiceProfile type (see Part 5)
│   │   │   └── conditioning.ts    # inject profile into any downstream prompt
│   │   ├── /agents
│   │   │   ├── ingestion.ts
│   │   │   └── /formats
│   │   │       ├── linkedin.ts
│   │   │       ├── x-thread.ts
│   │   │       ├── newsletter.ts
│   │   │       └── _registry.ts   # register new formats here (ship with 3!)
│   │   ├── /llm
│   │   │   ├── claude.ts          # quality-critical calls
│   │   │   ├── kimi.ts            # via DeepInfra/Parasail, prompt-cached
│   │   │   └── router.ts          # picks model per job-type
│   │   └── /transcription
│   │       └── whisper.ts
│   │
│   ├── /components                # shadcn/ui + v0-generated shells
│   │   ├── /ui                    # shadcn primitives
│   │   ├── /board                 # multi-format editable board
│   │   ├── /onboarding
│   │   └── /voice-editor
│   │
│   ├── /lib
│   │   ├── supabase/              # client, server, RLS helpers
│   │   ├── stripe/
│   │   └── utils.ts
│   │
│   └── /types                     # shared TS types
│
├── /supabase
│   ├── /migrations                # SQL incl. RLS policies + pgvector setup
│   └── seed.sql
│
├── /n8n                           # exported workflows (publishing, re-ingest)
│   └── workflows/
│
└── /tests
    ├── /voice                     # ◄── test the moat hardest
    └── /orchestration
```

**Key principle:** `/core` must not import from `/app` or `/components`. The orchestration + voice IP should be runnable and testable in isolation. This keeps the moat portable and lets Claude Code reason about it without UI noise.

---

## Part 5 — The Voice Profile (the moat, build first)

### Suggested schema (`/core/voice/schema.ts`)

```typescript
interface VoiceProfile {
  id: string;
  workspaceId: string;        // RLS tenant key
  clientId?: string;          // agencies: one profile per client
  version: number;            // increments on each refinement

  tone: {
    descriptors: string[];    // e.g. ["direct", "warm", "contrarian"]
    formality: number;        // 0–1
    energy: number;           // 0–1
  };
  structure: {
    avgSentenceLength: number;
    sentenceLengthVariance: number;
    paragraphRhythm: string;  // e.g. "short punchy / occasional long"
    usesLists: boolean;
  };
  lexicon: {
    signaturePhrases: string[];
    vocabularyLevel: string;
    emojiUsage: "none" | "sparse" | "frequent";
    neverSay: string[];       // anti-patterns — critical for authenticity
  };
  hooks: {
    openingPatterns: string[];
    closingPatterns: string[];
    ctaStyle: string;
  };
  embedding: number[];        // pgvector — for similarity / QA matching
  sampleCount: number;        // how many sources have shaped this
  lastRefinedAt: string;
}
```

### Extraction flow (onboarding)
1. User pastes/uploads 5–15 samples of their best existing content.
2. Analysis agent (Claude) produces the structured profile above.
3. **Confirmation screen** — show the user "here's how I read your voice," let them tweak. This is a huge trust moment; treat it as a first-class UI surface, not an afterthought.

### The feedback loop (what makes it compound)
- When a user edits generated output, diff the edit vs. the original.
- Feed the diff to the refinement agent → adjust the profile (bump `version`).
- Over time the profile converges on the creator's true voice. **This loop is the actual moat** — prioritize it in v1, do not defer it.

---

## Part 6 — App Flow

1. **Onboarding** → connect channels or paste samples → voice engine builds profile → confirmation/tweak screen.
2. **Create** → drop any source → strategy agent proposes a content set → user approves/edits the plan → parallel generation → editable multi-format board.
3. **Refine** → inline edits → edits feed back into the voice profile.
4. **Publish/export** → copy out, or (v2) push to platforms via the n8n scheduler side-channel.

---

## Part 7 — Phased Build Plan (solo + AI pair-coding, ~5–6 weeks)

> Discipline rule: **ship with 3 formats, not 8.** Scope creep on format agents is the #1 timeline risk.

### Phase 0 — Scaffold (2–3 days)
- Next.js + Supabase + Stripe wired. Auth + workspace model + RLS skeleton.
- `/core` directory established, isolated from UI. LLM router stubbed (Claude + Kimi).
- *Claude Code owns this — correctness compounds here.*

### Phase 1 — Voice engine (1.5–2 weeks) ← spend your time here
- `extract.ts`: samples → `VoiceProfile`.
- `conditioning.ts`: inject profile into a prompt.
- `feedback.ts`: edit-diff → refinement loop.
- Onboarding intake + confirmation screen.
- Hard tests in `/tests/voice`.
- *Claude Code for the engine; v0 for the onboarding shell.*

### Phase 2 — Ingestion (3–4 days)
- Any-source normalization + Whisper transcription for A/V.
- *Mostly gluing APIs — Kimi can carry most of this.*

### Phase 3 — Orchestration + formats + QA (1 week)
- Strategy agent, fan-out graph, 3 format agents, QA agent.
- Parallel + streamed Kimi calls via DeepInfra/Parasail with prompt caching.
- *Kimi-generated, low novelty — let it run, Claude Code reviews the graph.*

### Phase 4 — App shell, multi-tenancy, billing (1 week)
- Multi-format board UI, profile management (per-client for agencies), Stripe tiers, RLS hardening.
- *v0/Stitch for shells; Claude Code for RLS + billing.*

### Phase 5 — Polish + ship (3–4 days)
- Design pass, error handling on the final 20%, deploy to Vercel.
- *Claude Code owns interactivity; do not let design tools touch orchestration.*

---

## Part 8 — Claude Code Synthesis Notes

When developing with this spec, instruct Claude Code to:

1. **Treat `/core/voice` as the crown jewel.** Highest test coverage, most careful review, Claude (not Kimi) for runtime calls.
2. **Keep `/core` framework-agnostic.** No imports from `/app` or `/components`. The orchestration must be testable in isolation.
3. **Use the model router, not hardcoded clients.** Every LLM call goes through `/core/llm/router.ts` so job-type → model mapping stays in one place and is cheap to retune.
4. **Parallelize format agents; never chain them.** Fan-out/fan-in only. Stream all user-facing output.
5. **Cache the voice profile in Kimi calls.** Route through a cached-token provider; the profile is re-sent every generation.
6. **Enforce RLS from day one.** Agency client-data isolation is a correctness requirement, not a feature. Every table carries `workspaceId`; every query is tenant-scoped.
7. **Register formats in `_registry.ts`.** Adding a format should be one file + one registry line — but resist adding more than 3 before launch.
8. **Hand the design tools static shells only.** v0/Stitch output is a starting layout; Claude Code wires state, data, and error handling.

---

*End of specification. Build the voice engine first; everything else is plumbing around it.*
