# CLAUDE.md — Operating Manual for the MVC Pipeline Service

Read this file at the start of every session. It is the source of truth for how to work in this repo.

---

## 1. What this repo is

The `mvc-pipeline` service: a FastAPI + LangGraph backend that orchestrates a 10-agent video-clipping pipeline. The Rork-built mobile app talks to this service. **You are building the system described in `mvp-build-spec.md` §3 (the agent pipeline).**

Hosted on **Fly.io**. Staging: `mvc-pipeline-staging.fly.dev`.

The product owner has minimal Python experience. They review code, they don't write it. Optimize for review-ability over cleverness.

---

## 2. The non-negotiables

These rules are absolute. Violating any of them means the work is rejected.

1. **Typed Python only.** `mypy --strict` must pass. No `Any` without a `# type: ignore[reason]` comment explaining why.
2. **All external I/O behind a protocol.** LLMs, transcription, storage, posting, queues — every integration is a `typing.Protocol` with a real and a mock implementation. Agents depend on the protocol, never the concrete class. This is enforced by import rules in `tests/test_contracts.py`.
3. **No PR over 400 lines of diff.** Split the work. If you can't split it, stop and ask for a revised brief.
4. **Every PR has a plain-English summary** in the description: what changed, what to review, what tests cover it, what's deferred. Three to six bullets max.
5. **Tests before merge.** `make verify` must be green: `ruff` + `mypy --strict` + `pytest`. CI enforces this.
6. **Mocks are the default in tests.** Real integrations only run when explicitly opted in via env vars (`MVC_USE_REAL_LLM=1` etc.). Tests must never hit the network without that flag.
7. **No secrets in code, ever.** `.env.example` shows the shape; `.env` is gitignored; secrets in CI come from GitHub Actions secrets; secrets in Fly come from `fly secrets`.
8. **Supabase is the only database.** No SQLite, no in-memory state pretending to be a database, no `pickle`. State lives in Postgres or it doesn't exist.
9. **Idempotency.** Every endpoint that creates state accepts an `Idempotency-Key` header. Replays return the same result, not a duplicate.
10. **Structured logging only.** `structlog` or equivalent. Every log line has `pipeline_id`, `agent`, `run_id` when those are in scope. No `print()`.

---

## 3. Architectural rules

- **The graph is the contract.** `src/mvc/graph.py` is the single place the agent DAG is wired. Agents are pure functions of `(state, integrations) -> state_delta`. Side effects happen only through injected integrations.
- **State is one Pydantic model.** `src/mvc/state.py` defines `PipelineState`. Every agent reads it, returns a delta, and LangGraph merges. No agent invents new state fields without updating the model first.
- **Integrations are protocols.** `src/mvc/integrations/` holds one file per external dependency. Each file exports a `Protocol`, a real implementation, and a mock implementation. Imports outside this folder reference only the protocol.
- **The CLI is a first-class entrypoint.** `mvc run --theme "..."` exercises the same graph the API does. If a bug only repros via the API, the CLI is wrong.
- **Observability is non-optional.** Every agent emits one structured log line on entry and one on exit (success or failure). Sentry captures every unhandled exception. LangSmith traces every run in staging.

---

## 4. The 10 agents

Build them in this order, each as a separate file under `src/mvc/agents/`:

1. `strategy.py` — theme → source plan + cadence
2. `source.py` — source plan → resolved URLs/files (priority chain per spec §4)
3. `ingest.py` — URLs/files → transcript + shot metadata
4. `moment.py` — transcript + metadata → ranked candidate moments
5. `safety.py` — moments → category tags + block/warn decisions
6. `editor.py` — approved moments → rendered 9:16 clips
7. `captioner.py` — clip + voice profile → 3 caption variants
8. `distribution.py` — clip + captions → posts on TikTok/IG/YT (via aggregator mock)
9. `monitor.py` — post records → time-series metrics
10. `critic.py` — outcomes → updated bandit parameters

Each agent must:
- Be a single async function `async def run(state: PipelineState, deps: Deps) -> StateDelta`.
- Have its own unit tests in `tests/test_agents/test_<agent>.py`.
- Log entry/exit with timing.
- Return a typed delta, never mutate `state` directly.

---

## 5. How to take a task

Every task arrives as a brief (a numbered Week-N from `WEEK_BRIEFS.md` or an ad-hoc spec). Workflow:

