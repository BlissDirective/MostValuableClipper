# SETUP — Accounts & API Keys

Practical, step-by-step guide to the accounts and keys MVC needs. Ordered by what unblocks the **Phase 2 ingest pipeline** first (the thing that turns an uploaded video into clips), then everything else.

> **Canonical env var names live in code (`backend/app/core/config.py`).** Use the names in this doc. ⚠️ Note: `backend/.env.example` has some **stale** names (`R2_ACCESS_KEY_ID`); the code actually reads `CLOUDFLARE_R2_*`. The root `.env.example` is correct. When in doubt, match `config.py`.

**Setup flow:** copy `.env.example` → `.env` (root) and `backend/.env.example` → `backend/.env`, fill values below, never commit `.env`.

---

## Tier 1 — Required to run the ingest pipeline

These four make `upload → transcribe → segment → render → clips` work end to end.

### 1. OpenAI (Whisper transcription) — `OPENAI_API_KEY`
Used by `TranscriptionService` (Whisper `whisper-1`). Without it, transcription returns empty and ingest produces no segment clips.
1. Go to **https://platform.openai.com/signup** and sign in.
2. **Settings → Billing → Add payment method** and add a small credit balance (Whisper is ~**$0.006/min** of audio; pay-as-you-go).
3. **API keys → Create new secret key** (name it `mvc-backend`). Copy it once — you can't view it again.
4. Set `OPENAI_API_KEY=sk-...` in `backend/.env`.
- Cost check: a 60-min podcast ≈ **$0.36** to transcribe.

### 2. Cloudflare R2 (video storage) — `CLOUDFLARE_*`
Stores source uploads + rendered clips. R2 is chosen because **egress is free** (the thing that kills S3-based video apps).
1. Create/sign in at **https://dash.cloudflare.com**. Add a payment method (R2 has a free tier: 10 GB storage, then **$0.015/GB-mo**, **$0 egress**).
2. Left sidebar → **R2** → **Create bucket** → name it `mvc-clips` (matches `CLOUDFLARE_R2_BUCKET` default).
3. **Account ID:** shown on the R2 overview page (right side) → `CLOUDFLARE_ACCOUNT_ID`.
4. **R2 → Manage R2 API Tokens → Create API Token:**
   - Permissions: **Object Read & Write**, scoped to the `mvc-clips` bucket.
   - On creation it shows **Access Key ID**, **Secret Access Key**, and an **S3 endpoint** like `https://<accountid>.r2.cloudflarestorage.com`. Copy all three now.
5. Set:
   - `CLOUDFLARE_R2_ACCESS_KEY_ID=...`
   - `CLOUDFLARE_R2_SECRET_ACCESS_KEY=...`
   - `CLOUDFLARE_R2_ENDPOINT=https://<accountid>.r2.cloudflarestorage.com`
   - `CLOUDFLARE_ACCOUNT_ID=<accountid>`
   - `CLOUDFLARE_R2_BUCKET=mvc-clips`
6. **(Recommended) Public access for playback:** R2 bucket → **Settings → Public access → enable r2.dev subdomain** (or attach a custom domain). Put that base URL in `CLOUDFLARE_R2_PUBLIC_URL=https://pub-xxxx.r2.dev`. The app falls back to presigned URLs if unset, but a public/CDN URL is better for the in-app video player.

### 3. Supabase (database + auth) — `SUPABASE_*`
1. Sign in at **https://supabase.com/dashboard** → **New project** (free tier is fine to start). Choose a region near your users; set a strong DB password.
2. **Project Settings → API:**
   - **Project URL** → `SUPABASE_URL`
   - **`anon` public key** → `SUPABASE_ANON_KEY` (and `EXPO_PUBLIC_SUPABASE_ANON_KEY`)
   - **`service_role` key** → `SUPABASE_SERVICE_ROLE_KEY` ⚠️ **backend only — never ship to the app/frontend.**
3. **Project Settings → Database → Connection string (URI)** → `SUPABASE_DIRECT_URL` (used for migrations).
4. **Run the schema + migrations** (SQL Editor, in order): `backend/supabase_schema.sql`, then everything in `docs/supabase_migrations/` (`002`→`007`). Migration `007_variant_outcomes.sql` is required for the swarm performance loop.

### 4. Upstash Redis (job queue) — `UPSTASH_REDIS_*`
The worker consumes jobs from here; without it, uploads never get processed.
1. Sign in at **https://console.upstash.com** → **Create Database** (Redis) → pick a region matching Supabase. Free tier is fine.
2. On the database page, **REST API** section:
   - **UPSTASH_REDIS_REST_URL** → `UPSTASH_REDIS_REST_URL`
   - **UPSTASH_REDIS_REST_TOKEN** → `UPSTASH_REDIS_REST_TOKEN`

