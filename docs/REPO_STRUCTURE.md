# REPO_STRUCTURE.md — Canonical Layout for `mvc-pipeline`

Every brief assumes this layout. If a brief needs a new top-level entry, it must be added here first.

---

## Tree

```
mvc-pipeline/
├── CLAUDE.md                  # operating manual (read every session)
├── REPO_STRUCTURE.md          # this file
├── README.md                  # human-facing intro: what + how to run locally
├── Makefile                   # one-word commands: verify, test, run, deploy
├── pyproject.toml             # uv-managed; deps + tool configs (ruff, mypy, pytest)
├── uv.lock                    # committed
├── .python-version            # 3.12
├── .env.example               # template; .env is gitignored
├── .gitignore
├── .dockerignore
├── Dockerfile                 # production image for Fly
├── fly.staging.toml           # Fly app config for staging
├── .github/
│   └── workflows/
│       ├── ci.yml             # lint + types + tests on every PR
│       └── deploy-staging.yml # on push to main → flyctl deploy
├── .pre-commit-config.yaml    # ruff + mypy + secret scan
│
├── src/mvc/
│   ├── __init__.py
│   ├── main.py                # FastAPI app factory; /health; route registration
│   ├── config.py              # pydantic-settings: all env vars typed
│   ├── state.py               # PipelineState (Pydantic) — single source of truth
│   ├── graph.py               # LangGraph DAG wiring; nothing else
│   ├── deps.py                # Deps container (DI for integrations into agents)
│   ├── observability.py       # Sentry + structlog + LangSmith init
│   │
│   ├── agents/                # 10 agents, one file each
│   │   ├── __init__.py
│   │   ├── strategy.py
│   │   ├── source.py
│   │   ├── ingest.py
│   │   ├── moment.py
│   │   ├── safety.py
│   │   ├── editor.py
│   │   ├── captioner.py
│   │   ├── distribution.py
│   │   ├── monitor.py
│   │   └── critic.py
│   │
│   ├── integrations/          # all external I/O; protocol + real + mock per file
│   │   ├── __init__.py
│   │   ├── llm.py             # LLMClient protocol; AnthropicLLM; MockLLM
│   │   ├── transcription.py   # TranscriptionClient; ModalWhisper; MockTranscription
│   │   ├── storage.py         # StorageClient; R2Storage; MockStorage (local /tmp)
│   │   ├── posting.py         # PostingClient; AggregatorPosting; MockPosting
│   │   ├── queue.py           # QueueClient; RedisQueue; MockQueue
│   │   └── db.py              # SupabaseClient wrapper (real-only, no mock — use a test schema)
│   │
│   ├── api/                   # FastAPI routers
│   │   ├── __init__.py
│   │   ├── pipelines.py       # POST/GET /v1/pipelines
│   │   ├── runs.py            # POST /v1/pipelines/{id}/run, GET /v1/runs/{id}
│   │   ├── webhooks.py        # inbound webhooks (aggregator, Stripe later)
│   │   └── auth.py            # Supabase Auth JWT middleware + dependency
│   │
│   ├── models/                # Pydantic request/response schemas (API boundary)
│   │   ├── __init__.py
│   │   ├── pipeline.py
│   │   └── run.py
│   │
│   └── cli.py                 # `mvc run --theme "..."` — same graph as the API
│
├── migrations/                # SQL migrations for Supabase
│   ├── 0001_initial.sql       # users (mirror), pipelines, compliance_events
│   ├── 0002_pipeline_runs.sql
│   └── ...
│
├── scripts/
│   ├── bootstrap.sh           # one-shot: install uv, sync deps, run migrations
│   ├── smoke_staging.sh       # curls staging /health + a no-op run
│   └── reset_local_db.sh
│
└── tests/
    ├── __init__.py
    ├── conftest.py            # shared fixtures: mock factories, FastAPI test client
    ├── fixtures/              # JSON fixtures of agent inputs/outputs for replay tests
    │   └── ...
    ├── test_contracts.py      # asserts every mock satisfies the same protocol as real
    ├── test_graph.py          # end-to-end DAG with all mocks
    ├── test_api/
    │   ├── test_pipelines.py
    │   ├── test_runs.py
    │   └── test_auth.py
    └── test_agents/
        ├── test_strategy.py
        ├── test_source.py
        ├── test_ingest.py
        ├── test_moment.py
        ├── test_safety.py
        ├── test_editor.py
        ├── test_captioner.py
        ├── test_distribution.py
        ├── test_monitor.py
        └── test_critic.py
```

---

## Conventions

### Naming
- Modules: `snake_case.py`. Classes: `PascalCase`. Constants: `UPPER_SNAKE`.
- Protocols end in `Client` (e.g. `LLMClient`). Mocks are prefixed `Mock` (e.g. `MockLLM`).
- Tests mirror the source path: `src/mvc/agents/strategy.py` → `tests/test_agents/test_strategy.py`.

### Imports
- Agents import only from `mvc.state`, `mvc.deps`, `mvc.integrations.<protocol>`. Never from each other.
- API routers import from `mvc.models`, `mvc.deps`, `mvc.graph`. Never directly from agents.
- `tests/test_contracts.py` enforces these rules via static checks.

### File size
- Source file soft cap: 300 lines. Hard cap: 500.
- Test file no cap (split when natural).

### Async
- Every agent is `async def`. Every integration method is `async def`.
- Sync work in agents must be wrapped in `asyncio.to_thread`.

### Errors
- Each integration raises a typed exception in its module (e.g. `LLMError`, `LLMRateLimitError`).
- Agents catch only what they know how to recover from. Everything else bubbles to the orchestrator.

### Migrations
- Numbered `NNNN_short_name.sql`. Forward-only. Never edit a committed migration; add a new one.
- Each migration has a comment header with date, purpose, and rollback notes.

---

## When to update this file

- Adding a new top-level directory.
- Adding a new integration (and therefore a new file under `integrations/`).
- Adding a new API module (and therefore a new file under `api/`).
- Changing a convention above.

Update is a separate PR titled `chore: update REPO_STRUCTURE for <thing>`.
