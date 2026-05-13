# MVP Build Spec

*Synthesis of all decisions from `brainstorming.md` walkthrough. This is the build plan.*

---

## 0. Locked decisions (the source of truth)

Every choice below is final unless this doc is explicitly revised.

### Product

| Decision | Locked to |
|---|---|
| Tiers in MVP | **Basic ($19/mo) + Premium ($39/mo)** |
| Studio tier | **"Request access," manually provisioned**, no UI build |
| Trial | **14 days, both tiers** |
| Annual discount | **15% off full year**, available at launch |
| Performance fee | **None in MVP** |
| Compute pass-through / BYOK | **Deferred to post-MVP** |

### Stack

| Layer | Choice |
|---|---|
| Mobile UI builder | **Rork** → eject to Expo / Claude Code when depth needed |
| Web companion | **Lovable, post-MVP** (not in MVP scope) |
| Pipeline service | **Python (FastAPI) + LangGraph**, hosted on Fly.io |
| Orchestration | **LangGraph for MVP**; Temporal as future migration if durability becomes a pain point |
| Product backend | **Supabase** (Postgres + Auth + Storage + pgvector) |
| GPU | **Modal** (locked in from Week 1; faster-whisper + FFmpeg containers) |
| Object storage | **Cloudflare R2** |
| Database | **Postgres (Supabase) + pgvector** |
| Queue | **Upstash Redis** (managed Redis Streams; serverless-friendly) |
| Payments | **Stripe** |
| Posting | **Aggregator (Postproxy / Upload-Post / Ayrshare) for MVP**, direct APIs post-PMF |
| Transcription | **faster-whisper on Modal** (cheap path); Deepgram if latency matters more |
| Auth | **Supabase Auth** (email + social OAuth; JWT verified server-side via JWKS) |
| LLM | **Provider-agnostic abstraction**; **Claude Sonnet 4.6** for Strategy/Critic/Safety reasoning, **Claude Haiku 4.5** for Captioner/lightweight calls |
| Design system | **Tokens-first** (`design-tokens.json` + `component-spec.md`); Lucide icons; Inter font |
| Cross-platform UI library | **No Tamagui** — separate implementations bound by tokens |
| Observability | **Sentry + Logfire** (or Datadog free tier) |

### UX

| Decision | Locked to |
|---|---|
| Mobile dashboard depth | **Full depth on mobile** from day one. Web mirrors later. |
| Critic Agent voice | **Neutral analyst** ("+124% retention" not "crushing it") |
| Approval mode UX | **TikTok-style swipe deck** — full screen, swipe right post / left reject / tap edit / long-press remix |

### Data

| Decision | Locked to |
|---|---|
| Source video retention | **User-configurable per pipeline; default Moderate (90 days source, transcripts/clips forever)** |
| Sub-1K-follower analytics | **Hybrid: API → manual entry → never scrape** |
| Cohort transfer learning | **Off by default, opt-in** |

### Wedge

| Decision | Locked to |
|---|---|
| MVP architecture | **Vertical-agnostic** |
| GTM positioning when wedge picked | **Clip moments and reactions, not raw broadcasts/proprietary footage** |
| Clipper-Friendly Source Resolver | **Default-on with visible toggle** |
| Wedge decision | **Deferred until post-MVP** |

### Safety / risk

| Decision | Locked to |
|---|---|
| Browser-automation posting | **Opt-in only, off by default, disabled in Studio tier** |
| DMCA / copyright | **Safe harbor + Chromaprint audio fingerprinting on user-supplied URLs** |
| Safety Classifier blocking | **Always runs all categories. Blocks only: Copyrighted-Material-Risk + Adult-NSFW. Others warn.** |
| Insurance | **General + cyber liability ($1-3M), Day 1** |

---

## 1. The MVP slice

What ships:

A vertical-agnostic mobile app where a user types a theme, the system resolves sources from a clipper-friendly priority chain, generates clips through a 9-agent pipeline (Strategy → Source → Ingest → Moment → Safety → Editor → Captioner → Distribution → Monitor → Critic), posts via an aggregator to TikTok + IG Reels + YouTube Shorts, monitors performance, and feeds a bandit-based learning loop that improves future clips.

Two paid tiers ($19 Basic, $39 Premium). 14-day trial. Studio tier manually provisioned. Safety classifier always running with two hard-block categories. DMCA + audio fingerprinting on user-supplied URLs.

What's deferred:
- Web companion (Lovable, post-MVP).
- Thumbnail Agent (frame-pick heuristic only).
- Campaign Agent (manual user submission to campaign networks).
- Cohort transfer learning (built but off by default; opt-in toggle live).
- Direct platform APIs (aggregator-only).
- Browser automation (code path exists, UI disabled).
- Studio multi-account workspace UI.
- Compute pass-through and BYOK.

---

## 2. Tier benefits matrix

| Capability | Basic ($19/mo) | Premium ($39/mo) |
|---|---|---|
| Active pipelines (themes) | 1 | 5 |
| Connected social accounts per platform | 1 | 3 |
| Clips generated per month | **50** | 300 |
| Source types | User upload + user-supplied URLs + creator-licensed sources | Same + creator-opt-in clip APIs + CC/archive search |
| Clipper-Friendly Source Resolver | On (default) | On (default) |
| Autonomy modes | Full Auto + Approve Each | Full Auto + Approve Each + Suggest Only + per-clip overrides |
| Posting platforms | TikTok + YouTube Shorts + IG Reels (via aggregator) | Same + Facebook Reels + scheduling control |
| Caption styles | Standard library (~10) | Full library + voice-matched generation from user's top performers |
| Thumbnail generation | Frame-pick heuristic | Frame-pick heuristic in MVP; AI-generated post-MVP |
| Learning loop | Bandit v1, weekly insight card | Bandit v1 + per-niche detail view, A/B testing toggle, hook-archetype dashboard |
| Cohort cold-start transfer | Available, opt-in | Available + cohort selection |
| Campaign network discovery | View only (no auto-submit in MVP) | View only (no auto-submit in MVP) |
| Analytics depth | Last 30 days summary | Unlimited history, per-clip drill-down |
| Source video retention | Default 90 days, configurable | Default 90 days, configurable |
| Support | Email, 48h | Email, 24h + priority |
| Compute caps | Hard cap at clip limit | Soft cap; overage available post-MVP |

**Studio (manual provisioning)**: priced on application. Multiple Premium-equivalent accounts under one Stripe invoice. Manually onboarded by founder.

---

## 3. The agent pipeline (MVP scope)

```
Strategy → Source → Ingest → Moment → Safety → Editor → Captioner → Distribution → Monitor → Critic
```

Per-agent MVP scope below. Each agent is a separate LangGraph node with its own retry policy and budget gate.

### 3.1 Strategy Agent
- **Input**: theme string, user's preferences, niche history (if any).
- **Output**: source plan (which source types + which specific URLs/handles), suggested cadence, suggested autonomy default.
- **Model**: Claude Sonnet 4.6 (or equivalent reasoner).
- **MVP behavior**: produces source plan + cadence; user reviews and confirms before pipeline activates.
- **Cost target**: <$0.10 per pipeline creation.

### 3.2 Source Agent
- **Input**: source plan from Strategy.
- **Output**: list of resolved video URLs/files ready for ingest.
- **Behavior**: walks the priority chain — uploads → creator-licensed → CC/archive → user-URLs. The Clipper-Friendly Source Resolver biases the chain toward creator-licensed sources for any theme that maps to high-risk verticals (sports, gaming, film/TV, music). Default-on, with a per-pipeline toggle to disable.
- **Per source type**:
  - **Uploads**: handled via R2 multipart upload from mobile.
  - **Creator-licensed**: integration with at least one opt-in creator clip platform at MVP launch (specific platform decided during Week 4 integration sprint based on partnership availability).
  - **CC/archive**: integration with archive.org and Creative Commons search.
  - **User-supplied URLs**: yt-dlp-equivalent for downloading; user attests rights before clip generation begins.