### Local prerequisite — FFmpeg
The pipeline shells out to `ffmpeg`/`ffprobe` (already installed in the Docker images). For local dev: macOS `brew install ffmpeg`, Debian/Ubuntu `apt-get install -y ffmpeg`. `yt-dlp` is only needed for the optional URL-ingest path (`pip install -r backend/requirements.txt` includes it).

**After Tier 1:** you can upload a video and get reviewable clips back. The minimum `backend/.env` to run ingest: `OPENAI_API_KEY`, the 5 `CLOUDFLARE_*` R2 vars, the 3 `SUPABASE_*` vars, and the 2 `UPSTASH_*` vars.

---

## Tier 2 — Needed for AI hooks/captions & payments

### 5. Anthropic (hook/caption/remix LLM) — `ANTHROPIC_API_KEY`
The swarm's hook/remix generation routes through the LLM router (Anthropic primary).
1. **https://console.anthropic.com** → sign in → **Billing** → add credit.
2. **API Keys → Create Key** → `ANTHROPIC_API_KEY=sk-ant-...`.
- (Optional) The router can also use `OPENAI_API_KEY` as a fallback tier — already set in Tier 1.

### 6. Stripe (metered billing — Phase 3) — `STRIPE_*`
Not required to run ingest; needed before charging.
1. **https://dashboard.stripe.com** → start in **Test mode**.
2. **Developers → API keys:** Publishable → `STRIPE_PUBLISHABLE_KEY` (`pk_test_...`); Secret → `STRIPE_SECRET_KEY` (`sk_test_...`).
3. **Developers → Webhooks → Add endpoint:** URL `https://<your-api>/api/v1/webhooks/stripe`, then copy the **Signing secret** → `STRIPE_WEBHOOK_SECRET` (`whsec_...`). For local testing use the Stripe CLI (`stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe`).
4. Create Products/Prices for the plans (see `PIVOT_SPEC.md` pricing) and set the `STRIPE_PRICE_*` IDs.

---

## Tier 3 — Security & deployment

### 7. App secrets (generate yourself)
Generate three random values: `openssl rand -hex 32` for each.
- `APP_SECRET`, `JWT_SECRET`, `ENCRYPTION_KEY` (the last encrypts stored tokens — keep it stable or you can't decrypt existing rows).

### 8. Fly.io (backend + worker hosting) — `FLY_*`
1. Install flyctl (`curl -L https://fly.io/install.sh | sh`), `fly auth signup`.
2. `fly tokens create deploy` → `FLY_ORG_TOKEN` (used by CI/CD). Apps: API (`fly.toml`) + worker (`fly.worker.toml`).
3. Set secrets on Fly with `fly secrets set KEY=value` (don't bake them into images).

### 9. Sentry (error tracking, optional) — `SENTRY_DSN_*`
**https://sentry.io** → create two projects (Python backend, React Native) → copy each **DSN** → `SENTRY_DSN_BACKEND`, `SENTRY_DSN_FRONTEND`.

---

## Tier 4 — Deliberately NOT needed (pivot)

Per `PIVOT_SPEC.md`, MVC no longer auto-posts. You can **skip** these unless you re-introduce posting:
- `TIKTOK_CLIENT_KEY` / `TIKTOK_CLIENT_SECRET`, `META_APP_ID` / `META_APP_SECRET`, `YOUTUBE_CLIENT_ID` / `YOUTUBE_CLIENT_SECRET`
- `ZERNIO_API_KEY` (third-party posting aggregator)
- Instagram/TikTok webhook secrets

Posting is user-initiated (export + native upload), so no platform developer apps, audits, or OAuth review are required.

---

## Quick checklist

| Key | Provider | Tier | Needed for |
|-----|----------|------|-----------|
| `OPENAI_API_KEY` | OpenAI | 1 | transcription (Whisper) |
| `CLOUDFLARE_R2_ACCESS_KEY_ID` / `_SECRET_ACCESS_KEY` / `_ENDPOINT` / `CLOUDFLARE_ACCOUNT_ID` / `CLOUDFLARE_R2_BUCKET` | Cloudflare R2 | 1 | video storage |
| `CLOUDFLARE_R2_PUBLIC_URL` | Cloudflare R2 | 1 (rec.) | in-app playback |
| `SUPABASE_URL` / `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_ROLE_KEY` | Supabase | 1 | DB + auth |
| `UPSTASH_REDIS_REST_URL` / `_TOKEN` | Upstash | 1 | job queue |
| `ANTHROPIC_API_KEY` | Anthropic | 2 | hooks/captions/remix |
| `STRIPE_SECRET_KEY` / `_PUBLISHABLE_KEY` / `_WEBHOOK_SECRET` | Stripe | 2 | billing (Phase 3) |
| `APP_SECRET` / `JWT_SECRET` / `ENCRYPTION_KEY` | self-generated | 3 | security |
| `FLY_ORG_TOKEN` | Fly.io | 3 | deploy |
| `SENTRY_DSN_*` | Sentry | 3 | error tracking |
| TikTok/Meta/YouTube/Zernio | — | 4 | **skip** (no auto-posting) |
