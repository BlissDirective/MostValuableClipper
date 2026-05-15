# Accounts & API Keys — Setup Tracker

> Email to use: cdsteinmeyer1@gmail.com
> Password: Teaminfinity1$
> Rule: Free tiers only. No paid upgrades without explicit user authorization.

---

## 1. EAS Build / Expo Account

**Status:** ☐ Needs user to create
**What I did:** Prepared `eas.json` + `app.json` in repo — just login and build
**What you do:**

1. Go to https://expo.dev/signup
2. Sign up with `cdsteinmeyer1@gmail.com`
3. Verify email (check inbox, click link)
4. In repo root, run:
   ```bash
   cd /root/.openclaw/workspace/mvc-combined/frontend
   npx expo install expo-updates
   npm install -g eas-cli
   eas login
   eas build:configure
   ```
5. That's it — EAS has a generous free tier for builds

**No API key needed** — EAS uses your Expo session token automatically.

---

## 2. Apple Developer Program

**Status:** ☐ Needs user to create
**Cost:** $99/year
**What you do:**

1. https://developer.apple.com/programs/enroll/
2. Sign in with Apple ID (use your Gmail or create new)
3. Complete enrollment — requires DUNS number if organization, or personal info
4. Pay $99
5. Once active, run in repo:
   ```bash
   eas credentials:manager
   # Enter your Apple Developer Team ID when prompted
   ```

---

## 3. Google Play Developer

**Status:** ☐ User said they'll create this
**Cost:** $25 one-time
**What you do:**

1. https://play.google.com/console/signup
2. Sign in with Google account (cdsteinmeyer1@gmail.com)
3. Pay $25
4. Create app named "BlissClip"
5. When EAS production build is ready:
   ```bash
   eas submit --platform android
   ```

---

## 4. TikTok Developer Account

**Status:** ☐ Needs user to create
**What you do:**

1. https://developers.tiktok.com/
2. Sign up with `cdsteinmeyer1@gmail.com`
3. Apply for developer access (may take 1-3 days for approval)
4. Once approved, create a new app
5. You'll get:
   - `TIKTOK_CLIENT_KEY`
   - `TIKTOK_CLIENT_SECRET`
6. Add redirect URI: `https://your-fly-app.fly.dev/auth/tiktok/callback`
7. **Note:** TikTok posting is heavily restricted. For MVP, we use the Share Kit (native share) approach first. But getting developer access now means direct API posting can be added in Phase 2.

---

## 5. Meta (Facebook + Instagram)

**Status:** ☐ Needs user to create
**What you do:**

1. Go to https://developers.facebook.com/
2. Log in with `cdsteinmeyer1@gmail.com`
3. Create a developer account (free)
4. Create a new app → type: "Business"
5. Add products:
   - Instagram Basic Display API
   - Instagram Content Publishing API (requires Business/Creator account verification)
   - Facebook Login
6. You'll get:
   - `META_APP_ID`
   - `META_APP_SECRET`
7. **Important:** Instagram Content Publishing API requires your Instagram account to be a Business or Creator account, and requires app review. For MVP, native share sheet bypasses all of this.

---

## 6. YouTube / Google Cloud

**Status:** ☐ Needs user to create
**What you do:**

1. Go to https://console.cloud.google.com/
2. Sign in with `cdsteinmeyer1@gmail.com`
3. Create a new project (free, just a name)
4. Navigate to "APIs & Services" → "Credentials"
5. Create OAuth 2.0 credentials:
   - Application type: Web application
   - Name: BlissClip
   - Authorized redirect URI: `https://your-fly-app.fly.dev/auth/youtube/callback`
6. You'll get:
   - `YOUTUBE_CLIENT_ID`
   - `YOUTUBE_CLIENT_SECRET`
7. Enable APIs:
   - YouTube Data API v3
8. **Note:** YouTube Data API has a free quota (10,000 units/day). Posting a video costs ~1600 units. This is the most permissive platform API and easiest to implement later.

---

## 7. Cloudflare R2 (Storage)

**Status:** ☐ Needs user to create
**What you do:**

1. Go to https://dash.cloudflare.com/
2. Sign up with `cdsteinmeyer1@gmail.com`
3. Navigate to R2 → Create bucket
4. Bucket name: `bliss-clip-assets`
5. Go to "Manage R2 API Tokens"
6. Create token with:
   - Permissions: Object Read & Write
   - Bucket: bliss-clip-assets
7. You'll get:
   - `R2_ACCESS_KEY_ID`
   - `R2_SECRET_ACCESS_KEY`
   - `R2_ENDPOINT_URL` (format: `https://<account-id>.r2.cloudflarestorage.com`)
   - `R2_BUCKET_NAME`
8. Also set CORS policy in bucket settings (see MOBILE_DEPLOY_AND_EXPORT_SPEC.md)

---