- **MVP cut**: skip "broader scraping by theme" entirely — UI doesn't offer it.

### 3.3 Ingest Agent
- **Input**: video URLs/files.
- **Output**: transcript, shot-detection metadata, basic scene tags, transcoded video stored in R2.
- **Pipeline**:
  - Download (if URL) → transcode to standardized H.264/AAC mp4 → faster-whisper transcription on Modal → PySceneDetect for shot boundaries → basic frame-level metadata (face presence, brightness, motion).
- **Cost target**: <$0.30 per source video at typical lengths (30-90 min).
- **Caching**: dedupe by content hash — same URL ingested twice doesn't re-transcribe.

### 3.4 Moment Agent
- **Input**: transcript + shot metadata + scene tags.
- **Output**: ranked list of candidate clip moments (start/end timestamps + score vector).
- **Base detectors** (always on): transcript salience, audio energy spikes, scene-change density, speaker change, face/object presence.
- **Sub-detectors** (loadable per vertical, MVP ships 2):
  - Streamer/podcast sub-detector (laughter, applause, exclamation patterns).
  - General-event sub-detector (audio-energy spikes, crowd reactions).
- Other sub-detectors (sports score-event, gaming kill-feed OCR, etc.) are **stubbed for post-MVP**.
- **Scoring**: weighted composite. Weights start at cohort defaults; updated per-user/niche by Critic over time.
- **Cost target**: <$0.05 per source video (small reasoning model, transcript-only input).

### 3.5 Safety Classifier Agent
- **Input**: candidate moments + context.
- **Output**: category tags per moment (multi-label).
- **Categories**: General, News-Political, Children's, Health, Finance, Adult-NSFW, Identifiable Private Individuals, Violent-Graphic, Copyrighted-Material-Risk.
- **MVP gate behavior**:
  - **Adult-NSFW**: hard block. Clip never reaches Distribution.
  - **Copyrighted-Material-Risk** (detected via Chromaprint audio fingerprint match against curated DB): hard block + user notification with explanation.
  - **All other categories**: warning surfaced to user. No block.
- **Implementation**: lightweight classifier (Claude Haiku 4.5 or equivalent) on transcript + visual frame samples. Chromaprint runs as a separate parallel check.
- **Cost target**: <$0.02 per clip.

### 3.6 Editor Agent
- **Input**: approved moments + clip parameters from learned user state.
- **Output**: rendered 9:16 mp4 clips, ready for captioning.
- **MVP behavior**:
  - Trim to chosen in/out points with optional padding.
  - Reframe 16:9 → 9:16 with auto-zoom on detected speaker (uses face-tracking model).
  - No B-roll insertion in MVP.
  - Frame-pick heuristic generates a thumbnail (highest-energy frame in middle third of clip).
- **Implementation**: FFmpeg in containers on Modal.
- **Cost target**: <$0.15 per clip.

### 3.7 Captioner Agent
- **Input**: clip + transcript + user voice profile (if any) + user tier.
- **Output**: 3 caption variants (hook + body + hashtags) per clip.
- **MVP behavior**:
  - Basic tier: generic caption library style (~10 archetypes).
  - Premium tier: voice-matched — few-shot prompts the model with user's top 5 performing clips' captions.
  - Category-specific disclosures auto-inserted when Safety Classifier flagged Health, Finance, or News-Political categories.
- **Cost target**: <$0.05 per clip.

### 3.8 Distribution Agent
- **Input**: clips + selected captions + thumbnails + user account credentials.
- **Output**: posted clips on TikTok + YouTube Shorts + IG Reels (via aggregator).
- **MVP posting flow**:
  - Aggregator integration (Postproxy / Upload-Post / Ayrshare — pick one in Week 3).
  - Per-platform format adjustments (caption length, hashtag formatting).
  - Posting times from user pipeline cadence; Critic Agent updates time recommendations over time.
