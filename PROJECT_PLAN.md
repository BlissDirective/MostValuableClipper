# MVC — Master Video Clips
## Unified Project Plan

> **Product:** An AI-powered creator autopilot that turns any content theme into an automated short-form video pipeline.
> **Repos Merged:** `mvc-pipeline` (architecture/planning) + `rork-ai-MVC-UI` (React Native frontend)

---

## 1. Product Vision

**One-line pitch:** Turn any theme into a clip pipeline — AI finds the content, edits it, checks safety, posts it, and tells you how much you earned.

**The user journey:**
1. A creator says "I want clips about design podcasts"
2. AI finds the best sources (RSS feeds, YouTube channels, licensed content)
3. AI generates short-form clips with optimized captions, hooks, and hashtags
4. AI checks every clip against safety/compliance rules
5. Creator approves (or auto-posts) via a swipe-deck UI
6. AI posts to TikTok, Instagram Reels, YouTube Shorts
7. AI monitors performance, optimizes strategy, and tracks earnings

**Key insight:** Most creators spend 80% of their time on sourcing, editing, compliance, and distribution — not creating. MVC automates all of it.

---

## 2. System Architecture

### 2.1 High-Level Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Creator   │────▶│  Mobile App │────▶│  Supabase   │
│   (Human)   │◀────│  (React Nat)│◀────│   (DB+Auth) │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                    ┌──────────────────────────┘
                    ▼
           ┌─────────────────┐
           │  FastAPI Backend │
           │  (Python)       │
           └────────┬────────┘
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐
   │  AI     │ │ Cloud   │ │  Social │
   │ Agents  │ │  Infra  │ │  APIs   │
   │(Claude) │ │(CF/R2)  │ │(TT/IG/YT│
   └─────────┘ └─────────┘ └─────────┘
```

### 2.2 AI Agent System (7 Agents)

| Agent | Responsibility | Trigger |
|-------|---------------|---------|
| **ContentAgent** | Scans sources, identifies viral-worthy moments, generates clip proposals | Scheduled (every 15min per pipeline) |
| **SourceAgent** | Manages source catalog (add/remove/verify), resolves creator handles | User action or ContentAgent request |
| **SafetyAgent** | Scans every clip for policy violations, copyright, misinformation | Every generated clip |
| **StrategyAgent** | Optimizes posting schedule, trending hashtags, platform-specific format | Every post window, weekly review |
| **MonitorAgent** | Tracks clip performance, flagging underperformers, A/B test results | Every 6 hours |
| **EarningsAgent** | Aggregates revenue, estimates CPM, calculates creator payouts | Daily |
| **DirectorAgent** | Orchestrates all agents, manages queues, handles errors, escalates | Always running |

### 2.3 Tech Stack

**Frontend (Mobile + Web):**
- React Native with Expo (SDK 54)
- expo-router for navigation
- Zustand for state management
- TanStack Query for server state
- lucide-react-native for icons
- Dark-first design system with typed tokens

**Backend:**
- Python 3.12 + FastAPI
- Supabase (PostgreSQL + Auth)
- Upstash Redis (caching, sessions)
- Cloudflare Workers (edge processing)
- Cloudflare R2 (media storage)
- Anthropic Claude 4 Sonnet (AI orchestration)

**Social Platform APIs:**
- TikTok Research API
- Instagram Graph API
- YouTube Data + YouTube Partner API

**Infrastructure:**
- Vercel (frontend web deployment)
- Cloudflare Workers (backend edge)
- Stripe (payments)
- Sentry (error tracking)

---

## 3. Database Schema (Supabase)

### Core Tables

```sql
-- Users & Authentication (managed by Supabase Auth)
profiles (id, email, display_name, avatar_url, timezone, created_at)

-- Creator accounts linked to social platforms
accounts (id, user_id, platform, handle, followers, access_token, refresh_token, token_expires, eligible, created_at)

-- Content pipelines (themes)
pipelines (id, user_id, theme_name, niche, status, clips_per_day, autonomy, retention, created_at, updated_at)

-- Sources feeding a pipeline
sources (id, pipeline_id, kind, name, url, status, last_scanned, created_at)

-- Generated clips
clips (id, pipeline_id, source_id, status, caption, transcript, video_url, thumbnail_url, platforms, scheduled_for, posted_at, created_at)

-- Safety reviews
safety_reviews (id, clip_id, status, categories, action_taken, reviewed_at, created_at)

-- Performance metrics (from MonitorAgent)
metrics (id, clip_id, platform, views, likes, comments, shares, retention_rate, earnings, recorded_at)

-- Earnings payouts
earnings (id, user_id, period_start, period_end, total_views, estimated_cpm, gross_revenue, platform_fees, net_payout, status, created_at)

-- Cohort data (anonymized for research)
cohort_data (id, pipeline_id, clip_count, view_count, earnings, retention_strategy, created_at)
```

---

## 4. API Contract Summary

All endpoints follow RESTful conventions with JWT Bearer auth.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | System health check |
| `/users` | POST | Create account |
| `/users/auth` | POST | Sign in (Supabase) |
| `/users/me` | GET | Current user profile |
| `/clips` | GET | List clips (paginated) |
| `/clips` | POST | Generate clip (manual) |
| `/clips/{id}/action` | POST | Approve/reject/boost/kill |
| `/pipelines` | GET | List pipelines |
| `/pipelines` | POST | Create pipeline |
| `/pipelines/{id}` | PATCH | Update pipeline |
| `/pipelines/{id}/run` | POST | Trigger manual run |
| `/sources/search` | GET | Search content sources |
| `/sources` | POST | Add source |
| `/sources/resolve` | POST | Resolve creator handle |
| `/earnings` | GET | Get earnings summary |
| `/earnings/payout` | POST | Request payout |
| `/webhooks/tiktok` | POST | TikTok webhook |
| `/webhooks/stripe` | POST | Stripe webhook |

Full spec in `docs/API_CONTRACT.md`.

---

## 5. Frontend Screens (Expo Router)

### Auth Flow
1. `/welcome` — Brand intro, create account or sign in
2. `/theme-input` — "What do you want to clip?"
3. `/connect-accounts` — Link TikTok, Instagram, YouTube
4. `/autonomy` — Choose autopilot level (full auto / approve each / suggest only)
5. `/cohort-opt-in` — Opt into anonymized research cohort
6. `/onboarding` — Completion summary

### Main App (Tab Navigation)
1. `/` (Home) — Live feed of clips, approval banner, status strip
2. `/pipelines` — List of active pipelines
3. `/insights` — Performance analytics, AI recommendations
4. `/earnings` — Revenue tracking, payout requests
5. `/profile` — Account settings, billing, preferences

### Sub-Screens
- `/clip/{id}` — Clip detail with safety review
- `/pipelines/{id}` — Pipeline detail with controls
- `/pipelines/new` — Create new pipeline
- `/approval` — Swipe-deck approval queue
- `/profile/settings` — App settings
- `/profile/billing` — Payment methods & history

---

## 6. Design System

**Theme:** Dark-first, high-contrast, confident-saturated

**Color Palette:**
- Background: `#0A0E1A` (base) → `#10162A` (raised) → `#161D38` (surface)
- Primary: `#4256F5` (indigo)
- Secondary: `#0FA39A` (teal)
- Success: `#1FCB8C`
- Warning: `#F0B438`
- Danger: `#F25555`
- Text: `#F4F6FF` (primary) → `#A8B0CC` (secondary) → `#6B7494` (tertiary)

**Typography:** Inter font family (400/500/600/700)
- Display: 32px bold
- H1: 24px bold
- H2: 20px semibold
- Body: 16px regular
- Caption: 12px medium

**Components:**
- ActionButton (primary/secondary/ghost/danger)
- ClipCard (feed/detail/queue variants)
- PipelineRow (status + metrics)
- MetricChip (with delta indicators)
- SafetyFlag (warn/block/review/general)
- AccountBadge (platform indicators)
- InsightTile (AI recommendations)
- SwipeDeckCard (approval queue)

Full component spec in `docs/component-spec.md`.

---

## 7. Current State Assessment

### ✅ What's Done
- **Frontend UI:** ~95% of screens and components are built with placeholder data
- **Design System:** Complete token system, consistent dark theme across all screens
- **Navigation:** Full expo-router structure with auth + tab flows
- **State Management:** Zustand store with pipeline, auth, and onboarding state
- **Component Library:** 8 core components with full props and styling
- **Haptics:** Integrated with expo-haptics
- **Type Safety:** Full TypeScript throughout

### ❌ What's Missing
- **Backend API:** All endpoints are stubs — no real implementation
- **Database:** Schema defined but not deployed to Supabase
- **Auth Integration:** Frontend has console.log stubs for Supabase auth
- **AI Agents:** Spec'd but not implemented
- **Social Platform APIs:** No TikTok/Instagram/YouTube integration
- **Real Data:** Every screen uses placeholder/mock data
- **Video Processing:** No actual clip generation or editing
- **Payment:** Stripe integration not started
- **Deployment:** No CI/CD, no hosting configured

### 🔧 The Gap
The frontend is a beautiful, functional shell. The backend is a detailed blueprint. What connects them is the API layer — and that's entirely missing. Every `CLAUDE_CODE:` comment in the frontend marks a place where a real API call should live.

---

## 8. Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Social API rate limits / policy changes | High | High | Abstract platform layer, graceful degradation |
| AI hallucination in clip generation | Medium | High | SafetyAgent mandatory review, human-in-the-loop |
| Copyright claims on generated clips | Medium | High | SourceAgent verifies licensing, watermark system |
| Backend costs scaling unexpectedly | Medium | Medium | Usage caps, tiered pricing, queue throttling |
| Mobile performance with video | Medium | Medium | Lazy loading, video compression, CDN delivery |
| Creator account bans (false positives) | Low | Critical | Aggressive safety defaults, appeal process |

---

## 9. Success Metrics (MVC Definition)

**Technical:**
- End-to-end clip generation < 5 minutes
- 99.5% uptime for posting window
- Safety review accuracy > 95%

**Business:**
- Creator NPS > 50
- Average clips per pipeline: 10/week
- Average earnings per creator: $200/month

**Research:**
- Cohort retention strategy data: 10,000+ clips analyzed
- Published paper or open dataset

---

*This plan was generated on 2026-05-14 after merging two repositories and analyzing 40+ files across architecture docs, API contracts, component specs, and a complete React Native frontend codebase.*
