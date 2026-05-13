# API_CONTRACT.md — The seam between Rork and the FastAPI pipeline service

This is the **single source of truth** for the HTTP boundary between the Rork mobile app and the `mvc-pipeline` FastAPI service. It exists so both halves of the build can move in parallel without surprises.

- **Rork** (TypeScript / Expo / React Native) generates the UI and calls these endpoints.
- **Claude Code** (Python / FastAPI / LangGraph) implements these endpoints in `mvc-pipeline`.

When the spec and the implementation disagree, **the spec wins**. Change the spec first, then the implementation. PRs that change endpoint shape without updating `openapi.yaml` are rejected.

---

## 1. Versioning and base URL

- **Base path**: `/v1`
- **Staging**: `https://mvc-pipeline-staging.fly.dev/v1`
- **Production**: `https://mvc-pipeline.fly.dev/v1` (post-launch)
- **Breaking changes**: bump to `/v2`. The `/v1` surface stays live for at least 90 days after `/v2` ships.
- **Non-breaking changes** (adding optional fields, new endpoints, new enum values consumers can ignore): no version bump, but every release notes entry must call them out.

---

## 2. Authentication

Every endpoint except `GET /v1/health` requires a Supabase Auth JWT.

```http
Authorization: Bearer <supabase_access_token>
```

- **Token issuer**: `https://<supabase-project-ref>.supabase.co/auth/v1`
- **Audience**: `authenticated`
- **Algorithm**: `RS256`, verified against the JWKS at `https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json`
- **Claim used for identity**: `sub` (a UUID matching `auth.users.id`)
- **On the Rork client**: use `@supabase/supabase-js` with the Expo session storage adapter; call `supabase.auth.getSession()` and attach `session.access_token` to every request. The Supabase client refreshes the token automatically; no manual refresh logic needed on the client.

**Failures:**
- Missing or malformed `Authorization` header → `401 Unauthorized`
- Expired token → `401 Unauthorized` with body `{"error":{"code":"token_expired","message":"..."}}` — the client must call `supabase.auth.refreshSession()` and retry once.
- Valid token but resource not owned by the caller → `404 Not Found` (never `403`, to avoid existence-leak).

---

## 3. Conventions

### 3.1 Content type
- All request and response bodies are `application/json` unless noted (R2 uploads use `multipart/form-data` via signed URLs minted by `POST /v1/uploads/sign`).

### 3.2 Identifiers
- All IDs are UUIDs (RFC 4122 v4), serialized as strings.
- Server generates IDs; clients never pass them on `POST`.

### 3.3 Timestamps
- All timestamps are ISO 8601 with timezone, always UTC, microsecond precision: `2026-05-11T14:32:01.123456Z`.

### 3.4 Pagination
- List endpoints accept `?limit=<int, default 50, max 100>` and `?cursor=<opaque string>`.
- Responses include `{"items": [...], "next_cursor": "..."}`. When `next_cursor` is absent, the list is exhausted.
- Cursors are opaque; clients must not parse them.

### 3.5 Idempotency
- Every `POST` accepts an optional `Idempotency-Key` header (UUID, client-generated).
- Within a 24-hour window, replaying the same `Idempotency-Key` from the same user returns the original response with `Idempotency-Replayed: true` set.
- The Rork client SHOULD send an `Idempotency-Key` on every `POST` that creates state (`/pipelines`, `/pipelines/{id}/runs`, `/uploads/sign`). It MAY omit it on `PATCH` and `DELETE`.

### 3.6 Error shape
Every error response has this body:

```json
{
  "error": {
    "code": "snake_case_error_code",
    "message": "Human-readable message safe to show in the UI.",
    "details": { "...": "optional structured context" },
    "request_id": "uuid-from-X-Request-ID-header"
  }
}
```

Codes the Rork client should know how to display:
- `token_expired` → silent refresh + retry
- `validation_failed` → show field errors from `details.fields`
- `pipeline_not_found`, `run_not_found` → show "not found" state
- `tier_limit_exceeded` → show upgrade modal; `details.limit` and `details.tier` populated
- `safety_block_in_progress` → show a banner; not a real error, just informational
- `internal_error` → show generic "something went wrong" + the `request_id` for support

### 3.7 Request tracing
- Every response includes `X-Request-ID: <uuid>`. The Rork client SHOULD log this with any client-side error. Sentry on the client and server share this ID to make crash correlation possible.

### 3.8 Rate limiting
- Per-user, per-endpoint, sliding window. Defaults:
  - `POST /v1/pipelines`: 10/min
  - `POST /v1/pipelines/{id}/runs`: 20/min
  - All others: 60/min
- On limit hit: `429 Too Many Requests` with `Retry-After` header.

---

## 4. Endpoints (overview)

The authoritative shapes live in `openapi.yaml`. This section is a human map.