- **Browser automation tier**: code path stubbed but UI disabled. Re-enabled in a future release with explicit risk disclosure.
- **Approval-mode behavior**: posts go to a review queue (the swipe deck) instead of live; post on right-swipe, drop on left-swipe.

### 3.9 Monitor Agent
- **Input**: posted clip records.
- **Output**: time-series metrics per clip per platform.
- **Polling schedule**:
  - +1h, +3h, +12h, +24h, +72h, +7d, +14d.
- **Source**: official platform analytics APIs via aggregator.
- **Sub-1K IG fallback**: when API returns "not eligible," prompt user to manually screenshot insights from IG app; OCR pulls numbers; stored in same metrics table flagged as "manual."

### 3.10 Critic Agent
- **Input**: post outcomes + clip features.
- **Output**: updated parameter weights per user × niche × platform.
- **MVP mechanism**: Thompson-sampling bandit over hook archetype, caption style, length bucket, post time, source channel.
- **Update cadence**: triggered on each metrics-snapshot ingestion at 24h and 72h marks.
- **Cohort transfer**: off by default per user choice. Toggle in onboarding.
- **Insight surfacing**: weekly card written by Critic, neutral-analyst voice, e.g., *"Hook archetype 'question-before-second-1' produced +124% 3-second retention vs. statement hooks. Weight increased."*

---

## 4. Source resolution priority chain (MVP)

```
1. User uploads (always available)
2. Creator-licensed sources (1 partner integration at launch)
3. Public domain / Creative Commons (archive.org, CC search)
4. User-supplied URLs (yt-dlp-equivalent + attestation)
5. Broader scraping (DISABLED in MVP UI)
```

The Clipper-Friendly Source Resolver (default-on) reorders the chain when the theme matches a "high-risk vertical" (sports, broadcast TV/film, music, mainstream gaming). For these themes, sources 4 and below are deprioritized; user is shown a banner: *"This theme typically involves copyrighted material. We've prioritized creator-licensed sources to reduce risk. Toggle off in pipeline settings if needed."*

### Rights-attestation flow
- For source type 4 (user-supplied URLs), the user must check an attestation box per pipeline before clips generate: *"I confirm I have the rights to use this content, or it qualifies as fair use, and I take responsibility for the clips produced from it."*
- Attestation timestamp + IP + user ID + URL stored in the compliance log.

---

## 5. Safety + DMCA infrastructure

### 5.1 Always-on Safety Classifier
- Runs after Moment Agent, before Editor.
- Multi-label classification across nine categories.
- Logs every decision (clip ID, categories, scores, action taken) to the compliance log.

### 5.2 Active blocking
- **Adult-NSFW**: detector trips → clip discarded, user notified.
- **Copyrighted-Material-Risk**: Chromaprint match against curated DB trips → clip held, user shown the match (artist/show/broadcast title), given option to manually override (Premium only) with attestation, or discard.

### 5.3 Curated audio fingerprint database
MVP database scope:
- Top 500 currently-charting music tracks (Spotify Top 500 daily refresh).
- Major sports broadcasters' commentator audio (manually curated samples — top 20 leagues' broadcast voices).
- Top 100 grossing films of last 5 years (theatrical audio samples where licensable).

This is intentionally narrow. It catches the most-likely-to-be-claimed material without trying to be Content ID.

### 5.4 DMCA pipeline
- Designated DMCA agent registered with the US Copyright Office (one of the Day 1 admin tasks).
- Public takedown notice intake form on website.
- Intake → automated email to filer + content takedown within 24h of valid notice.
- Counter-notice flow.
- Repeat-infringer policy (3 strikes → account terminated). Tracked per Stripe customer ID.

### 5.5 Other safety category warnings (not blocking)
Each non-blocking category triggers a UI warning at the user's review/approval stage (or a notification if Full Auto):
- *"This clip mentions financial investments. Disclosure recommended."*
- *"This clip contains an identifiable private individual. Verify you have consent or the use is newsworthy."*
- etc.