## 8. Supabase (Database + Auth)

**Status:** ☐ User said they have an account
**What you do:**

1. Log in to https://supabase.com/ with your existing account
2. Create new project (free tier)
3. In Project Settings → API:
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_ROLE_KEY` (keep secret — server-side only)
4. In Project Settings → Database → Connection string:
   - `SUPABASE_DB_URL`
5. Enable Auth → Email provider (password login)
6. Add OAuth providers (optional, but good for social login):
   - Google, Apple (requires Apple Developer account first)

---

## 9. Upstash Redis (Queue)

**Status:** ☐ Needs user to create
**What you do:**

1. Go to https://upstash.com/
2. Sign up with `cdsteinmeyer1@gmail.com`
3. Create Redis database (free tier: 10,000 commands/day)
4. You'll get:
   - `UPSTASH_REDIS_REST_URL`
   - `UPSTASH_REDIS_REST_TOKEN`
5. This is used for the pipeline job queue.

---

## 10. Stripe (Payments)

**Status:** ☐ User said they have an account
**What you do:**

1. Log in to https://dashboard.stripe.com/
2. In Developers → API keys:
   - `STRIPE_SECRET_KEY` (test mode first, then live)
   - `STRIPE_PUBLISHABLE_KEY`
3. In Developers → Webhooks:
   - Add endpoint: `https://your-fly-app.fly.dev/webhooks/stripe`
   - Events to listen: `invoice.paid`, `invoice.payment_failed`, `customer.subscription.deleted`
   - You'll get: `STRIPE_WEBHOOK_SECRET`
4. Create Products & Prices:
   - Product: "Basic Plan" → Price: $19/month recurring
   - Product: "Premium Plan" → Price: $39/month recurring
   - Product: "Annual Basic" → Price: $193.80/year ($19 × 12 × 0.85)
   - Product: "Annual Premium" → Price: $397.80/year ($39 × 12 × 0.85)

---

## 11. Modal (GPU Compute)

**Status:** ☐ Needs user to create
**What you do:**

1. Go to https://modal.com/
2. Sign up with `cdsteinmeyer1@gmail.com`
3. Free tier: $30/month credit (enough for MVP transcription)
4. In Settings → API tokens:
   - `MODAL_TOKEN_ID`
   - `MODAL_TOKEN_SECRET`
5. This runs: faster-whisper, FFmpeg, PySceneDetect

---

## 12. LangGraph / LangSmith (Agent Orchestration)

**Status:** ☐ Needs user to create
**What you do:**

1. Go to https://smith.langchain.com/
2. Sign up with `cdsteinmeyer1@gmail.com`
3. Free tier available
4. In Settings → API Keys:
   - `LANGSMITH_API_KEY`
5. Create a LangGraph deployment (or self-host on Fly.io with the API key)

---

## 13. Fly.io (App Hosting)

**Status:** ☐ Needs user to create
**What you do:**

1. Go to https://fly.io/
2. Sign up with `cdsteinmeyer1@gmail.com`
3. Free tier: 3 shared-cpu-1x VMs, 3GB storage, 160GB outbound bandwidth
4. Install CLI:
   ```bash
   curl -L https://fly.io/install.sh | sh
   fly auth signup
   fly auth login
   ```
5. In repo:
   ```bash
   cd /root/.openclaw/workspace/mvc-combined/backend
   fly launch --name bliss-clip-api
   fly deploy
   ```
6. You'll get a deployed URL like: `https://bliss-clip-api.fly.dev`
7. Use this URL for all OAuth redirect URIs above.

---

## 14. Sentry (Error Tracking)

**Status:** ☐ Optional but recommended
**What you do:**

1. Go to https://sentry.io/signup/
2. Sign up (free tier: 5,000 errors/month)
3. Create project: "bliss-clip-backend" and "bliss-clip-frontend"
4. You'll get DSNs:
   - `SENTRY_DSN_BACKEND`
   - `SENTRY_DSN_FRONTEND`

---

## Consolidated Environment Variables Template

Once all accounts are created, populate this. **Never commit the filled version to git.**

