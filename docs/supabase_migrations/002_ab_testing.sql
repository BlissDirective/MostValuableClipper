-- A/B Testing Schema Extension
-- Run this in your Supabase SQL Editor

-- A/B Tests table
CREATE TABLE IF NOT EXISTS ab_tests (
    test_id TEXT PRIMARY KEY,
    original_clip_id TEXT NOT NULL REFERENCES clips(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    pipeline_id TEXT REFERENCES pipelines(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    platform TEXT NOT NULL DEFAULT 'tiktok',
    confidence_level FLOAT NOT NULL DEFAULT 0.95,
    winner_variant_id TEXT,
    variants JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for fast user lookups
CREATE INDEX IF NOT EXISTS idx_ab_tests_user ON ab_tests(user_id);
CREATE INDEX IF NOT EXISTS idx_ab_tests_original_clip ON ab_tests(original_clip_id);
CREATE INDEX IF NOT EXISTS idx_ab_tests_status ON ab_tests(status);

-- Proven Hooks table (stores A/B test winners for future optimization)
CREATE TABLE IF NOT EXISTS proven_hooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    test_id TEXT NOT NULL REFERENCES ab_tests(test_id) ON DELETE CASCADE,
    clip_id TEXT NOT NULL REFERENCES clips(id) ON DELETE CASCADE,
    hook_archetype TEXT NOT NULL,
    hook_text TEXT NOT NULL,
    platform TEXT NOT NULL DEFAULT 'tiktok',
    views INTEGER NOT NULL DEFAULT 0,
    engagement_rate FLOAT NOT NULL DEFAULT 0,
    retention_3s FLOAT NOT NULL DEFAULT 0,
    retention_full FLOAT NOT NULL DEFAULT 0,
    composite_score FLOAT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_proven_hooks_user ON proven_hooks(user_id);
CREATE INDEX IF NOT EXISTS idx_proven_hooks_archetype ON proven_hooks(hook_archetype);

-- Clip Revisions table (audit trail for remix/edit history)
CREATE TABLE IF NOT EXISTS clip_revisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clip_id TEXT NOT NULL REFERENCES clips(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    revision_type TEXT NOT NULL, -- 'remix', 'edit', 'manual'
    previous_state JSONB NOT NULL DEFAULT '{}',
    new_state JSONB NOT NULL DEFAULT '{}',
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_clip_revisions_clip ON clip_revisions(clip_id);
CREATE INDEX IF NOT EXISTS idx_clip_revisions_user ON clip_revisions(user_id);

-- Update clips table to support remix lineage
-- (These use JSONB/metadata so no schema changes needed if using Supabase JSONB)
-- If using strict columns, run:
-- ALTER TABLE clips ADD COLUMN IF NOT EXISTS parent_clip_id TEXT;
-- ALTER TABLE clips ADD COLUMN IF NOT EXISTS remix_variant_id TEXT;
-- ALTER TABLE clips ADD COLUMN IF NOT EXISTS remix_metadata JSONB DEFAULT '{}';

-- Enable RLS
ALTER TABLE ab_tests ENABLE ROW LEVEL SECURITY;
ALTER TABLE proven_hooks ENABLE ROW LEVEL SECURITY;
ALTER TABLE clip_revisions ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view own A/B tests"
    ON ab_tests FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY "Users can insert own A/B tests"
    ON ab_tests FOR INSERT
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can update own A/B tests"
    ON ab_tests FOR UPDATE
    USING (user_id = auth.uid());

CREATE POLICY "Users can view own proven hooks"
    ON proven_hooks FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY "Users can view own clip revisions"
    ON clip_revisions FOR SELECT
    USING (user_id = auth.uid());

-- Function to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_ab_tests_updated_at
    BEFORE UPDATE ON ab_tests
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
