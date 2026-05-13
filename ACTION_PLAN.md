# MVC Action Plan
## Autonomous Development Roadmap

> **How to use this:** Work top-to-bottom, one phase at a time. Each phase has specific files to edit and clear acceptance criteria. When a phase is complete, check it off and move to the next.
>
> **Mobile-first constraint:** All development happens via SSH/cloud IDE or by editing files directly. No local Android Studio/Xcode required for frontend work.

---

## Phase 0: Project Setup ✅

**Goal:** Unified repo structure ready for development.

**Status:** DONE — Two repos merged into `mvc-combined/` with:
- `docs/` — All planning documents (mvp-build-spec, API_CONTRACT, component-spec, design tokens, Claude.md)
- `frontend/` — Complete React Native Expo app (from rork-ai-MVC-UI)
- `backend/` — FastAPI scaffold with router stubs

---

## Phase 1: Backend Foundation (Week 1)

**Goal:** Backend boots, connects to Supabase, serves health endpoint, has working auth.

### 1.1 Supabase Schema Deployment
**Files to edit:**
- `backend/supabase/migrations/001_initial_schema.sql` (CREATE)
- `backend/supabase/seed.sql` (optional test data)

**Tasks:**
1. Create SQL migration with all tables from PROJECT_PLAN §3
2. Include Row Level Security (RLS) policies:
   - Users can only read/write their own pipelines
   - Users can only read/write their own clips
   - Earnings are user-scoped
3. Deploy to Supabase project via SQL Editor or CLI
4. Enable Supabase Auth (Email + OAuth providers)

**Acceptance:**
- `supabase db reset` successfully creates all tables
- RLS policies enforced (test with anon key vs service key)

### 1.2 Backend Configuration
**Files to edit:**
- `backend/.env` (local secrets)
- `backend/app/core/config.py` (validate env vars)
- `backend/app/core/database.py` (Supabase client wrapper)

**Tasks:**
1. Add Supabase client initialization to `database.py`
2. Add JWT validation using Supabase JWT secret
3. Add dependency injection for auth: `get_current_user()`

**Acceptance:**
- `uvicorn app.main:app --reload` boots without errors
- `GET /health` returns `{"status": "ok"}`
- `GET /users/me` with invalid JWT returns 401
- `GET /users/me` with valid JWT returns user profile

### 1.3 Auth API Implementation
**Files to edit:**
- `backend/app/api/users.py`
- `backend/app/models/user.py`

**Tasks:**
1. Implement `POST /users` — create profile in Supabase
2. Implement `POST /users/auth` — sign in via Supabase Auth
3. Implement `GET /users/me` — fetch current profile
4. Implement `PATCH /users/me` — update profile

**Acceptance:**
- Can create user via API
- Can sign in and receive JWT
- JWT works on all protected endpoints
- Tests pass: `pytest tests/test_users.py`

---

## Phase 2: Core Data APIs (Week 1-2)

**Goal:** CRUD APIs for pipelines, clips, and sources. Frontend can read/write real data.

### 2.1 Pipeline API
**Files to edit:**
- `backend/app/api/pipelines.py`
- `backend/app/models/pipeline.py`

**Tasks:**
1. `GET /pipelines` — list user's pipelines with pagination
2. `POST /pipelines` — create new pipeline (trigger SourceAgent)
3. `GET /pipelines/{id}` — get pipeline detail with sources
4. `PATCH /pipelines/{id}` — update settings (autonomy, retention, clips/day)
5. `DELETE /pipelines/{id}` — soft delete
6. `POST /pipelines/{id}/run` — trigger manual pipeline run

**Acceptance:**
- Create → Read → Update → Delete cycle works via curl/API client
- Tests pass: `pytest tests/test_pipelines.py`

### 2.2 Clip API
**Files to edit:**
- `backend/app/api/clips.py`
- `backend/app/models/clip.py`

**Tasks:**
1. `GET /clips` — list clips with filters (status, pipeline, date range)
2. `POST /clips` — manual clip creation (upload video)
3. `GET /clips/{id}` — full clip detail with metrics
4. `POST /clips/{id}/action` — approve/reject/boost/kill/replicate
5. `GET /clips/approval-queue` — pending clips for review

**Acceptance:**
- Can list, create, and action clips via API
- Approval queue returns only `pending_review` clips
- Tests pass: `pytest tests/test_clips.py`

### 2.3 Source API
**Files to edit:**
- `backend/app/api/sources.py`
- `backend/app/models/source.py`
- `backend/app/services/source_search.py`

**Tasks:**
1. `GET /sources/search?q={query}` — search YouTube, RSS, podcasts
2. `POST /sources` — add source to pipeline
3. `POST /sources/resolve` — resolve creator handle to platform ID
4. `DELETE /sources/{id}` — remove source