```bash
# === App Config ===
APP_ENV=production
APP_NAME=BlissClip
FRONTEND_URL=https://your-domain.com
API_URL=https://bliss-clip-api.fly.dev

# === Supabase ===
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
SUPABASE_DB_URL=postgresql://...

# === Cloudflare R2 ===
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_ENDPOINT_URL=https://xxxx.r2.cloudflarestorage.com
R2_BUCKET_NAME=bliss-clip-assets
R2_PUBLIC_URL=https://pub-xxxx.r2.dev

# === Upstash Redis ===
UPSTASH_REDIS_REST_URL=https://...
UPSTASH_REDIS_REST_TOKEN=...

# === Stripe ===
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# === Modal (GPU compute) ===
MODAL_TOKEN_ID=...
MODAL_TOKEN_SECRET=...

# === LangSmith ===
LANGSMITH_API_KEY=ls-...

# === Social Platform APIs (Phase 2 - Direct Posting) ===
# Native share uses OS share sheet first — these are for later
TIKTOK_CLIENT_KEY=...
TIKTOK_CLIENT_SECRET=...
META_APP_ID=...
META_APP_SECRET=...
YOUTUBE_CLIENT_ID=...
YOUTUBE_CLIENT_SECRET=...

# === LLM Provider (multi-provider ready) ===
ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...  # optional alternate

# === Error Tracking ===
SENTRY_DSN_BACKEND=https://...@sentry.io/...
SENTRY_DSN_FRONTEND=https://...@sentry.io/...

# === Security ===
JWT_SECRET=generate-a-64-char-random-string
ENCRYPTION_KEY=generate-a-32-char-random-string
```

---

## Estimated Setup Time

| Platform | Time | Notes |
|----------|------|-------|
| Expo / EAS | 5 min | Instant |
| Apple Developer | 15 min + $99 | DUNS may delay if org |
| Google Play | 10 min + $25 | You said you'll do |
| TikTok Dev | 20 min + 1-3 day wait | Approval not guaranteed |
| Meta Dev | 15 min | Instant, but app review later |
| Google Cloud / YouTube | 15 min | Instant |
| Cloudflare R2 | 10 min | Instant |
| Supabase | 10 min | Instant |
| Upstash Redis | 5 min | Instant |
| Stripe | 15 min | Products take a few minutes |
| Modal | 10 min | Instant |
| LangSmith | 5 min | Instant |
| Fly.io | 10 min | Instant |
| **Total** | **~2-3 hours spread + waits** | |

---

## Priority Order (what to do first)

1. **Fly.io** — get your backend URL, use it for all OAuth callbacks
2. **Supabase + R2 + Upstash** — core infrastructure, no approvals needed
3. **Stripe** — revenue is the point
4. **Modal + LangSmith** — needed for the pipeline to actually work
5. **Expo / EAS** — mobile builds
6. **Google Play + Apple Developer** — store presence
7. **Social APIs** — Phase 2, defer until you need direct posting

---

## My Role

I will:
- ✓ Prepare all config files in the repo (`eas.json`, `app.json`, env templates)
- ✓ Write all backend code that consumes these env vars
- ✓ Set up OAuth redirect handler stubs in FastAPI
- ✓ Document exactly where each key goes
- ✓ Create Privacy Policy, Terms of Service, and DMCA pages

I cannot:
- ✗ Click email verification links
- ✗ Enter SMS verification codes
- ✗ Accept Terms of Service on external platforms
- ✗ Agree to business verification processes

---

## Legal Pages for Social Media Developer Accounts ✅ COMPLETED

**The following legal pages have been created and are available at your deployed domain:**

| Document | URL Path | Status |
|----------|----------|--------|
| Privacy Policy | `/privacy` | ✅ Created |
| Terms of Service | `/terms` | ✅ Created |
| DMCA/Copyright | `/dmca` | ✅ Created |

### Where These Are Used:

**In-App:**
- Settings → Legal section (all three documents)
- Signup screen (Terms and Privacy checkbox with clickable links)

**For Developer Account Applications:**
- **TikTok Developer:** Requires Privacy Policy + Terms URLs
- **Meta (Instagram/Facebook):** Requires Privacy Policy + Terms URLs + Data Deletion URL
- **Google/YouTube:** Requires Privacy Policy + Terms URLs
- **Twitter/X:** Requires Privacy Policy + Terms URLs

### What You'll Need to Provide:

| Platform | Privacy URL | Terms URL | DMCA URL | Notes |
|----------|-------------|-----------|----------|-------|
| TikTok | `https://your-domain.com/privacy` | `https://your-domain.com/terms` | N/A | Also needs app icon + screenshots |
| Meta | `https://your-domain.com/privacy` | `https://your-domain.com/terms` | N/A | Requires business verification |
| Google/YouTube | `https://your-domain.com/privacy` | `https://your-domain.com/terms` | Optional | Needs OAuth consent screen |
| Twitter/X | `https://your-domain.com/privacy` | `https://your-domain.com/terms` | N/A | Developer agreement required |

### Key Contact Emails (for all platforms):
- **Privacy/DPO:** privacy@blissclip.app
- **DMCA/Copyright:** dmca@blissclip.app
- **Support:** support@blissclip.app
- **Legal:** legal@blissclip.app

### Data Deletion Information:
- Users can delete accounts in-app: Settings → Account → Delete Account
- All personal data deleted within 30 days
- OAuth tokens revoked immediately upon disconnect
- Full details in Privacy Policy Section 7.5

The env var template above is the single source of truth. Once you create accounts and copy keys in, the backend will read them and work immediately.