For Health / Finance / News-Political flags, the Captioner Agent auto-inserts a disclosure ("Not financial advice", "Educational only", source citation) into the caption.

---

## 6. UI/UX scope

### 6.1 Design tokens (Week 0 deliverable)
A `design-tokens.json` file with the following structure, used by both Rork prompts and Lovable prompts later:

```json
{
  "colors": { "primary": "...", "secondary": "...", "bg": "...", "surface": "...", "success": "...", "warning": "...", "danger": "...", "text-primary": "...", "text-secondary": "..." },
  "spacing": { "xs": 4, "sm": 8, "md": 16, "lg": 24, "xl": 32, "xxl": 48 },
  "type": { "display": 32, "h1": 24, "h2": 20, "body": 16, "caption": 12 },
  "radii": { "sm": 8, "md": 12, "lg": 16, "pill": 9999 },
  "fontFamily": "Inter",
  "iconLibrary": "lucide"
}
```

Specific values picked during Week 0 brand sprint.

### 6.2 Component spec (Week 0 deliverable)
Markdown describing every shared component. MVP set:
- ClipCard
- PipelineRow
- InsightTile
- AccountBadge
- SafetyFlag
- MetricChip
- ActionButton (primary, secondary, danger, ghost)
- SwipeDeckCard (for approval mode)

Each component documented with: purpose, anatomy, states (default/hover/loading/error), key props, behavior. Both Rork and (post-MVP) Lovable consume this spec.

### 6.3 Mobile screens (MVP)

**Auth & onboarding (5 screens)**
1. Welcome / sign up.
2. Theme input ("What do you want to clip?").
3. Connect social accounts (OAuth list).
4. Autonomy choice (Full Auto / Approve Each).
5. Cohort transfer opt-in (clear explanation, default off).

**Home / live feed (1 screen, deep)**
- Status strip (clips queued, posted today, week earnings).
- Vertical card feed of clips (newest first), each ClipCard showing thumbnail, source, posted-to badges, view counts, earnings, safety flag, quick actions.
- Pull-to-refresh.

**Pipelines (2 screens)**
- List view: all active pipelines with status.
- Detail view: source list, cadence, autonomy, performance summary, settings (including Clipper-Friendly Source Resolver toggle, retention period override, safety category disable for non-blocking categories).

**Insights (1 screen)**
- Weekly Critic card at top.
- Hook archetype rankings.
- Best post times per platform.
- Caption style rankings.
- Toggle: "Apply learnings to all pipelines."

**Earnings (1 screen)**
- Per-platform native CPM accrued.
- Per-campaign brand earnings (when Campaign Agent ships post-MVP).
- 7-day projection.
- Manual entry trigger for sub-1K IG accounts.

**Approval queue (1 screen)**
- TikTok-style swipe deck. Full-screen ClipCard. Caption preview below. Safety flag banner if any.
- Gestures: right swipe = post, left swipe = reject, tap = open editor, long-press = remix (with haptic confirmation overlay to prevent accidents).

**Profile / settings (3 screens)**
- Profile main.
- Subscription / billing.
- Settings (cohort transfer, retention defaults, support, account deletion).

**Per-clip detail (1 screen)**
- Full clip preview.
- All metrics (per platform, per snapshot interval).
- Edit / repost / kill actions.
- Safety classification details.
- Source attribution.

**Total: ~14 screens.** Tight but achievable with Rork + Claude Code for an 8-12 week MVP.

### 6.4 Critical interaction details
- **Long-press remix**: requires 500ms hold + haptic tick. A confirmation overlay appears showing "Remix this clip with new parameters?" with confirm/cancel. Prevents accidental remixes during normal swiping.
- **Approval swipe**: reject (left) is undoable for 5 seconds via toast.
- **Safety flag display**: every clip with any safety flag shows a small badge in the corner of the ClipCard. Tap reveals categories. Blocking flags (NSFW, Copyright) prevent posting; warning flags surface text disclosures.
- **Cohort transfer toggle**: shown during onboarding with a clear explanation: *"Some users let our system apply patterns learned from similar pipelines to give themselves a head start. No raw data is shared between users. Off by default."*

