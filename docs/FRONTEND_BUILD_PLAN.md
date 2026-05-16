# MVC Frontend Assessment & Build Plan

## Completed Infrastructure

| Item | Status | Details |
|------|--------|---------|
| Backend Deployment | ✅ LIVE | https://mvc-backend.fly.dev |
| GitHub Secrets | ✅ DONE | 23 secrets uploaded |
| Stripe Webhook | ✅ CONFIGURED | Endpoint: `we_1TXja4PWFs4prRS483WsKSp1` |
| Supabase DB | ✅ CONNECTED | Health check confirms connection |
| Upstash Redis | ✅ CONNECTED | Queue + cache ready |
| Cloudflare R2 | ✅ CONNECTED | Clip storage bucket ready |

---

## Frontend Code Assessment

### Architecture (Solid Foundation)

| Layer | Implementation | Quality |
|-------|----------------|---------|
| **Navigation** | Expo Router (file-based) | ✅ Clean tab + stack structure |
| **State** | Zustand (`lib/store.ts`) | ✅ Well-typed, atomic updates |
| **API Client** | `lib/api.ts` | ✅ Fully typed, auth-aware, error handling |
| **Data Hooks** | `lib/api-hooks.ts` | ✅ React Query + Zustand bridge |
| **Design System** | `constants/tokens.ts` | ✅ Consistent spacing, colors, typography |
| **Components** | `components/` | ✅ Reusable ClipCard, PipelineRow, etc. |

### Screens Inventory (14 Total)

| Screen | File | Status | Data Source |
|--------|------|--------|-------------|
| Welcome | `(auth)/welcome.tsx` | ✅ UI Complete | Static |
| Auth | `(auth)/autonomy.tsx` | ⚠️ Stubbed | Local only |
| Theme Input | `(auth)/theme-input.tsx` | ✅ UI Complete | Local store |
| Connect Accounts | `(auth)/connect-accounts.tsx` | ⚠️ Stubbed | Local store |
| Cohort Opt-in | `(auth)/cohort-opt-in.tsx` | ✅ UI Complete | Local store |
| Home/Dashboard | `(app)/index.tsx` | ✅ UI Complete | **PLACEHOLDER DATA** |
| Pipelines | `(app)/pipelines.tsx` | ✅ UI Complete | **PLACEHOLDER DATA** |
| Pipeline Detail | `(app)/pipelines/[id].tsx` | ⚠️ Partial | Local store |
| New Pipeline | `(app)/pipelines/new.tsx` | ⚠️ Partial | Local store |
| Approval Queue | `(app)/approval.tsx` | ✅ UI Complete | **PLACEHOLDER DATA** |
| Clip Detail | `(app)/clip/[id].tsx` | ⚠️ Partial | Local store |
| Profile | `(app)/profile/index.tsx` | ✅ UI Complete | **PLACEHOLDER DATA** |
| Billing | `(app)/profile/billing.tsx` | ✅ UI Complete | **PLACEHOLDER DATA** |
| Settings | `(app)/profile/settings.tsx` | ✅ UI Complete | Local store |

### Critical Gap: No Backend Connection

Every screen that should display real data currently uses:
- Hardcoded placeholder arrays (`PLACEHOLDER_CLIPS`, `seedPipelines`)
- `console.log()` stubs with `CLAUDE_CODE: wire to...` comments
- No actual API calls through the `api-hooks.ts` layer

---

## Backend API Status

| Endpoint | Router | Status | Note |
|----------|--------|--------|------|
| `GET /health` | `health.py` | ✅ Working | Returns service status |
| `GET /users/me` | `users.py` | ⚠️ Stub | Returns mock data |
| `GET /clips` | `clips.py` | ⚠️ Stub | Returns empty list |
| `POST /clips` | `clips.py` | ⚠️ Stub | No-op |
| `GET /pipelines` | `pipelines.py` | ⚠️ Stub | Returns empty list |
| `POST /pipelines` | `pipelines.py` | ⚠️ Stub | No-op |
| `GET /sources` | `sources.py` | ⚠️ Stub | Returns empty list |
| `GET /earnings` | `earnings.py` | ⚠️ Stub | Returns mock data |
| `GET /social/accounts` | `social.py` | ⚠️ Stub | Returns empty list |
| `GET /analytics/dashboard` | `analytics.py` | ⚠️ Stub | Returns mock data |
| `POST /webhooks/stripe` | `webhooks.py` | ✅ Configured | Handles Stripe events |
| `GET /privacy` | `legal.py` | ✅ Working | Static page served |
| `GET /terms` | `legal.py` | ✅ Working | Static page served |
| `GET /dmca` | `legal.py` | ✅ Working | Static page served |

---

## Build Plan: Frontend-Backend Integration

### Phase 1: Authentication (Priority: CRITICAL)

**Goal**: Real user signup/login with Supabase Auth

**Backend Tasks**:
1. Integrate Supabase Auth into FastAPI dependency (`get_current_user`)
2. Add JWT validation middleware
3. Create auth router: `/auth/register`, `/auth/login`, `/auth/refresh`