**Acceptance:**
- Source search returns relevant results
- Can add/remove sources from pipeline
- Tests pass: `pytest tests/test_sources.py`

---

## Phase 3: AI Agent System (Week 2-3)

**Goal:** The core value engine. AI agents generate clips, check safety, optimize strategy.

### 3.1 ContentAgent
**Files to create:**
- `backend/app/agents/content_agent.py`
- `backend/app/services/video_processor.py`

**Tasks:**
1. Scan pipeline sources (RSS, YouTube API, uploaded files)
2. Identify viral-worthy moments using heuristics:
   - High engagement segments (likes/comments spikes)
   - Transcript analysis for quotable moments
   - Duration sweet spot detection (15-60s)
3. Generate clip proposals with:
   - Start/end timestamps
   - Suggested caption with hook
   - Platform-specific hashtags
   - Predicted reach/retention

**Acceptance:**
- Given a YouTube URL, returns 3-5 clip proposals
- Each proposal has timestamps, caption, hashtags
- Processing time < 30s per source

### 3.2 SafetyAgent
**Files to create:**
- `backend/app/agents/safety_agent.py`

**Tasks:**
1. Scan clip proposals for policy violations:
   - Copyright material detection
   - Misinformation flags (news/health/finance)
   - Identifiable individuals (privacy)
   - Graphic/violent content
   - Children-facing content
2. Categorize risk level: `general` | `warn` | `block` | `review`
3. Auto-generate disclosure text for `warn` clips
4. Flag `block` clips for human review

**Acceptance:**
- Known problematic content correctly flagged
- False positive rate < 5% (measured on test set)
- Each flagged clip has specific category and action

### 3.3 StrategyAgent
**Files to create:**
- `backend/app/agents/strategy_agent.py`

**Tasks:**
1. Determine optimal posting schedule per platform:
   - TikTok: 6-10pm weekdays, 9-11am weekends
   - Instagram: 11am-1pm, 7-9pm
   - YouTube: 2-4pm, 8-10pm
2. Adjust based on creator's timezone and audience analytics
3. A/B test caption variants
4. Trending hashtag injection
5. Retention policy execution (aggressive/moderate/indefinite)

**Acceptance:**
- Generates posting schedule for next 7 days
- Schedule respects platform best practices + creator timezone
- Can adjust based on performance feedback

### 3.4 DirectorAgent (Orchestrator)
**Files to create:**
- `backend/app/agents/director_agent.py`
- `backend/app/services/scheduler.py`

**Tasks:**
1. Coordinate all agents via message queue
2. Schedule recurring jobs:
   - ContentAgent: every 15 min per active pipeline
   - StrategyAgent: every post window, weekly review
   - MonitorAgent: every 6 hours
   - EarningsAgent: daily at midnight
3. Handle failures with exponential backoff
4. Escalate `block` safety flags to human review queue
5. Maintain job queue state in Redis

**Acceptance:**
- All agents run on schedule without manual intervention
- Failed jobs retry with backoff (max 5 attempts)
- Queue state visible via API: `GET /admin/queue-status`

### 3.5 SourceAgent (Bonus - Phase 3.5)
**Files to create:**
- `backend/app/agents/source_agent.py`

**Tasks:**
1. Maintain source catalog per pipeline
2. Verify source freshness (last post date)
3. Handle source failures (remove after 3 consecutive failures)
4. Suggest new sources based on theme similarity

### 3.6 MonitorAgent (Bonus - Phase 3.5)
**Files to create:**
- `backend/app/agents/monitor_agent.py`

**Tasks:**
1. Poll platform APIs for clip performance
2. Update metrics table (views, likes, comments, shares, retention)
3. Flag underperforming clips (< 50% of predicted reach)
4. Generate insight recommendations for StrategyAgent

### 3.7 EarningsAgent (Bonus - Phase 3.5)
**Files to create:**
- `backend/app/agents/earnings_agent.py`

**Tasks:**
1. Aggregate daily metrics into earnings estimates
2. Calculate CPM by platform and niche
3. Generate payout-ready summaries
4. Handle Stripe payout initiation

---

## Phase 4: Video Pipeline (Week 3-4)

**Goal:** Actually download, edit, and produce video clips.

### 4.1 Video Download
**Files:**
- `backend/app/services/video_downloader.py`

**Tasks:**
1. YouTube video download (yt-dlp)
2. RSS media enclosure download
3. Uploaded file handling (R2 presigned URLs)
4. Store raw media in R2 with pipeline-scoped paths

### 4.2 Video Processing
**Files:**
- `backend/app/services/video_editor.py`