---

## 7. Data model

### 7.1 Tables (Postgres / Supabase)

```
users
  id (UUID, FK → auth.users.id), email, tier, subscription_status, trial_ends_at, created_at

connected_accounts
  id, user_id, platform, oauth_token (encrypted), oauth_refresh_token (encrypted),
  external_account_id, external_handle, follower_count, eligibility_flags, connected_at

pipelines
  id, user_id, theme, source_plan_json, cadence_json, autonomy_mode,
  clipper_friendly_resolver_enabled, retention_days, status, created_at, paused_at

source_assets
  id, pipeline_id, source_type, source_url, source_attestation_json,
  content_hash, transcript_url, shot_metadata_json, ingested_at, expires_at

moments
  id, source_asset_id, start_ts, end_ts, score_vector_json, sub_detector_hits_json

clips
  id, moment_id, output_url, thumbnail_url, voice_fingerprint_id,
  parameter_snapshot_json, status (rendered/blocked/etc.), created_at

safety_tags
  id, clip_id, category, score, action_taken (none/warn/block), classifier_version, created_at

caption_variants
  id, clip_id, hook, body, hashtags, style_archetype, selected_for_post

posts
  id, clip_id, platform, external_post_id, posted_at, scheduled_for, status

metrics_snapshots
  id, post_id, snapshot_at, views, likes, comments, shares, saves, watch_time_avg,
  follows_attributed, source (api/manual)

learned_parameters
  user_id, niche_id, platform, parameter_name, value_json, last_updated

cohort_priors
  niche_id, parameter_name, value_json, last_updated, sample_size

compliance_events
  id, user_id, event_type (attestation/dmca/safety_block/...), payload_json, created_at

dmca_notices
  id, target_post_id, claimant, payload, status, received_at, actioned_at

stripe_subscriptions
  id, user_id, stripe_customer_id, stripe_subscription_id, tier, status, current_period_end
```

### 7.2 Storage (Cloudflare R2)
- `/sources/{pipeline_id}/{content_hash}.mp4` — original video, retention per pipeline policy.
- `/transcripts/{content_hash}.json` — kept indefinitely.
- `/clips/{clip_id}.mp4` — kept indefinitely.
- `/thumbnails/{clip_id}.jpg` — kept indefinitely.

### 7.3 Vector store (pgvector)
- Caption embeddings (for voice-matching few-shot retrieval).
- Cohort embeddings (for cold-start prior retrieval, when opted in).

---

## 8. Build sequence (12-week solo plan)

This is the realistic critical path. Each week assumes ~40 productive hours.

### Week 0: Foundation (admin, design, scaffolding)
- LLC formation, EIN, business banking.
- Insurance: get quotes from Embroker, Vouch, Hiscox; bind general + cyber liability ($1-3M).
- DMCA agent registration with US Copyright Office.
- Domain, brand sprint, design tokens, component spec.
- Supabase project setup (Auth + Postgres + Storage), Stripe products created, R2 bucket.
- Modal account + LangGraph hello-world (Modal locked in from Week 1 — no benchmark gate).
- Upstash Redis instance provisioned.
- Repository scaffolding (mobile, pipeline service, infra).

### Week 1-2: Pipeline backbone
- LangGraph skeleton with all 10 agents stubbed.
- Strategy + Source agents to "happy path" with user-upload source type.
- Ingest agent: Modal-hosted faster-whisper, R2 read/write, PySceneDetect.
- Postgres schema + migrations.
- Job queue, retries, budget gates.

### Week 3: Aggregator integration
- Pick aggregator (Postproxy / Upload-Post / Ayrshare) based on Week 2 evaluation.
- TikTok + YT Shorts + IG Reels posting via aggregator.
- OAuth flows for connecting accounts.

