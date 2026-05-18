# Environment Variables

## Core Infrastructure
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

## Cloudflare R2 (Video Storage)
CLOUDFLARE_ACCOUNT_ID=your-account-id
CLOUDFLARE_R2_ACCESS_KEY_ID=your-access-key
CLOUDFLARE_R2_SECRET_ACCESS_KEY=your-secret-key
CLOUDFLARE_R2_BUCKET_NAME=mostvaluableclipper

## Redis (Upstash)
REDIS_URL=redis://your-upstash-url
REDIS_TOKEN=your-upstash-token

## Stripe (Payments)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID=price_...

## Social Media APIs (TBD — user creating accounts)
# TikTok API
TIKTOK_CLIENT_KEY=
TIKTOK_CLIENT_SECRET=
# Instagram/Facebook (Meta)
META_APP_ID=
META_APP_SECRET=
# YouTube
YOUTUBE_CLIENT_ID=
YOUTUBE_CLIENT_SECRET=

## Unified Social API (Evaluating Blotato vs Zernio)
BLOTATO_API_KEY=
ZERNIO_API_KEY=

## AI / LLM
# Anthropic Claude (Hook Generation + Creative AI)
# Get your key at: https://console.anthropic.com/
ANTHROPIC_API_KEY=sk-ant-api03-...

## Music Library
# TikTok Commercial Music (requires TikTok for Business account)
TIKTOK_MUSIC_TOKEN=

## Application
APP_SECRET_KEY=your-secret-key-here
FRONTEND_URL=https://your-app.fly.dev
API_BASE_URL=https://your-api.fly.dev

## Deployment
FLY_APP_NAME=mostvaluableclipper
FLY_REGION=lax