**Tasks:**
1. FFmpeg-based clip extraction (start/end timestamps)
2. Aspect ratio conversion (9:16 for Shorts/Reels/TikTok)
3. Caption burn-in (optional)
4. Watermark overlay (MVC brand + creator handle)
5. Thumbnail generation
6. Output to R2 in platform-specific formats

### 4.3 Quality Gate
**Files:**
- `backend/app/services/quality_gate.py`

**Tasks:**
1. Duration validation (15-90s)
2. Resolution check (min 720p)
3. Audio level normalization
4. Auto-reject if file size > 100MB

---

## Phase 5: Social Platform Integration (Week 4-5)

**Goal:** Post clips to TikTok, Instagram, YouTube automatically.

### 5.1 Platform Abstraction Layer
**Files:**
- `backend/app/services/platforms/base.py` (abstract)
- `backend/app/services/platforms/tiktok.py`
- `backend/app/services/platforms/instagram.py`
- `backend/app/services/platforms/youtube.py`

**Tasks:**
1. Common interface: `upload(video, caption, hashtags, schedule)`
2. Platform-specific formatting:
   - TikTok: 9:16, max 3min, hashtag limit
   - Instagram: Reels format, caption length limit
   - YouTube: Shorts format, title + description + tags

### 5.2 TikTok Integration
**Tasks:**
1. OAuth 2.0 flow for creator account linking
2. Research API for analytics
3. Publish API for posting (or direct upload workaround)
4. Webhook handling for post status

### 5.3 Instagram Integration
**Tasks:**
1. Facebook Login → Instagram Graph API
2. Reels publishing API
3. Stories cross-post (optional)
4. Analytics polling

### 5.4 YouTube Integration
**Tasks:**
1. Google OAuth → YouTube Data API
2. Shorts upload (must be < 60s, vertical)
3. Title, description, tags, category
4. YouTube Partner API for monetization data

---

## Phase 6: Frontend Integration (Week 5-6)

**Goal:** Connect the beautiful UI to real APIs. Replace all `CLAUDE_CODE:` stubs.

### 6.1 API Client Setup
**Files:**
- `frontend/lib/api.ts` (create)
- `frontend/lib/queryClient.ts` (create)

**Tasks:**
1. Configure TanStack Query client
2. Create typed API client with interceptors:
   - Attach JWT from Supabase session
   - Refresh token on 401
   - Rate limit handling
3. Environment-based base URL (dev/staging/prod)

### 6.2 Auth Wiring
**Files:**
- `frontend/lib/auth.ts` (create)
- `frontend/app/(auth)/welcome.tsx`
- `frontend/app/(auth)/theme-input.tsx`

**Tasks:**
1. Replace `console.log` stubs with Supabase auth calls
2. `handleCreate` → `supabase.auth.signUp()`
3. `handleSignIn` → `supabase.auth.signInWithPassword()`
4. Onboarding state persists to backend via `POST /users`

### 6.3 Home Feed Wiring
**Files:**
- `frontend/app/(app)/index.tsx`
- `frontend/components/ClipCard.tsx`

**Tasks:**
1. Replace `PLACEHOLDER_CLIPS` with `useQuery(['clips'])`
2. Pull-to-refresh triggers `refetch()`
3. Clip actions (boost, replicate, kill) call `POST /clips/{id}/action`
4. Approval banner shows real pending count from `GET /clips/approval-queue`

### 6.4 Pipeline Management Wiring
**Files:**
- `frontend/app/(app)/pipelines.tsx`
- `frontend/app/(app)/pipelines/[id].tsx`
- `frontend/app/(app)/pipelines/new.tsx`

**Tasks:**
1. Pipeline list from `GET /pipelines`
2. Pipeline detail with real sources and settings
3. Create pipeline triggers `POST /pipelines` then `POST /sources`
4. Status changes (play/pause/delete) call PATCH/DELETE

### 6.5 Approval Queue Wiring
**Files:**
- `frontend/app/(app)/approval.tsx`

**Tasks:**
1. Load queue from `GET /clips/approval-queue`
2. Approve/Reject call `POST /clips/{id}/action`
3. Edit opens caption editor (modal)
4. After queue empty, show "Queue clear" state

### 6.6 Insights Wiring
**Files:**
- `frontend/app/(app)/insights.tsx`

**Tasks:**
1. Real metrics from `GET /earnings` + clip performance data
2. Insight tiles generated from StrategyAgent recommendations
3. Chart data from MonitorAgent aggregates

### 6.7 Earnings Wiring
**Files:**
- `frontend/app/(app)/earnings.tsx`

**Tasks:**
1. Real earnings data from `GET /earnings`
2. Payout request triggers `POST /earnings/payout`
3. Connect to Stripe for payment processing

---

## Phase 7: Polish & Monetization (Week 6-7)

