-- Migration 004: Composite indexes and database integrity constraints
-- Fixes: M-04 (ON DELETE CASCADE), M-05 (composite indexes), M-06 (platform enum)
-- Apply with: supabase db push  OR  run directly in Supabase SQL editor

-- ─────────────────────────────────────────────────────────────────────────────
-- M-05: Composite indexes for common query patterns
-- ─────────────────────────────────────────────────────────────────────────────

-- clips: most frequent queries filter by user_id + status, order by created_at
CREATE INDEX IF NOT EXISTS idx_clips_user_status
    ON clips (user_id, status);

CREATE INDEX IF NOT EXISTS idx_clips_user_pipeline
    ON clips (user_id, pipeline_id);

CREATE INDEX IF NOT EXISTS idx_clips_user_created
    ON clips (user_id, created_at DESC);

-- sources: list by user
CREATE INDEX IF NOT EXISTS idx_sources_user
    ON sources (user_id);

CREATE INDEX IF NOT EXISTS idx_sources_user_created
    ON sources (user_id, created_at DESC);

-- analytics_events: aggregate queries group by user_id + event_type + timestamp
CREATE INDEX IF NOT EXISTS idx_analytics_user_type
    ON analytics_events (user_id, event_type);

CREATE INDEX IF NOT EXISTS idx_analytics_user_created
    ON analytics_events (user_id, created_at DESC);

-- social_accounts: list by user
CREATE INDEX IF NOT EXISTS idx_social_accounts_user
    ON social_accounts (user_id);

-- swarm_jobs: history queries filter by user_id, order by created_at
CREATE INDEX IF NOT EXISTS idx_swarm_jobs_user_created
    ON swarm_jobs (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_swarm_jobs_user_status
    ON swarm_jobs (user_id, status);

-- swarm_batch_jobs: same pattern
CREATE INDEX IF NOT EXISTS idx_swarm_batch_jobs_user_created
    ON swarm_batch_jobs (user_id, created_at DESC);

-- pipelines: owned by user
CREATE INDEX IF NOT EXISTS idx_pipelines_user
    ON pipelines (user_id);

-- earnings: aggregate by user + period
CREATE INDEX IF NOT EXISTS idx_earnings_user_period
    ON earnings (user_id, period_start DESC);

-- ─────────────────────────────────────────────────────────────────────────────
-- M-06: Platform enum constraint
-- Prevents arbitrary strings from being inserted into social_accounts.platform
-- ─────────────────────────────────────────────────────────────────────────────

DO $$
BEGIN
    -- Drop old constraint if it exists (idempotent)
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'chk_social_accounts_platform'
          AND table_name = 'social_accounts'
    ) THEN
        ALTER TABLE social_accounts DROP CONSTRAINT chk_social_accounts_platform;
    END IF;

    ALTER TABLE social_accounts
        ADD CONSTRAINT chk_social_accounts_platform
        CHECK (platform IN ('tiktok', 'instagram', 'youtube', 'twitter', 'facebook', 'linkedin'));
END $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- M-04: ON DELETE CASCADE consistency
-- Ensures child rows are removed when parent user is deleted.
-- We only alter FKs that currently lack CASCADE (check information_schema first).
-- ─────────────────────────────────────────────────────────────────────────────

-- clips → users
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.referential_constraints rc
        JOIN information_schema.key_column_usage kcu
            ON rc.constraint_name = kcu.constraint_name
        WHERE kcu.table_name = 'clips'
          AND kcu.column_name = 'user_id'
          AND rc.delete_rule != 'CASCADE'
    ) THEN
        ALTER TABLE clips DROP CONSTRAINT IF EXISTS clips_user_id_fkey;
        ALTER TABLE clips ADD CONSTRAINT clips_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
    END IF;
END $$;

-- sources → users
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.referential_constraints rc
        JOIN information_schema.key_column_usage kcu
            ON rc.constraint_name = kcu.constraint_name
        WHERE kcu.table_name = 'sources'
          AND kcu.column_name = 'user_id'
          AND rc.delete_rule != 'CASCADE'
    ) THEN
        ALTER TABLE sources DROP CONSTRAINT IF EXISTS sources_user_id_fkey;
        ALTER TABLE sources ADD CONSTRAINT sources_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
    END IF;
END $$;

-- social_accounts → users
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.referential_constraints rc
        JOIN information_schema.key_column_usage kcu
            ON rc.constraint_name = kcu.constraint_name
        WHERE kcu.table_name = 'social_accounts'
          AND kcu.column_name = 'user_id'
          AND rc.delete_rule != 'CASCADE'
    ) THEN
        ALTER TABLE social_accounts DROP CONSTRAINT IF EXISTS social_accounts_user_id_fkey;
        ALTER TABLE social_accounts ADD CONSTRAINT social_accounts_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
    END IF;
END $$;

-- pipelines → users
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.referential_constraints rc
        JOIN information_schema.key_column_usage kcu
            ON rc.constraint_name = kcu.constraint_name
        WHERE kcu.table_name = 'pipelines'
          AND kcu.column_name = 'user_id'
          AND rc.delete_rule != 'CASCADE'
    ) THEN
        ALTER TABLE pipelines DROP CONSTRAINT IF EXISTS pipelines_user_id_fkey;
        ALTER TABLE pipelines ADD CONSTRAINT pipelines_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
    END IF;
END $$;

-- analytics_events → users
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.referential_constraints rc
        JOIN information_schema.key_column_usage kcu
            ON rc.constraint_name = kcu.constraint_name
        WHERE kcu.table_name = 'analytics_events'
          AND kcu.column_name = 'user_id'
          AND rc.delete_rule != 'CASCADE'
    ) THEN
        ALTER TABLE analytics_events DROP CONSTRAINT IF EXISTS analytics_events_user_id_fkey;
        ALTER TABLE analytics_events ADD CONSTRAINT analytics_events_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
    END IF;
END $$;

-- swarm_configs → users
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.referential_constraints rc
        JOIN information_schema.key_column_usage kcu
            ON rc.constraint_name = kcu.constraint_name
        WHERE kcu.table_name = 'swarm_configs'
          AND kcu.column_name = 'user_id'
          AND rc.delete_rule != 'CASCADE'
    ) THEN
        ALTER TABLE swarm_configs DROP CONSTRAINT IF EXISTS swarm_configs_user_id_fkey;
        ALTER TABLE swarm_configs ADD CONSTRAINT swarm_configs_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
    END IF;
END $$;

-- swarm_jobs → users
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.referential_constraints rc
        JOIN information_schema.key_column_usage kcu
            ON rc.constraint_name = kcu.constraint_name
        WHERE kcu.table_name = 'swarm_jobs'
          AND kcu.column_name = 'user_id'
          AND rc.delete_rule != 'CASCADE'
    ) THEN
        ALTER TABLE swarm_jobs DROP CONSTRAINT IF EXISTS swarm_jobs_user_id_fkey;
        ALTER TABLE swarm_jobs ADD CONSTRAINT swarm_jobs_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
    END IF;
END $$;
