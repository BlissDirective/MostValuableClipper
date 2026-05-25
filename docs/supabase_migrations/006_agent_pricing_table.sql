-- Migration 006: Agent pricing table (L-07)
-- Replaces hardcoded DEFAULT_COSTS dict in SwarmConfigService.
-- Applied to Supabase via MCP; stored here for version-control history.
--
-- To update prices: INSERT a new row with effective_from = now() and
-- UPDATE the old row to set effective_until = now(). The in-process
-- cache (TTL 5 min) picks up changes within one cache cycle.

CREATE TABLE IF NOT EXISTS agent_pricing (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pool_type       text        NOT NULL,
    cost_cents      integer     NOT NULL CHECK (cost_cents >= 0),
    effective_from  timestamptz NOT NULL DEFAULT now(),
    effective_until timestamptz,          -- NULL = currently active
    note            text,
    created_at      timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT chk_pricing_pool_type CHECK (
        pool_type IN ('hook','remix','post','ab_test','music_match','batch',
                      'content_discovery','edit','thumbnail','safety',
                      'hooks_analysis','segment_analyze')
    ),
    CONSTRAINT chk_pricing_dates CHECK (
        effective_until IS NULL OR effective_until > effective_from
    )
);

-- Enforces one active row per pool_type
CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_pricing_active
    ON agent_pricing (pool_type)
    WHERE effective_until IS NULL;

-- Seed initial prices
INSERT INTO agent_pricing (pool_type, cost_cents, note)
VALUES
    ('hook',              5,  'Initial baseline — verify against Anthropic usage dashboard'),
    ('remix',             20, 'Initial baseline'),
    ('post',              1,  'Initial baseline'),
    ('ab_test',           3,  'Initial baseline'),
    ('music_match',       2,  'Initial baseline'),
    ('batch',             3,  'Initial baseline — batch discount applied'),
    ('content_discovery', 5,  'Initial baseline'),
    ('edit',              15, 'Initial baseline'),
    ('thumbnail',         1,  'Initial baseline'),
    ('safety',            1,  'Initial baseline'),
    ('hooks_analysis',    8,  'Initial baseline'),
    ('segment_analyze',   5,  'Initial baseline')
ON CONFLICT DO NOTHING;

ALTER TABLE agent_pricing ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read pricing" ON agent_pricing
    FOR SELECT USING (true);