### 4.1 Health
| Method | Path | Purpose |
|---|---|---|
| GET | `/v1/health` | Liveness probe. Unauthenticated. Returns `{status,version,env}`. |

### 4.2 Pipelines
| Method | Path | Purpose |
|---|---|---|
| POST | `/v1/pipelines` | Create a pipeline from a theme + autonomy + settings. |
| GET | `/v1/pipelines` | List the caller's pipelines (paginated). |
| GET | `/v1/pipelines/{id}` | Fetch one pipeline. 404 if not owned. |
| PATCH | `/v1/pipelines/{id}` | Update settings (pause/resume, cadence, autonomy, safety toggles). |
| DELETE | `/v1/pipelines/{id}` | Soft-delete a pipeline. Existing clips remain. |

### 4.3 Runs
| Method | Path | Purpose |
|---|---|---|
| POST | `/v1/pipelines/{id}/runs` | Trigger a new run. Returns `{run_id, status:"queued"}`. |
| GET | `/v1/pipelines/{id}/runs` | List runs for a pipeline (paginated). |
| GET | `/v1/runs/{run_id}` | Fetch run state including the final `PipelineState` snapshot. |

### 4.4 Sources
| Method | Path | Purpose |
|---|---|---|
| POST | `/v1/uploads/sign` | Mint a signed R2 upload URL for a user-supplied video. |
| POST | `/v1/pipelines/{id}/sources` | Register a source (post-upload or external URL). |
| DELETE | `/v1/pipelines/{id}/sources/{source_id}` | Remove a source from a pipeline. |

### 4.5 Clips
| Method | Path | Purpose |
|---|---|---|
| GET | `/v1/clips` | List clips for the caller (filterable by `pipeline_id`, `status`). |
| GET | `/v1/clips/{id}` | Fetch one clip with captions, posts, metrics, safety tags. |
| POST | `/v1/clips/{id}/approve` | Approve a clip (Approve-Each autonomy mode). |
| POST | `/v1/clips/{id}/reject` | Reject a clip. |
| POST | `/v1/clips/{id}/remix` | Trigger a remix (re-run Editor + Captioner with new parameters). |

### 4.6 Connected accounts
| Method | Path | Purpose |
|---|---|---|
| GET | `/v1/connected-accounts` | List the caller's connected social accounts. |
| POST | `/v1/connected-accounts/oauth/start` | Begin OAuth for a platform; returns a URL the app opens. |
| POST | `/v1/connected-accounts/oauth/callback` | OAuth callback intake (also reachable as a webhook). |
| DELETE | `/v1/connected-accounts/{id}` | Disconnect a social account. |

### 4.7 Webhooks (inbound)
| Method | Path | Purpose |
|---|---|---|
| POST | `/v1/webhooks/aggregator` | Aggregator posting callbacks (post status, metrics). Stub in Week 4; real in Week 7+. |
| POST | `/v1/webhooks/stripe` | Stripe subscription / invoice events. Stub in Week 4; real in Week 10. |

Webhooks are not protected by Supabase Auth. They use HMAC signature verification (`X-Signature` header) — the secret is set per-aggregator and stored in Fly secrets.

---

## 5. Data shapes (high-level)

Full JSON Schemas live in `openapi.yaml`. This is the mental model:

### Pipeline
```
{
  "id": uuid,
  "user_id": uuid,
  "theme": string,
  "autonomy_mode": "full_auto" | "approve_each" | "suggest_only",
  "clipper_friendly_resolver_enabled": bool,
  "retention_days": 30 | 90 | 36500,
  "safety_overrides": {
    "news_political": "warn" | "block",
    "health": "warn" | "block",
    "finance": "warn" | "block",
    "childrens": "warn" | "block",
    "identifiable_individual": "warn" | "block",
    "violent_graphic": "warn" | "block"
  },
  "cadence": {
    "clips_per_day_max": int,
    "platforms": ["tiktok" | "instagram_reels" | "youtube_shorts"]
  },
  "source_plan": {
    "source_types": ["upload" | "creator_licensed" | "cc_archive"]
  },
  "status": "running" | "paused" | "errored",
  "created_at": iso8601,
  "updated_at": iso8601
}
```

### Run
```
{
  "id": uuid,
  "pipeline_id": uuid,
  "status": "queued" | "running" | "succeeded" | "failed",
  "started_at": iso8601 | null,
  "finished_at": iso8601 | null,
  "error": string | null,
  "summary": {
    "source_assets_count": int,
    "moments_count": int,
    "clips_count": int,
    "blocked_clips_count": int,
    "posts_count": int
  },
  "state_snapshot": PipelineState | null  // null until status="succeeded"
}
```

