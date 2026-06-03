# MVC High-Earner Spec — B2B Vertical Engine

> **Date:** 2026-06-02
> **Companion to:** `PIVOT_SPEC.md` (the *viable* path). This is the *high-earner* path. They diverge — read both, pick one, don't half-do both.
> **Thesis:** Stop being a clipper. Become a **compliant short-form content engine for a single regulated, high-budget B2B vertical.** Sell the *outcome a business already budgets for*, web-first, team seats, annual contracts. The agentic swarm becomes the production engine; the per-customer performance loop becomes the moat.

---

## 1. Pick ONE vertical (own its compliance + brand rules)

Generic clipping has no moat — TikTok does it free in-app. Defensibility comes from rules incumbents structurally won't touch.

| Vertical | Why it pays | The wedge (what OpusClip can't do) |
|----------|-------------|------------------------------------|
| **Financial advisors / wealth (primary rec)** | SEC/FINRA spend heavily on compliant marketing; can't legally use generic tools | Mandatory disclaimers, **FINRA 17a-4 archiving**, pre-approval workflow, prohibited-claims detection |
| Healthcare / med-device | HIPAA + FDA promo rules; large budgets | PHI scrubbing, claim-substantiation, MLR review trail |
| Law firms | Bar advertising rules per state | Jurisdiction-aware disclaimers, retention/archive |

**Recommendation: financial advisors first.** Clear regulator, deep budgets, acute pain, a compliance requirement that *is* the product. Repurpose the `safety` swarm into a **regulatory + brand-compliance reviewer** — that single capability justifies the whole price.

---

## 2. What the product becomes

**In:** the firm's *own* recorded content (webinars, Zoom/Riverside calls, earnings commentary).
**Out:** platform-ready short-form variants **that pass compliance**, with an auditable approval trail.
**Posting:** still human-in-the-loop / native upload — but now gated by a **compliance officer approval step**, which is a feature they pay for, not a limitation.

Core loop: upload → transcribe → segment → **swarm generates N distinct variants** → **compliance reviewer** (disclaimers present? prohibited claims? brand lockup?) → human approve → export + **immutable archive record**.

---

## 3. Architecture changes vs. current repo

**Keep & repurpose:**
- Swarm engine (`swarm_orchestrator`, `hook/remix/edit/segment/thumbnail/music` pools) — now a *variant production* engine.
- `safety` pool → **`compliance` pool**: rules engine + LLM check per vertical (disclaimers, restricted terms, claim substantiation). This is the new center of gravity.
- `MetricsSyncService` → feeds the per-customer performance loop (§4).
- Supabase RLS, Stripe — fine; move Stripe to **invoiced annual contracts**, not self-serve monthly.

**Build new:**
- **Web app (Next.js), team workspaces, roles** (creator / reviewer / admin). This replaces the 31-screen mobile app as the *product*.
- **Immutable archive** (WORM-style storage; R2 + write-once ledger row) for 17a-4-style retention + audit export.
- **Approval audit trail** (who generated, who reviewed, what changed, timestamps).
- **Brand kit** per workspace (logo lockups, mandated disclaimer text, banned phrases).

**Delete or freeze (over-engineering for users you don't have):**
- `post` pool / auto-posting, earnings autopilot, `fly.multi-region.toml`, autoscaler, batch service, genetic-evolution doc, 6-provider LLM router (keep 1 premium + 1 cheap), the consumer mobile app (demote to read-only "approve on the go" companion), free tier, autonomy levels, swipe-deck.
- **Rule:** re-add zero scaling infra until a paying customer's load forces it.

---

## 4. The moat: per-customer performance loop (build first, not last)

Everything else is rented (Whisper, ffmpeg, the LLM). The one uncopyable asset is *which variants performed for this firm*.
- Every generated variant carries a label; outcomes (views/retention/saves + compliance pass/fail) flow back via `MetricsSyncService` into `variant_outcomes(workspace_id, variant_id, persona, platform, metrics, approved_by)`.
- After ~90 days, suggestions are personalized per brand and demonstrably beat a cold tool → switching cost + a renewal story told in *their* numbers.
- Same data powers a quarterly **compliance + performance report** the firm can hand to their regulator and their CMO. That report is why they renew.

---

## 5. Pricing — invoiced, annual, seat + usage

Not self-serve SaaS. Land via design partners, expand by seats and source-volume.

| Plan | Annual (billed yearly) | Seats | Source-min/mo | Compliance reviews | Notes |
|------|------------------------|-------|---------------|--------------------|-------|
| **Practice** | $12k ($1k/mo) | 5 | 1,000 | included | single office |
| **Firm** | $36k ($3k/mo) | 20 | 4,000 | included + audit export | multi-advisor |
| **Enterprise** | $90k+ | 50+ | custom | + SSO, dedicated archive, BAA/compliance addendum | RIA networks / broker-dealers |

- **Anchor on cost avoided**, not clips produced: one FINRA marketing violation ≈ five-to-six figures in fines + remediation. $36k/yr is a rounding error against that.
- Overage on source-minutes only; variant generation is bundled (compliance is the value, not raw volume).
- Margin: vertical infra cost is the same ~$0.40–1.00/source-min stack — at $1–3k/mo per account, gross margin is 85%+.
- **Target shape:** ~150–250 firms at $12–90k = $3–10M ARR with a fraction of the support load and *renewal-based* retention, vs. 100k churny creators at $14.

---

## 6. Go-to-market (the hard part, not the code)

1. **3–5 design partners** (RIAs / mid-size advisory firms) on free pilots in exchange for case studies and rule-set co-design.
2. **Compliance officer is the buyer/champion**, not the marketer — sell "approval velocity + audit safety," demo the reviewer first.
3. Distribution via **wealth-tech ecosystems** (integrations/partners: Riverside, Zoom, broker-dealer marketing portals), and FINRA-compliance conferences — not TikTok creator channels.
4. Land on one office, expand across the firm's advisors (seat-based NRR).

---

## 7. Definition of done (high-earner MVP)

1. Web workspace: upload firm's own video → swarm generates 8 distinct variants → **compliance reviewer flags missing disclaimer / prohibited claim** → reviewer approves → export + **immutable archive + audit record**.
2. One vertical's rule pack (FINRA marketing) encoded and demonstrably catching violations.
3. Per-customer performance loop persisting `variant_outcomes` from day one.
4. One signed design partner using it on real content.
5. Mobile app demoted; auto-post / earnings autopilot / scale infra removed from surface.

---

## 8. Honest risk note

- **Slower, harder, less "fun"** than a creator app — sales cycles are months, you'll live in compliance docs, and the first 5 customers are won by founder hustle, not product.
- **Concentration risk:** few large accounts means each churn hurts — mitigated by archive lock-in + the performance loop.
- **Regulatory accuracy is existential:** a compliance tool that misses a real violation is worse than no tool. The reviewer must be conservative (flag-for-human, never auto-approve borderline) and the rule pack lawyer-reviewed.
- **But:** this is the only version of MVC with pricing power, durable retention, and a moat. The clipper isn't.
