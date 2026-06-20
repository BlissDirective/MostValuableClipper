# MVC Pivot Build Plan — "Variant Factory"

> **Thesis:** From *auto-source → auto-post → earnings autopilot* (non-viable: violates TikTok/IG/YouTube ToS, copyright, 2025–26 inauthentic-content crackdown) to a **human-in-the-loop variant factory**: the user's **own** long-form in → many **distinct** platform-ready clip variants out → **user picks and uploads natively**. No posting on the user's behalf. No third-party auto-sourcing.
>
> This doc is the **running, phase-by-phase build plan**. Status legend: ✅ done · 🔨 in progress · ⬜ not started.

---

## Build phases (status board)

| Phase | Scope | Status |
|-------|-------|--------|
| **Phase 0** | Legitimacy fixes on the `hook` pool (reference impl of Fixes 1–3) + cut auto-posting | ✅ done |
| **Phase 1** | Roll Fixes 1 & 2 to `remix` + `edit` pools; delete shadow `models.py` | ✅ done |
| **Phase 2 ← CURRENT** | **End-to-end pipeline (DoD #1):** upload own video → transcribe → segment → variants → **in-app video player** → export / native share | 🔨 in progress |
| **Phase 3** | Metered billing (Stripe usage on source-minutes + variant-gens, wired to real `cost_usd`) | ⬜ |
| **Phase 4** | Close the feedback loop: `MetricsSyncService` → `record_variant_outcome`; extend Fixes 1–3 to remaining pools (`thumbnail`, `music_match`, `segment_analyze`, `safety`) | ⬜ |

---

## Phase 0 — ✅ done (hook pool reference + cut)

- **Fix 1 (differentiation):** `ClaudeHookService.generate_hooks(system_override=)` now appends the persona directive to the base system prompt (platform rules + JSON contract preserved); `HookSwarmAgent` passes its persona through. 8 personas → 8 distinct calls.
- **Fix 2 (real cost):** `AgentResult.cost_usd` carries measured spend; `cost_cents` derived via `usd_to_cents()` (ceil, min 1). Hook-pool literals removed; `cost_usd` persisted on `SwarmAgentResult` and summed into `total_cost_usd`.
- **Fix 3 (performance loop / moat):** `variant_outcomes` table (migration `007`) + `SwarmConfigService.record_variant_outcome()` / `get_persona_performance()`; hook best-pick ranks by **real per-user retention** once ≥3 observations exist, else falls back to model estimate. Returns `ranked_by: history|estimate`.
- **Cut:** `execute_post_swarm` hard-guarded to disabled; `post` removed from default `enabled_pools` / allocation / behavior. Posting is user-initiated only.

## Phase 1 — ✅ done (remix + edit)

- **Remix Fix 1:** `RemixService.create_remix(strategy=)` re-weights segment scoring via `_STRATEGY_WEIGHTS` (per-strategy hook/salience/energy/face weights, each summing to 1.0) and steers hook voice via `_STRATEGY_DIRECTIVES`. Each remix agent now selects a distinct segment and writes in a distinct voice.
- **Remix Fix 2:** `create_remix` accumulates real LLM spend → returns `cost_usd`; `RemixSwarmAgent` reports measured `cost_cents`/`cost_usd`.
- **Remix Fix 3:** remix best-pick ranks by per-user `remix` strategy history when available.
- **Edit Fix 1:** recipes already differentiate via `_build_recipe_config` (verified: `fast_cuts` ≠ `zoom_pulse`).
- **Edit Fix 2:** local FFmpeg ⇒ no API spend ⇒ `cost_usd=0.0` (honest; compute-seconds metering deferred to a later phase, not a magic literal).
- **Cleanup:** deleted dead `backend/app/models.py` (was shadowed by the `app/models/` package and never loaded).
- **Verified:** `py_compile` all changed files; unit tests — strategy weights differ & sum to 1.0, directives reach `generate_hooks`, `usd_to_cents` wiring, edit recipe configs differ, full swarm module import.

---

## Phase 2 — 🔨 CURRENT: End-to-end pipeline (DoD #1)

**Goal:** one workflow that actually runs for a user's *own* uploaded video, with a watchable result. Today: no active video worker, no in-app player, and `yt-dlp`/transcription libs are missing from `requirements.txt`.

**Workstream checklist**
- ⬜ **Deps:** add `yt-dlp` (or direct-upload path that skips it) + a transcription lib (`faster-whisper` / `openai` transcribe) to `requirements.in`/`requirements.txt`; ensure `ffmpeg` present in the Docker image.
- ⬜ **Ingest:** user uploads their own long-form file (R2 presigned PUT) — no third-party URL sourcing in the default path.
- ⬜ **Worker:** a running consumer that processes a queued job: download/locate source → transcribe → `segment_analyze` → generate hook/remix variants → render → store. (Wire the existing Celery worker; today queued clips never process.)
- ⬜ **Player:** in-app video player on the clip/variant detail screen (replaces the static `Film` icon) so users can preview variants.
- ⬜ **Export / native share:** download + OS share sheet; **no auto-post**.
- ⬜ **Pipeline status:** surface job state (queued/processing/done/failed) end-to-end.

**Definition of done (Phase 2):** upload own long-form → transcribe → segment → **8 distinct hook+caption variants** → preview in an **actual video player** → export / native share, with measured `cost_usd` shown.

---

## Phase 3 — ⬜ Metered billing

Metered usage (priced on the scarce inputs: source-minutes + variant-gens), wired to the now-real `cost_usd`. See pricing sketch below. Replace flat self-serve tiers; no free tier beyond a trial.

---

## Reference — swarm pools: keep / cut / reframe

| Pool | Verdict | Why |
|------|---------|-----|
| `hook` | **KEEP** ✅ done | Parallel distinct hooks is the core variant value. |
| `remix` | **KEEP** ✅ done | Distinct segment/voice treatments of one clip. |
| `edit` | **KEEP** ✅ done | Recipe-driven cuts/transitions; genuine differentiation. |
| `thumbnail` | **KEEP** (Phase 4) | Cheap, high-perceived-value variant output. |
| `music_match` | **KEEP** (Phase 4) | Use **licensed/Commercial Music Library only**; never arbitrary tracks. |
| `segment_analyze` | **KEEP** (Phase 2 pipeline) | Picks the best moments from the user's own source. |
| `hooks_analysis` | **KEEP** | Feeds the feedback loop (Fix 3). |
| `safety` | **KEEP (downgrade scope)** | Brand/quality check on the user's own content, not a posting gate. |
| `ab_test` | **REFRAME** | Kill "A/B via auto-posting"; keep as offline variant scoring. |
| `post` | **CUT** ✅ done | Auto-posting is the banned behavior. Replaced with export + native upload. |

**Also cut:** earnings autopilot (`earnings_service` fabricated RPM math), multi-region posting infra (`fly.multi-region.toml`), genetic-evolution doc until the base swarm is real. **Input is the user's own/licensed content only.**

---

## Reference — the three legitimacy fixes (now implemented for hook/remix/edit)

**Fix 1 — Differentiation:** thread the persona/strategy/recipe through to the actual generation so N agents produce N genuinely different variants. *(hook: `system_override`; remix: `_STRATEGY_WEIGHTS` + `_STRATEGY_DIRECTIVES`; edit: `_build_recipe_config`.)*

**Fix 2 — Real cost metering:** `AgentResult.cost_usd` from the real LLM call; `cost_cents = usd_to_cents(cost_usd)`. No hardcoded literals. Persisted + summed to `total_cost_usd`.

**Fix 3 — Rank on real signal:** `variant_outcomes` per-user performance (migration 007) drives best-pick once ≥3 observations exist, else model estimate. This per-customer loop is the moat.

---

## Reference — metered pricing sketch (agency segment)

Price the scarce inputs (source-minutes + variant-gens), not seats. Target agencies/power podcasters, not $14 casual creators the native tools serve free.

| Plan | Price/mo | Source-minutes | Variant-gens | Overage | Seats |
|------|----------|----------------|--------------|---------|-------|
| **Studio** | $79 | 600 | 1,000 | $0.12/min, $0.05/variant | 3 |
| **Agency** | $249 | 2,500 | 5,000 | $0.10/min, $0.04/variant | 10 |
| **Scale** | $799 | 10,000 | 25,000 | $0.08/min, $0.03/variant | 30 + API |

- 1 variant-gen = 1 agent run; a swarm of 8 = 8 variant-gens, billed honestly via Fix 2.
- Set included quotas so blended gross margin ≥ 70% at p50 usage; overage protects the tail.
- Annual −20%. No free tier beyond a 50-min / 100-variant trial.