### Clip
```
{
  "id": uuid,
  "pipeline_id": uuid,
  "moment_id": uuid,
  "output_url": string,            // R2 signed URL, expires in 1h, request a new one to refresh
  "thumbnail_url": string,
  "status": "rendered" | "blocked" | "posted" | "rejected",
  "safety_tags": [SafetyTag],
  "captions": [CaptionVariant],
  "posts": [Post],
  "metrics_summary": {
    "total_views": int,
    "total_engagement": int,
    "earnings_cents": int
  },
  "source_attribution": {
    "source_asset_id": uuid,
    "source_type": "upload" | "creator_licensed" | "cc_archive",
    "external_url": string | null,
    "attribution_text": string
  },
  "created_at": iso8601
}
```

---

## 6. Working with the contract

### 6.1 Authoring flow

1. **Spec change first.** Edit `openapi.yaml`. Open a PR titled `spec: <what changed>`.
2. **Two reviewers, two diffs.** The Rork side reviews for "can the mobile app consume this?"; the FastAPI side reviews for "can we implement this?"
3. **Merge the spec.** Only then do server and client implementations begin.
4. **Both sides regenerate types** from the merged spec (see §6.2). PRs that don't regenerate fail CI.

### 6.2 Codegen on both sides

**FastAPI side** (`mvc-pipeline` repo):
- Pydantic models are the source of truth for the implementation. They are **manually written** to match `openapi.yaml`, not generated, because `mypy --strict` rejects most auto-generated Python and Pydantic gives nicer ergonomics for validators.
- A contract test (`tests/test_openapi_alignment.py`) compares the FastAPI-generated OpenAPI document with the committed `openapi.yaml`. CI fails if they drift.

**Rork side** (mobile app repo):
- Run `openapi-typescript openapi.yaml -o src/api/types.ts` to regenerate TypeScript types.
- Use a thin fetch wrapper around those types — no SDK dependency, no client codegen beyond the types themselves. This keeps the Rork-generated code reviewable.
- The wrapper handles: bearer token attachment, `Idempotency-Key` generation, `X-Request-ID` capture into Sentry breadcrumbs, single retry on `401 token_expired` after `supabase.auth.refreshSession()`.

### 6.3 Mocking the contract

- A **mock server** (`scripts/mock_api.py` in `mvc-pipeline`) serves canned responses for every endpoint. Rork can develop against it before any real backend exists.
- The mock server reads from `tests/fixtures/api_responses/*.json` — same fixtures the contract tests use. One source of truth for "what the contract says a response looks like."
- The Rork app's `.env.development` points to the mock server URL by default. Switching to the real staging API is one env-var change.

### 6.4 Out-of-band changes

If you discover the server needs to send something the contract doesn't allow (an enum value, a new field), **do not just add it**. Open a spec PR. The cost of a 30-minute spec turnaround is far less than the cost of the Rork app silently breaking because an unknown field crashed a Zod validator.

### 6.5 Things that are NOT in this contract

The contract is HTTP only. These things live elsewhere:
- **Realtime updates** — initially the Rork app polls `GET /v1/runs/{run_id}` and `GET /v1/clips`. Post-MVP, Supabase Realtime channels surface pipeline status changes directly from Postgres; that contract lives in a separate `REALTIME_CONTRACT.md` when added.
- **Push notifications** — Expo push tokens are registered via `POST /v1/users/me/push-token` (covered here), but the actual notification payloads are documented in `PUSH_PAYLOADS.md` (not yet written; lands when notifications wire up).
- **Direct R2 access** — the app uploads videos directly to R2 using signed URLs minted by `POST /v1/uploads/sign`. The R2 PUT request itself is governed by AWS's S3 API, not this contract.

---

## 7. Open questions for resolution before Week 4

Tracked here, not in code, until decided. Each must be answered before the Week 4 PR merges.

1. **Source URL submission for MVP** — `mvp-build-spec.md` defers user-supplied URLs from the MVP UI. The endpoint `POST /v1/pipelines/{id}/sources` accepts `source_type: "user_url"` for completeness, but should the API reject it with `403 feature_disabled` when called in MVP, or should it accept and queue? **Default**: accept, queue, but UI doesn't expose it. Confirm.

2. **Realtime vs. polling for run status** — for the MVP the Rork app polls `GET /v1/runs/{run_id}` every 5 seconds while a run is active. Acceptable? Or wire Supabase Realtime in Week 4 from the start? **Default**: polling for MVP, Realtime post-MVP.

3. **Signed URL expiry for clip playback** — current spec says 1 hour. Long enough for a user to browse and view? If a user opens a clip detail screen and walks away for 2 hours, then taps play, we serve a stale URL. **Default**: 1 hour with a `clip-refresh` endpoint the client calls on 403 from R2. Confirm.

4. **Per-platform metrics shape** — `metrics_summary` aggregates across platforms in the clip object. For the per-platform breakdown, do we add `metrics_by_platform` to the clip detail response, or a separate `GET /v1/clips/{id}/metrics` endpoint? **Default**: include inline on `GET /v1/clips/{id}` because the per-clip detail screen always shows the breakdown.
