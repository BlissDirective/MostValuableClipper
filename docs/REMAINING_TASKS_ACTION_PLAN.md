# Remaining MVP Tasks — Research & Action Plan

## ✅ Completed: Autonomous Stubs (All Done)

All console.log stubs have been replaced with real functionality or proper MVP UX:

| Feature | Implementation |
|---------|---------------|
| **Change Password** | `PATCH /users/me` via Supabase `updateUser` API |
| **Export Data** | `GET /users/me/export` returns full user data JSON + frontend Alert summary |
| **Help & Legal** | `Linking.openURL` to backend `/help` and `/legal/privacy` routes |
| **Reset Learned Params** | `PATCH /users/me` with cleared preference fields |
| **Stub Cleanup** | All `console.log` stubs replaced with user-facing feedback or removed |

**Backend**: 70 tests pass (100%).  
**Frontend**: All screens now call real APIs or show "Coming soon" for post-MVP features.

---

## 🔜 Remaining Post-MVP Tasks

### 1. Social Media OAuth Integration

#### Best Practices (2026 Research)

**The Landscape**: Every major platform has tightened OAuth access significantly:

| Platform | Approval Time | Key Gotcha |
|----------|--------------|------------|
| **Instagram** | 1-4 weeks | Business/Creator accounts only. 25 posts/24hr cap. Must connect via Facebook Page. |
| **Facebook** | 1-4 weeks | Pages only (no personal profiles). Extensive App Review. |
| **TikTok** | 2-14 days | Unaudited mode = private posts only, ~5 users/24hr. Full audit required for public. |
| **YouTube** | Same-day quota | 10,000 quota units/day. Video upload = 1,600 units. Need Google Cloud project. |

**Key Architectural Decision**: Use **Unified Social API** (Blotato/Zernio) instead of native APIs.

**Why**: 
- Native API integration per platform = 2-4 weeks each = 3+ months total
- Each requires separate OAuth flows, token refresh logic, rate limit handling
- Unified APIs offer: one Bearer token, 15 platforms, normalized payloads, handled rate limits
- Cost: ~$50-200/month vs. engineering months
- Can migrate to native APIs later once revenue justifies the investment

**Recommended Approach**:
1. **Phase 1 (Immediate)**: Integrate Blotato or Zernio unified API
   - Single OAuth flow for users
   - One API key for us
   - Handles all token refresh, rate limits, retries
   - Flat monthly pricing, no per-call billing
   
2. **Phase 2 (Revenue > $5K/mo)**: Migrate to native APIs platform-by-platform
   - Start with YouTube (easiest quota increase)
   - Then Instagram (highest monetization for our use case)
   - Then TikTok (largest viral potential)
   - Keep unified API as fallback

**Backend Changes Needed**:
- Replace `POST /social/connect/{platform}` stub with unified API OAuth initiation
- Store unified API account tokens in `social_accounts` table
- Add `POST /social/post/{clip_id}` to publish clips via unified API
- Webhook handlers for post status updates

**Frontend Changes Needed**:
- Replace account toggle stub with real OAuth deep-link to unified API
- Add posting status indicators to clip cards
- Show "Connected via Blotato" instead of per-platform toggles

---

### 2. Edit / Remix Clip

#### Best Practices (2026 Research)

**The Pipeline Architecture** (based on production AI video pipelines):

```
Stage 1: AI Analysis (ResNet-50 + CLIP + Qwen2.5-VL)
  - Frame sampling every 2 seconds
  - Scene classification with quality rating 1-10
  - Speed assignment (1x-6x based on content density)
  
Stage 2: Clip Extraction (FFmpeg + NVENC H.265)
  - Speed-adjusted segments
  - Showcase highlight detection
  - Boring scene exclusion (silence + static frame detection)
  
Stage 3: Timeline Generation
  - Teaser + Intro + Main + Outro structure
  - Cross-dissolve transitions
  - Audio mix + watermark overlay
  
Stage 4: Output Rendering
  - H.265 4K @ 30 Mbps for main content
  - 9:16 vertical 1080x1920 for Reels/Shorts
```

**Key Tools**:
- **MoviePy 2.2.1**: Python-based video editing (trimming, concatenation, overlays, GIF export)
- **FFmpeg**: Low-level video processing (encoding, format conversion, stream manipulation)
- **OpenCV 4.8.1**: Real-time AI inference and computer vision
- **NVIDIA NVENC**: Hardware-accelerated encoding (10x faster than CPU)

**Recommended Approach for MVC**:

1. **Edit (Lightweight)**:
   - Trim start/end times (MoviePy `subclipped()`)
   - Adjust caption text (TextClip overlay)
   - Re-export to R2 (FFmpeg H.264 for compatibility)
   - Store as new clip revision in `clips` table

2. **Remix (AI-Powered)**:
   - Extract best 15-30 seconds using scene detection (OpenCV/CLIP)
   - Generate new caption via GPT-4o-mini (existing pipeline)
   - Add background music from royalty-free library (Freesound/YouTube Audio Library)
   - Export vertical 9:16 format for Reels/TikTok
   - Queue in Redis for async processing (similar to existing pipeline)

