# MVC Pivot Spec — "Variant Factory" (one page)

> **Date:** 2026-06-02
> **Thesis change:** From *auto-source → auto-post → earnings autopilot* (non-viable: violates TikTok/IG/YouTube ToS, copyright, 2025–26 inauthentic-content crackdown) to a **human-in-the-loop variant factory**: the user's **own** long-form in → many **distinct** platform-ready clip variants out → **user picks and uploads natively**. No posting on the user's behalf. No third-party content auto-sourcing.

---

## 1. Swarm pools — keep / cut / reframe

| Pool | Verdict | Why |
|------|---------|-----|
| `hook` | **KEEP (make real)** | Parallel distinct hooks is the core variant value. |
| `remix` | **KEEP (make real)** | Distinct edit/segment treatments of one clip. |
| `edit` | **KEEP (make real)** | Recipe-driven cuts/transitions; genuine differentiation. |
| `thumbnail` | **KEEP** | Cheap, high-perceived-value variant output. |
| `music_match` | **KEEP** | Use **licensed/Commercial Music Library only**; never arbitrary tracks. |
| `segment_analyze` | **KEEP** | Picks the best moments from the user's own source. |
| `hooks_analysis` | **KEEP** | Becomes the **feedback loop** (see Fix 3). |
| `safety` | **KEEP (downgrade scope)** | Brand-safety/quality check on the user's own content, not a posting gate. |
| `ab_test` | **REFRAME** | Kill "A/B via auto-posting." Keep as **offline variant scoring** to rank options before the human picks. |
| `post` | **CUT** | Auto-posting on the user's behalf is the banned behavior. Replace with **export + one-tap native share / manual upload**. |

**Also cut from the roadmap:** earnings autopilot (`earnings_service` fabricated RPM math), multi-region posting infra (`fly.multi-region.toml`), genetic-evolution doc until the base swarm is real. **Input is the user's own/licensed content only** — remove "auto-discover third-party creators to clip."

---

## 2. The three code fixes that make the swarm legitimate

Today the swarm is *parallel duplicate calls, billed at made-up prices, ranked by a fabricated score.* Three fixes turn it into a real product.

**Fix 1 — Make personas actually differentiate (currently a no-op).**
`swarm_agents.py:85` computes `system_override = self._persona_system_prompt(...)` then **never passes it** to `generate_hooks()`. Thread it through; do the same for `RemixSwarmAgent.strategy` and `EditSwarmAgent.recipe`.
- `claude_hook_service.generate_hooks(..., system_override: str | None = None)` → use it in place of the default system prompt.
- Result: N agents produce N genuinely different variants instead of N near-identical ones.

**Fix 2 — Meter real cost, not constants.**
Remove the 42 hardcoded `cost_cents=10/20` literals in `swarm_agents.py`. Return token usage from the LLM call and price it with the existing `llm_router.estimate_cost_usd(input_tokens, output_tokens)`. Wire `check_budget()` / `audit_budget_post_execution()` to **measured** spend. Without this, a variant factory (N× calls/clip) silently runs flat tiers into the red.

**Fix 3 — Rank on a real signal, not LLM self-score.**
"Best-pick" uses `estimated_retention` (the model's guess about itself — `swarm_orchestrator.py:125`). Replace with a learned signal from the user's **own** posted-clip performance:
- New table `variant_outcomes(user_id, variant_id, persona, platform, posted_at, views, retention, saved_bool)`; the user reports/links which variant they shipped and metrics flow back via the already-built `MetricsSyncService`.
- Rank future variants per-user by historical persona/recipe performance. **This per-user feedback loop is the only thing here a competitor can't trivially copy** — it is the moat.

---

## 3. Metered pricing sketch — agency segment

Flat per-seat dies on heavy users (every incumbent moved to metering). Price the **scarce inputs** (source minutes + variant generations), not seats. Target agencies/power podcasters, not $14 casual creators the native tools already serve free.

| Plan | Price/mo | Included source-minutes | Included variant-gens | Overage | Seats |
|------|----------|------------------------|----------------------|---------|-------|
| **Studio** | $79 | 600 min | 1,000 | $0.12/min, $0.05/variant | 3 |
| **Agency** | $249 | 2,500 min | 5,000 | $0.10/min, $0.04/variant | 10 |
| **Scale** | $799 | 10,000 min | 25,000 | $0.08/min, $0.03/variant | 30 + API |

- **Unit cost to cover** (per the research): ~$0.40–1.00 per 60-min source (transcribe + transcode + LLM) **plus** ~real per-variant LLM cost from Fix 2. Set included quotas so blended gross margin ≥ 70% at p50 usage; overage protects the tail.
- **1 variant-gen = 1 agent run** (one hook/edit/thumbnail option). A swarm of 8 = 8 variant-gens — billed honestly because of Fix 2.
- **Annual −20%.** No free tier beyond a 50-minute / 100-variant trial (the worst-retaining "AI tourist" band is the casual free user — don't subsidize them).
- **Why this segment:** $50–249/mo AI tools retain ~45% of revenue over 12mo vs ~23% in the $12–30 band; agencies have recurring long-form (weekly podcasts/webinars) → durable, non-bursty usage.

---

## 4. Definition of done (pivot MVP)

1. One pipeline runs end-to-end: user uploads own long-form → transcribe → segment → **8 distinct hook+caption variants** → preview in an **actual video player** → export / native share. (Today: no worker, no player, `yt-dlp`/transcription missing from `requirements.txt`.)
2. Fixes 1–3 shipped; swarm cost shown to the user is **measured**.
3. Metered billing live; `post` pool and earnings autopilot removed from the app surface.