1. **Re-read this file.** It changes. Don't operate on stale rules.
2. **Read the brief end-to-end before writing code.** If anything is ambiguous, stop and ask one consolidated question. Don't ask one-at-a-time.
3. **Plan the diff.** Before writing, list the files you'll touch and the order. Confirm the plan fits under 400 lines of diff. If not, propose a split.
4. **Write code + tests in the same PR.** Tests aren't a follow-up.
5. **Run `make verify` locally before pushing.** CI will run it again; don't make CI find your bugs.
6. **Open the PR with the standard description template** (see §7). Tag it with the week number.
7. **Stop after the PR is opened.** Do not start the next brief until merge.

---

## 6. Environments and secrets

Three environments:

| Environment | Where | What's real | What's mocked |
|---|---|---|---|
| **Local** | Your laptop | Supabase (dev project), Sentry (dev DSN) | LLM, transcription, storage, posting, queue |
| **CI** | GitHub Actions | None | Everything |
| **Staging** | Fly.io | Supabase (staging project), Sentry, LangSmith | LLM, transcription, storage, posting, queue |

Switching a mock to real is a separate, explicit task — never a side effect of another change.

Env vars:

```
# Cheap services — real everywhere except CI
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_JWT_SECRET=        # for verifying user JWTs server-side
SUPABASE_JWKS_URL=          # https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json
SENTRY_DSN=
LANGSMITH_API_KEY=          # staging only

# Expensive services — mocked by default
MVC_USE_REAL_LLM=0
MVC_USE_REAL_TRANSCRIPTION=0
MVC_USE_REAL_STORAGE=0
MVC_USE_REAL_POSTING=0

# LLM model pins (provider-agnostic abstraction; these are the defaults)
MVC_LLM_DEFAULT_MODEL=claude-sonnet-4-6      # Strategy, Critic, Safety reasoning
MVC_LLM_LIGHT_MODEL=claude-haiku-4-5         # Captioner, lightweight calls

# Per-integration (only read when the flag above is 1)
ANTHROPIC_API_KEY=
MODAL_TOKEN_ID=
MODAL_TOKEN_SECRET=
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET=
UPSTASH_REDIS_REST_URL=     # Upstash Redis (queue) — required from Week 5
UPSTASH_REDIS_REST_TOKEN=
AGGREGATOR_API_KEY=         # Postproxy / Upload-Post / Ayrshare — decided Week 4
```

If the brief doesn't say which env vars are needed, ask before writing code.

---

## 7. PR description template

Copy this verbatim into every PR description and fill it in. Three to six bullets per section, no more.

```markdown
## Summary
<one sentence: what this PR accomplishes>

## What changed
- <bullet>
- <bullet>

## How to review
- <which files matter most, in order>
- <which tests cover the behavior>

## What's deferred / not in this PR
- <bullet>

## How I verified locally
- [ ] `make verify` green
- [ ] <any manual check, e.g. `curl http://localhost:8000/health`>
```

---

## 8. When to stop and ask

Stop and surface a question to the product owner (in the PR or as a comment back) when any of these are true:

- The brief and an existing rule in this file contradict each other.
- A new external dependency would be needed that isn't on the approved list (§9).
- A schema migration would require backfilling existing data.
- A test you'd have to write would take real network calls to be meaningful.
- The diff is heading over 400 lines and you can't see a clean split.
- Anything in the spec docs (`research-and-data.md`, `app-concept-outline.md`, `brainstorming.md`, `mvp-build-spec.md`) contradicts the brief.

Don't guess. Asking costs minutes; guessing costs days.

---

## 9. Approved dependencies

These are the only third-party packages you may add without a separate approval:

**Runtime:**
- `fastapi`, `uvicorn[standard]`, `gunicorn`
- `langgraph`, `langchain-core`, `langchain-anthropic`
- `pydantic`, `pydantic-settings`
- `httpx` (async HTTP), `tenacity` (retries)
- `structlog`, `sentry-sdk`, `langsmith`
- `supabase` (Python client), `asyncpg` (raw Postgres when needed)
- `redis` (queue, Week 5+)
- `python-jose[cryptography]` (Supabase Auth JWT verification via JWKS)

**Dev:**
- `pytest`, `pytest-asyncio`, `pytest-cov`, `pytest-httpx`
- `ruff`, `mypy`, `types-*`
- `pre-commit`

Anything else: ask before adding.

---

## 10. Definition of done

A piece of work is done when:

1. PR is open with the template filled in.
2. `make verify` is green in CI.
3. Diff is under 400 lines.
4. Every new public function has a docstring.
5. Every new integration has both a real and a mock implementation.
6. Every new endpoint has at least one happy-path test and one failure-path test.
7. The product owner can read the PR description and understand what changed without reading the code.

That's the bar. Don't merge below it.