**Backend Changes Needed**:
- Add `POST /clips/{id}/edit` endpoint (trim + caption update)
- Add `POST /clips/{id}/remix` endpoint (AI scene detection + re-export)
- Integrate MoviePy + FFmpeg in Python backend
- Add `clip_revisions` table for version history
- Background job queue for heavy processing (existing Redis queue)

**Frontend Changes Needed**:
- Simple trim UI with start/end sliders (existing clip detail screen)
- Caption editor with real-time preview
- "Remix for Reels" button with style selection
- Processing status indicator (polling or WebSocket)

**MVP vs Post-MVP**:
- **MVP**: Basic trim + caption edit only (MoviePy, ~1 day implementation)
- **Post-MVP**: Full AI remix with scene detection and vertical export (~1 week)

---

### 3. Full Insights Analytics

#### Best Practices (2026 Research)

**Key Metrics to Track** (based on creator analytics research):

| Metric | Why It Matters | Benchmark |
|--------|---------------|-----------|
| **Completion Rate** | #1 algorithm signal | 65%+ excellent, 40-50% average |
| **Engagement Rate** | (Likes + Comments + Shares + Saves) / Views | 8-15% nano, 4-8% micro, 1-3% macro |
| **Watch Time** | Total minutes watched | 2x earnings vs. views-focused |
| **Shares/Views Ratio** | Content virality signal | 1% excellent, 0.2-0.5% typical |
| **Audience Retention** | Where viewers drop off | Identify weak moments |
| **Most Active Times** | Optimal posting window | Post when audience is online |
| **Traffic Sources** | FYP vs Following vs Search | Optimize distribution |
| **Follower Growth** | Momentum indicator | Track curve, not total count |

**Architecture**:
- Store raw analytics events in `analytics_events` table (existing)
- Aggregate via materialized views or scheduled jobs (Supabase pg_cron)
- Cache dashboard data in Redis (1-6 hour TTL based on metric type)
- Real-time metrics via WebSocket for live streams

**Backend Changes Needed**:
- Expand `POST /analytics/events` to accept platform-specific metrics (views, likes, shares, watch_time)
- Add `GET /analytics/dashboard` with aggregated metrics (7d, 30d, 90d windows)
- Add `GET /analytics/clips/{id}` for per-clip performance
- Scheduled aggregation job (daily at 3 AM) using pg_cron or Redis queue
- WebSocket endpoint for real-time metrics during live streams

**Frontend Changes Needed**:
- Replace static demo data in `insights.tsx` with real API calls
- Add time period selector (7d/30d/90d/all)
- Add per-clip analytics drill-down
- Add engagement rate charts (using victory-native or react-native-svg)
- Add "Best posting times" recommendation card

**Data Sources**:
- Internal: Clip views, approvals, earnings (already tracked)
- Platform APIs (Phase 2): YouTube Analytics, Instagram Insights, TikTok Analytics
- Unified API (Phase 1): Normalized metrics from all platforms

---

## 🗓️ Recommended Implementation Order

### Week 1: Social Media OAuth (Highest Impact)
1. Sign up for Blotato or Zernio (2 hours)
2. Implement unified OAuth flow in backend (4 hours)
3. Replace frontend account toggles with real OAuth deep-links (4 hours)
4. Test end-to-end with one platform (2 hours)

### Week 2: Edit Clip (Quick Win)
1. Install MoviePy + FFmpeg in backend Docker image (2 hours)
2. Implement `POST /clips/{id}/edit` (trim + caption) (4 hours)
3. Add simple trim UI to clip detail screen (4 hours)
4. Test and iterate (2 hours)

### Week 3: Full Insights
1. Expand analytics schema for platform metrics (4 hours)
2. Implement aggregation queries and caching (4 hours)
3. Replace static insights screen with real data (4 hours)
4. Add charts and visualizations (4 hours)

### Week 4: Remix Clip (If Time Permits)
1. Integrate scene detection AI model (4 hours)
2. Implement `POST /clips/{id}/remix` pipeline (8 hours)
3. Add "Remix for Reels" UI with style selection (4 hours)
4. Test with real clips (4 hours)

---

## 💡 Key Decisions

| Decision | Recommendation |
|----------|---------------|
| **OAuth Strategy** | Unified API (Blotato/Zernio) for immediate launch, native APIs at revenue milestone |
| **Video Editing** | MoviePy + FFmpeg for MVP, migrate to cloud GPU (RunPod/Lambda) for scale |
| **Analytics** | Internal metrics first, add platform APIs after OAuth integration |
| **Timeline** | 3 weeks to full functionality, 4th week for polish/remix |

---

## 🔗 Resources

- **Blotato API**: https://blotato.com (unified social posting)
- **Zernio API**: https://zernio.com (unified social + MCP server)
- **MoviePy**: https://zulko.github.io/moviepy/ (Python video editing)
- **FFmpeg**: https://ffmpeg.org (video processing)
- **YouTube Analytics API**: https://developers.google.com/youtube/analytics
- **Instagram Graph API**: https://developers.facebook.com/docs/instagram-api
- **TikTok Research API**: https://developers.tiktok.com/doc/research-api/get-started

---

*Document updated: 2026-05-17*  
*Next step: Await user decision on OAuth provider (Blotato vs Zernio vs native)*
