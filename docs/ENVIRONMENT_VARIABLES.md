# Environment Variables

## Core Infrastructure
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

## Cloudflare R2 (Video Storage)
CLOUDFLARE_ACCOUNT_ID=2bb32a965806f844959920297e233167
CLOUDFLARE_R2_ACCESS_KEY_ID=2b259349da0083baaee5670ce98df86d
CLOUDFLARE_R2_SECRET_ACCESS_KEY=344994e22626d029b4207e2ccaf072002cdf3511d40eb6d768c47a4bde728a97
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
ANTHROPIC_API_KEY=your-anthropic-api-key-here

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