**Goal:** Production-ready app with payments, analytics, and cohort research.

### 7.1 Stripe Integration
**Files:**
- `backend/app/api/payments.py`
- `frontend/app/(app)/profile/billing.tsx`

**Tasks:**
1. Subscription tiers (Free / Pro / Studio)
2. In-app purchase flow
3. Webhook handling for subscription events
4. Usage-based billing for clip overages

### 7.2 Cohort Data Collection
**Files:**
- `backend/app/services/cohort_service.py`

**Tasks:**
1. Anonymized pipeline performance aggregation
2. Opt-in data export for research
3. Retention strategy A/B test framework

### 7.3 Push Notifications
**Files:**
- `frontend/lib/notifications.ts`

**Tasks:**
1. Expo Push notifications for:
   - Clip ready for approval
   - Safety flag triggered
   - Earnings milestone reached
   - Weekly performance summary

### 7.4 Performance Optimization
**Tasks:**
1. Video lazy loading in feed
2. Image CDN optimization
3. API response caching
4. Bundle size optimization

### 7.5 Deployment
**Tasks:**
1. Backend: Deploy to Cloudflare Workers or Fly.io
2. Frontend: EAS Build for iOS/Android + web via Vercel
3. Database: Supabase production project
4. Domain + SSL
5. Sentry error tracking
6. Analytics (PostHog or Amplitude)

---

## Quick Reference: File Map

### Frontend (React Native / Expo)
```
frontend/
  app/
    (app)/               ← Main app tabs
      _layout.tsx        ← Tab navigator
      index.tsx          ← Home feed
      approval.tsx       ← Swipe approval queue
      pipelines.tsx      ← Pipeline list
      pipelines/[id].tsx ← Pipeline detail
      pipelines/new.tsx  ← Create pipeline
      insights.tsx       ← Analytics
      earnings.tsx       ← Revenue
      clip/[id].tsx      ← Clip detail
      profile/           ← Profile sub-screens
    (auth)/              ← Auth flow
      _layout.tsx
      welcome.tsx
      theme-input.tsx
      connect-accounts.tsx
      autonomy.tsx
      cohort-opt-in.tsx
  components/
    ActionButton.tsx
    ClipCard.tsx
    PipelineRow.tsx
    MetricChip.tsx
    SafetyFlag.tsx
    AccountBadge.tsx
    InsightTile.tsx
    SwipeDeckCard.tsx
  constants/
    tokens.ts            ← Design tokens
  lib/
    store.ts             ← Zustand state
    templates.tsx        ← (missing — create for real data)
  utils/
    haptics.ts           ← Haptic feedback
```

### Backend (FastAPI)
```
backend/
  app/
    main.py              ← App entry point
    core/
      config.py          ← Settings
      database.py        ← Supabase client
      events.py          ← Startup/shutdown
      logging.py         ← Structlog config
    api/
      health.py          ← Health check
      users.py           ← Auth + profiles
      clips.py           ← Clip CRUD + actions
      pipelines.py       ← Pipeline CRUD
      sources.py         ← Source search + management
      earnings.py        ← Revenue + payouts
      webhooks.py        ← Platform webhooks
    agents/
      director_agent.py   ← Orchestrator
      content_agent.py    ← Clip generation
      safety_agent.py     ← Compliance checking
      strategy_agent.py   ← Post optimization
      monitor_agent.py    ← Performance tracking
      earnings_agent.py   ← Revenue calculation
      source_agent.py     ← Source management
    services/
      cache.py            ← Redis wrapper
      queue.py            ← Message queue
      video_downloader.py
      video_editor.py
      quality_gate.py
      platforms/
        base.py
        tiktok.py
        instagram.py
        youtube.py
    models/
      user.py
      pipeline.py
      clip.py
      source.py
      earnings.py
```

---

## Development Workflow (Mobile-Friendly)

Since you're building from a mobile device, here's the recommended flow:

1. **Edit files** directly in the cloud IDE (or via SSH + nano/vim)
2. **Test backend** with `curl` or a simple HTTP client app
3. **Test frontend** using `bunx rork start --web --tunnel` (runs in browser)
4. **Commit** with git after each working phase
5. **Push** to GitHub for backup
6. **Iterate** — complete one API endpoint at a time, test it, then wire the frontend

**Key commands:**
```bash
# Start backend
cd backend && uvicorn app.main:app --reload --port 8000

# Start frontend (web mode for mobile development)
cd frontend && bunx rork start --web --tunnel

# Run tests
cd backend && pytest

# Check types
cd frontend && npx tsc --noEmit
cd backend && mypy app/
```

---

*Action Plan v1.0 — Generated 2026-05-14*
*Next step: Begin Phase 1.1 (Supabase Schema)*
