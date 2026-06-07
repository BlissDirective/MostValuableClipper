-- Migration 007: variant_outcomes table (PIVOT Fix 3 — performance loop)
-- Records the REAL observed performance of variants the user actually shipped,
-- so swarm "best-pick" can rank by learned per-user signal instead of the
-- model's self-reported estimated_retention. This per-customer loop is the moat.
--
-- Populated when a user reports/links a posted clip and metrics flow back via
-- MetricsSyncService (see SwarmConfigService.record_variant_outcome).

CREATE TABLE IF NOT EXISTS variant_outcomes (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id     uuid        NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    pool_type   text        NOT NULL,
    persona     text        NOT NULL,        -- persona/strategy/recipe label
    platform    text,
    variant_id  text,
    clip_id     uuid        REFERENCES public.clips(id) ON DELETE SET NULL,
    retention   double precision NOT NULL CHECK (retention >= 0),
    created_at  timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT chk_outcome_pool_type CHECK (
        pool_type IN ('hook','remix','edit','thumbnail','music_match',
                      'segment_analyze','hooks_analysis','safety','ab_test')
    )
);

-- Primary lookup: ranking query filters by user + pool (+ platform).
CREATE INDEX IF NOT EXISTS idx_variant_outcomes_lookup
    ON variant_outcomes (user_id, pool_type, platform, persona);

CREATE INDEX IF NOT EXISTS idx_variant_outcomes_created
    ON variant_outcomes (user_id, created_at DESC);

ALTER TABLE variant_outcomes ENABLE ROW LEVEL SECURITY;

-- Owner-only access (writes happen via service role from the backend).
CREATE POLICY "Users read own variant outcomes" ON variant_outcomes
    FOR SELECT USING (auth.uid() = user_id);