### Week 4: Mobile UI shell (Rork sprint)
- Rork-generated UI for all 14 screens.
- Eject to Expo / Claude Code.
- Wire to pipeline service API.
- Auth flow via Supabase Auth.

### Week 5-6: Moment, Safety, Editor agents
- Moment Agent with base detectors + 2 sub-detectors.
- Safety Classifier with 9-category multi-label classifier.
- Chromaprint fingerprinting + curated database build (charting music + sports + film).
- Editor Agent: FFmpeg pipeline for trim + 9:16 reframe + auto-zoom + frame-pick thumbnail.

### Week 7: Captioner + Distribution flow end-to-end
- Captioner Agent (basic + voice-matched modes).
- Approval queue swipe deck on mobile.
- Full posting flow live: theme → posted clips on three platforms.

### Week 8: Monitor + Critic agents
- Polling schedules per platform.
- Manual-entry-with-OCR fallback for sub-1K IG.
- Bandit-based Critic agent.
- Insight card generation.

### Week 9: Source variety + Clipper-Friendly Resolver
- Creator-licensed source integration (1 partner).
- Public domain / CC integration.
- User-supplied URL flow with attestation.
- Clipper-Friendly Resolver logic + UI toggle.

### Week 10: Polish, metrics, billing
- All 14 screens dialed in.
- Tier gating (clip caps, pipeline caps, account caps enforced).
- Stripe subscription flows with 14-day trial + annual discount.
- Insights screen, earnings screen complete.
- Settings / profile / billing screens complete.

### Week 11: Hardening
- End-to-end automated tests for happy paths.
- Manual QA across all flows on iOS and Android.
- Sentry / Logfire instrumentation deeply applied.
- Security review (token storage, OAuth scopes, R2 access policies).
- Compliance review (DMCA flow tested, attestation flow tested, safety blocks verified).

### Week 12: Closed beta launch
- Recruit 30 beta users from your network and target communities.
- Free during beta.
- Daily check-ins on cohort metrics.
- Bug triage and rapid fixes.

### Validation gates before public launch
- ≥100 active users producing clips for 30+ days.
- ≥40% Day-30 retention.
- ≥1 user reporting first dollar of campaign or native CPM revenue attributable to the system.
- Average clip → post latency <15 minutes.
- Zero successful DMCA complaints unaddressed within 24h.

---

## 9. Cost ceiling (target operating economics per user)

Given $19 / $39 pricing, MVP must operate within these per-user-per-month costs:

| Component | Basic ($19) target | Premium ($39) target |
|---|---|---|
| Transcription (Whisper on Modal) | $0.50 | $3.00 |
| LLM inference (all agents) | $1.50 | $9.00 |
| Video processing (FFmpeg on Modal) | $1.00 | $6.00 |
| Storage (R2) | $0.50 | $2.00 |
| Aggregator posting | $1.50 | $9.00 |
| Database (Supabase) | $0.50 | $1.50 |
| Other (logs, transactional email, etc.) | $0.50 | $1.50 |
| **Total cost per user** | **$6.00** | **$32.00** |
| **Gross margin** | **~68%** | **~18%** |
| **Notes** | Healthy | **Tight** — Premium needs caching, model-tier optimization, or it's a loss leader |

Premium margin is the most concerning number in this whole plan. Three counter-mitigations:

1. **Aggressive caching**: same source video clipped twice doesn't re-transcribe / re-process. Cuts effective cost by ~20-30% for users who experiment.
2. **LLM tiering**: route to Haiku-class models for Captioner / lightweight tasks, Sonnet only for Strategy / Critic. Already in the design.
3. **Modal cold-start mitigation**: dedicated Modal containers for the most-called functions during peak hours. Reduces per-call cost by ~15%.
4. **If margins still don't work post-launch**: raise Premium to $49 or introduce per-clip overage. Don't sacrifice the loop quality.

---

## 10. Day-1 admin checklist

These are gating items before any user touches the system.