**Frontend Tasks**:
1. Wire `welcome.tsx` → Supabase signUp/signIn
2. Replace stub auth in `AuthScreen.tsx` with Supabase flows
3. Store session token in AsyncStorage (already in `lib/api.ts`)
4. Update `AuthGate` in `_layout.tsx` to check real auth state

### Phase 2: Core Data Flow (Priority: HIGH)

**Goal**: All screens fetch real data from backend

**Backend Tasks**:
1. Implement `pipelines.py` CRUD with Supabase queries
2. Implement `clips.py` with filtering by pipeline/status
3. Implement `sources.py` with video source tracking
4. Add pagination to list endpoints

**Frontend Tasks**:
1. Replace `seedPipelines` in store with API fetch
2. Wire `usePipelines()` hook to real API
3. Wire `useClips()` hook to real API
4. Add pull-to-refresh on all list screens
5. Implement infinite scroll for clip feeds

### Phase 3: Pipeline Management (Priority: HIGH)

**Goal**: Create and manage pipelines end-to-end

**Backend Tasks**:
1. Pipeline creation with validation
2. Pipeline status transitions (start/pause/errored)
3. Source ingestion triggers
4. Clip generation queue (Redis + background worker)

**Frontend Tasks**:
1. Wire `(app)/pipelines/new.tsx` to `POST /pipelines`
2. Wire pipeline detail screen to `GET /pipelines/:id`
3. Implement start/pause/delete with mutation hooks
4. Add source upload/connect flows

### Phase 4: Approval Flow (Priority: MEDIUM)

**Goal**: Real clip review and approval

**Backend Tasks**:
1. `GET /clips?status=ready_for_review` endpoint
2. `POST /clips/:id/approve` → update status, queue for posting
3. `POST /clips/:id/reject` → update status, log reason
4. `PATCH /clips/:id/schedule` → set post time

**Frontend Tasks**:
1. Replace `QUEUE` placeholder with API-fetched clips
2. Wire approve/reject buttons to mutations
3. Add swipe gesture handlers (reanimated)
4. Implement undo toast after reject

### Phase 5: Monetization (Priority: MEDIUM)

**Goal**: Stripe subscription + earnings tracking

**Backend Tasks**:
1. Stripe checkout session creation
2. Customer portal session creation
3. Webhook handling for subscription changes
4. Earnings calculation from analytics

**Frontend Tasks**:
1. Wire billing screen to Stripe checkout
2. Add "Manage in Stripe" portal link
3. Display real subscription tier from `/users/me/subscription`
4. Show earnings from `/earnings` endpoint

### Phase 6: Social Platform Integration (Priority: LOW)

**Goal**: OAuth connections + posting

**Backend Tasks**:
1. OAuth handlers for TikTok, Instagram, YouTube
2. Token refresh management
3. Post scheduling worker
4. Metrics aggregation

**Frontend Tasks**:
1. Wire social account connection to OAuth flows
2. Display connected accounts in profile
3. Platform picker during clip creation

---

## Immediate Next Steps

1. **Add Supabase Auth to backend** (2-3 hours)
   - Install `supabase-py` dependency
   - Add JWT validation to `get_current_user`
   - Create auth endpoints

2. **Wire frontend auth to Supabase** (2-3 hours)
   - Add `@supabase/supabase-js` to frontend
   - Create `lib/supabase.ts` client
   - Replace stub auth flows

3. **Implement pipeline backend** (3-4 hours)
   - Database queries for CRUD
   - Validation schemas
   - Status transitions

4. **Connect frontend pipelines to API** (2-3 hours)
   - Remove seed data
   - Wire `usePipelines()` to real hooks
   - Test create/update/delete

5. **Deploy updated backend** (30 min)
   - `fly deploy` with new code
   - Verify health check

---

## File Structure Changes Needed

```
frontend/
├── lib/
│   ├── supabase.ts          # NEW: Supabase client init
│   ├── auth.ts              # NEW: Auth helpers (signUp/signIn/signOut)
│   └── api.ts               # UPDATE: Add auth header from Supabase session
├── app/
│   ├── (auth)/
│   │   └── welcome.tsx      # UPDATE: Real auth flows
│   └── (app)/
│       └── index.tsx        # UPDATE: Fetch real clips
backend/
├── app/
│   ├── services/
│   │   └── auth.py          # UPDATE: Supabase JWT validation
│   └── api/
│       └── auth.py          # NEW: Registration/login endpoints
```

---

## Testing Strategy

| Stage | Method | Target |
|-------|--------|--------|
| API | Postman/cURL | All endpoints return correct shapes |
| Frontend | Expo Go (mobile) | Screens render with real data |
| Integration | End-to-end | Create pipeline → add source → generate clip → approve |
| Stripe | Test mode | Checkout flow + webhook + subscription update |

---

## Deployment Checklist

- [ ] Backend auth endpoints live
- [ ] Frontend auth wired
- [ ] Pipeline CRUD working
- [ ] Clip list populating
- [ ] Approval queue functional
- [ ] Stripe checkout tested
- [ ] Earnings dashboard showing data
- [ ] Social OAuth (Phase 2)

---

*Document generated: 2026-05-16*
*Backend: https://mvc-backend.fly.dev*
*Repo: https://github.com/BlissDirective/MostValuableClipper*