- [ ] LLC formed, EIN, bank account.
- [ ] Insurance: general liability + cyber liability bound ($1-3M).
- [ ] Terms of Service drafted (with attorney review of attestation language and Studio manual provisioning).
- [ ] Privacy Policy drafted (GDPR / CCPA compliant; cohort transfer disclosure).
- [ ] DMCA agent registered with US Copyright Office.
- [ ] Stripe account verified.
- [ ] Domain registered, basic landing page live.
- [ ] Support email + intake form live.
- [ ] Apple Developer + Google Play developer accounts.
- [ ] Aggregator account contracted (Postproxy / Upload-Post / Ayrshare).
- [ ] Modal + Supabase + R2 + Upstash Redis + Sentry production accounts provisioned.

---

## 11. Risks I'm tracking that aren't yet mitigated in this spec

1. **Aggregator dependency**: every posting goes through one third party. If they break or change terms, posting stops. Mitigation: architect Distribution Agent so aggregator is swappable. Not in MVP scope but constraint baked into the abstraction.
2. **Cold-start quality**: with cohort transfer off by default, new users have no learning loop signal for ~30-60 clips. Mitigation: invest extra in generic baseline parameters during Week 7-8. Strong defaults are the silent feature.
3. **Premium margin**: ~18% is tight. Watch closely in beta; raise price if needed.
4. **Apple App Store review**: an app that auto-posts to social media may trigger 4.2 / 5.0 reviews. Mitigation: ensure user explicitly authorizes each connected account; show clear review screen before posting in any auto mode. Build review-friendly framing of the product into App Store description.
5. **Content moderation surface**: even with two hard blocks, the system can produce clips that violate platform-specific policies (e.g., political content rules on TikTok). Mitigation: warning surface + the operator-level category disable. Watch beta for systematic patterns.
6. **DMCA volume**: hard to predict pre-launch. If it's high (>5/week), it'll consume founder time. Mitigation: automate intake → review → action with admin tooling from Day 1.

---

## 12. Wedge Pivot Playbook (for when the deferred wedge decision is made)

When you're ready to pick a launch wedge — World Cup, GTA 6, podcasts, anything else — execute this playbook:

1. **Score the wedge** against the five-axis framework in `brainstorming.md` §5.
2. **Enable the relevant Moment Agent sub-detector** if it isn't already shipping (sports score detection, gaming kill-feed OCR, etc.).
3. **Stand up creator-licensed source partnerships** for that vertical. The Source Agent already supports them; you're adding to the integrations list.
4. **Adjust marketing**: position as "clip the moments and reactions" — not raw broadcast/proprietary. Update homepage and onboarding.
5. **Update the Clipper-Friendly Source Resolver's high-risk-vertical list** if needed.
6. **Prepare DMCA / takedown process** for higher volume during the wedge.
7. **Recruit early users from communities** in that vertical.
8. **Don't change the architecture.** That's the point of vertical-agnostic design.

---

## 13. What this spec does not commit to

For clarity, things deliberately left out of MVP scope:
- Web companion (Lovable, post-MVP).
- Browser-automation posting (code stub only, UI disabled).
- Studio multi-account workspace UI (manual provisioning until 5+ paying agencies).
- Campaign Agent auto-submission (users manually submit to campaign networks).
- Thumbnail generation by image model (frame-pick heuristic only).
- Direct platform APIs (aggregator only).
- Performance fee billing.
- Compute pass-through / BYOK.
- All Moment Agent sub-detectors except 2.
- Cohort transfer learning (built but off by default).
- Multi-language captions (English only).
- Any feature not listed in §3-§7.

These are explicit deferrals, not oversights. Each can be picked up post-MVP based on validated demand.

---

## Next document

`mvp-build-spec.md` is the build plan. Once Week 0 admin items are underway and design tokens are locked, the next doc to produce is `system-architecture-detail.md` — the deeper engineering doc covering API contracts, agent state machines, retry policies, and infrastructure-as-code. Produced when implementation begins, not before.
