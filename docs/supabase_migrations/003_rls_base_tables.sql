-- ============================================
-- Migration 003: Row Level Security on Base Tables
-- Audit reference: C-09 (missing DELETE policies on 002 tables)
-- ============================================
-- Idempotent: safe to re-run. Policies use DO $$ blocks to guard
-- against duplicate-name errors when a policy already exists.
-- ============================================

-- ============================================
-- SECTION 1: Enable RLS on all base tables
-- ============================================

ALTER TABLE profiles           ENABLE ROW LEVEL SECURITY;
ALTER TABLE clips              ENABLE ROW LEVEL SECURITY;
ALTER TABLE pipelines          ENABLE ROW LEVEL SECURITY;
ALTER TABLE sources            ENABLE ROW LEVEL SECURITY;
ALTER TABLE earnings           ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_events   ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions      ENABLE ROW LEVEL SECURITY;
ALTER TABLE social_accounts    ENABLE ROW LEVEL SECURITY;
ALTER TABLE swarm_configs      ENABLE ROW LEVEL SECURITY;
ALTER TABLE swarm_jobs         ENABLE ROW LEVEL SECURITY;


-- ============================================
-- SECTION 2: profiles
-- Primary key: id (= auth.uid() for that user)
-- Users may only read and update their own row.
-- INSERT is handled by the auth trigger (system/service role).
-- DELETE is soft-delete via update; no hard-delete policy needed.
-- ============================================

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'profiles'
      AND policyname = 'Users can view own profile'
  ) THEN
    CREATE POLICY "Users can view own profile"
        ON profiles FOR SELECT
        USING (id = auth.uid());
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'profiles'
      AND policyname = 'Users can update own profile'
  ) THEN
    CREATE POLICY "Users can update own profile"
        ON profiles FOR UPDATE
        USING (id = auth.uid())
        WITH CHECK (id = auth.uid());
  END IF;
END $$;


-- ============================================
-- SECTION 3: clips
-- Foreign key: user_id → auth.users(id)
-- ============================================

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'clips'
      AND policyname = 'Users can view own clips'
  ) THEN
    CREATE POLICY "Users can view own clips"
        ON clips FOR SELECT
        USING (user_id = auth.uid());
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'clips'
      AND policyname = 'Users can insert own clips'
  ) THEN
    CREATE POLICY "Users can insert own clips"
        ON clips FOR INSERT
        WITH CHECK (user_id = auth.uid());
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'clips'
      AND policyname = 'Users can update own clips'
  ) THEN
    CREATE POLICY "Users can update own clips"
        ON clips FOR UPDATE
        USING (user_id = auth.uid())
        WITH CHECK (user_id = auth.uid());
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'clips'
      AND policyname = 'Users can delete own clips'
  ) THEN
    CREATE POLICY "Users can delete own clips"
        ON clips FOR DELETE
        USING (user_id = auth.uid());
  END IF;
END $$;


-- ============================================
-- SECTION 4: pipelines
-- Foreign key: user_id → auth.users(id)
-- ============================================

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'pipelines'
      AND policyname = 'Users can view own pipelines'
  ) THEN
    CREATE POLICY "Users can view own pipelines"
        ON pipelines FOR SELECT
        USING (user_id = auth.uid());
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'pipelines'
      AND policyname = 'Users can insert own pipelines'
  ) THEN
    CREATE POLICY "Users can insert own pipelines"
        ON pipelines FOR INSERT
        WITH CHECK (user_id = auth.uid());
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'pipelines'
      AND policyname = 'Users can update own pipelines'
  ) THEN
    CREATE POLICY "Users can update own pipelines"
        ON pipelines FOR UPDATE
        USING (user_id = auth.uid())
        WITH CHECK (user_id = auth.uid());
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'pipelines'
      AND policyname = 'Users can delete own pipelines'
  ) THEN
    CREATE POLICY "Users can delete own pipelines"
        ON pipelines FOR DELETE
        USING (user_id = auth.uid());
  END IF;
END $$;


-- ============================================
-- SECTION 5: sources
-- Foreign key: user_id → auth.users(id)
-- ============================================

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'sources'
      AND policyname = 'Users can view own sources'
  ) THEN
    CREATE POLICY "Users can view own sources"
        ON sources FOR SELECT
        USING (user_id = auth.uid());
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'sources'
      AND policyname = 'Users can insert own sources'
  ) THEN
    CREATE POLICY "Users can insert own sources"
        ON sources FOR INSERT
        WITH CHECK (user_id = auth.uid());
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'sources'
      AND policyname = 'Users can update own sources'
  ) THEN
    CREATE POLICY "Users can update own sources"
        ON sources FOR UPDATE
        USING (user_id = auth.uid())
        WITH CHECK (user_id = auth.uid());
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'sources'
      AND policyname = 'Users can delete own sources'
  ) THEN
    CREATE POLICY "Users can delete own sources"
        ON sources FOR DELETE
        USING (user_id = auth.uid());
  END IF;
END $$;


-- ============================================
-- SECTION 6: earnings
-- Foreign key: user_id → auth.users(id)
-- Earnings records are written by the system (Stripe webhooks / service role).
-- Authenticated users may only read their own rows.
-- ============================================

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'earnings'
      AND policyname = 'Users can view own earnings'
  ) THEN
    CREATE POLICY "Users can view own earnings"
        ON earnings FOR SELECT
        USING (user_id = auth.uid());
  END IF;
END $$;


-- ============================================
-- SECTION 7: analytics_events
-- Foreign key: user_id → auth.users(id)
-- Users may INSERT their own events and SELECT their own events.
-- No UPDATE/DELETE — events are append-only audit records.
-- ============================================

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'analytics_events'
      AND policyname = 'Users can insert own analytics events'
  ) THEN
    CREATE POLICY "Users can insert own analytics events"
        ON analytics_events FOR INSERT
        WITH CHECK (user_id = auth.uid());
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'analytics_events'
      AND policyname = 'Users can view own analytics events'
  ) THEN
    CREATE POLICY "Users can view own analytics events"
        ON analytics_events FOR SELECT
        USING (user_id = auth.uid());
  END IF;
END $$;


-- ============================================
-- SECTION 8: subscriptions
-- Foreign key: user_id → auth.users(id)
-- INSERT/UPDATE are performed by the Stripe webhook handler via
-- the service-role key and are therefore not subject to RLS.
-- Authenticated users may only read their own subscription row.
-- ============================================

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'subscriptions'
      AND policyname = 'Users can view own subscription'
  ) THEN
    CREATE POLICY "Users can view own subscription"
        ON subscriptions FOR SELECT
        USING (user_id = auth.uid());
  END IF;
END $$;


-- ============================================
-- SECTION 9: social_accounts
-- Foreign key: user_id → auth.users(id)
-- ============================================

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'social_accounts'
      AND policyname = 'Users can view own social accounts'
  ) THEN
    CREATE POLICY "Users can view own social accounts"
        ON social_accounts FOR SELECT
        USING (user_id = auth.uid());
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'social_accounts'
      AND policyname = 'Users can insert own social accounts'
  ) THEN
    CREATE POLICY "Users can insert own social accounts"
        ON social_accounts FOR INSERT
        WITH CHECK (user_id = auth.uid());
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'social_accounts'
      AND policyname = 'Users can update own social accounts'
  ) THEN
    CREATE POLICY "Users can update own social accounts"
        ON social_accounts FOR UPDATE
        USING (user_id = auth.uid())
        WITH CHECK (user_id = auth.uid());
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'social_accounts'
      AND policyname = 'Users can delete own social accounts'
  ) THEN
    CREATE POLICY "Users can delete own social accounts"
        ON social_accounts FOR DELETE
        USING (user_id = auth.uid());
  END IF;
END $$;


-- ============================================
-- SECTION 10: swarm_configs
-- Foreign key: user_id → auth.users(id)
-- One config row per user (upserted by the app).
-- ============================================

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'swarm_configs'
      AND policyname = 'Users can view own swarm config'
  ) THEN
    CREATE POLICY "Users can view own swarm config"
        ON swarm_configs FOR SELECT
        USING (user_id = auth.uid());
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'swarm_configs'
      AND policyname = 'Users can insert own swarm config'
  ) THEN
    CREATE POLICY "Users can insert own swarm config"
        ON swarm_configs FOR INSERT
        WITH CHECK (user_id = auth.uid());
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'swarm_configs'
      AND policyname = 'Users can update own swarm config'
  ) THEN
    CREATE POLICY "Users can update own swarm config"
        ON swarm_configs FOR UPDATE
        USING (user_id = auth.uid())
        WITH CHECK (user_id = auth.uid());
  END IF;
END $$;


-- ============================================
-- SECTION 11: swarm_jobs
-- Foreign key: user_id → auth.users(id)
-- Users may SELECT, INSERT, and UPDATE (status/result) their own jobs.
-- DELETE is not exposed; jobs are retained for audit/billing history.
-- ============================================

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'swarm_jobs'
      AND policyname = 'Users can view own swarm jobs'
  ) THEN
    CREATE POLICY "Users can view own swarm jobs"
        ON swarm_jobs FOR SELECT
        USING (user_id = auth.uid());
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'swarm_jobs'
      AND policyname = 'Users can insert own swarm jobs'
  ) THEN
    CREATE POLICY "Users can insert own swarm jobs"
        ON swarm_jobs FOR INSERT
        WITH CHECK (user_id = auth.uid());
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'swarm_jobs'
      AND policyname = 'Users can update own swarm jobs'
  ) THEN
    CREATE POLICY "Users can update own swarm jobs"
        ON swarm_jobs FOR UPDATE
        USING (user_id = auth.uid())
        WITH CHECK (user_id = auth.uid());
  END IF;
END $$;


-- ============================================
-- SECTION 12: C-09 fix — missing DELETE policies on 002 tables
-- 002_ab_testing.sql added SELECT/INSERT/UPDATE but omitted DELETE.
-- ============================================

-- ab_tests: users may delete their own tests
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'ab_tests'
      AND policyname = 'Users can delete own A/B tests'
  ) THEN
    CREATE POLICY "Users can delete own A/B tests"
        ON ab_tests FOR DELETE
        USING (user_id = auth.uid());
  END IF;
END $$;

-- proven_hooks: users may delete their own proven hooks
-- (Also adds INSERT/UPDATE that 002 omitted for this table.)
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'proven_hooks'
      AND policyname = 'Users can insert own proven hooks'
  ) THEN
    CREATE POLICY "Users can insert own proven hooks"
        ON proven_hooks FOR INSERT
        WITH CHECK (user_id = auth.uid());
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'proven_hooks'
      AND policyname = 'Users can update own proven hooks'
  ) THEN
    CREATE POLICY "Users can update own proven hooks"
        ON proven_hooks FOR UPDATE
        USING (user_id = auth.uid())
        WITH CHECK (user_id = auth.uid());
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'proven_hooks'
      AND policyname = 'Users can delete own proven hooks'
  ) THEN
    CREATE POLICY "Users can delete own proven hooks"
        ON proven_hooks FOR DELETE
        USING (user_id = auth.uid());
  END IF;
END $$;

-- clip_revisions: append-only audit trail.
-- Users may INSERT their own revisions and SELECT them.
-- UPDATE/DELETE intentionally omitted to preserve audit integrity.
-- Only adds the INSERT policy missing from 002 (which only had SELECT).
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'clip_revisions'
      AND policyname = 'Users can insert own clip revisions'
  ) THEN
    CREATE POLICY "Users can insert own clip revisions"
        ON clip_revisions FOR INSERT
        WITH CHECK (user_id = auth.uid());
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'clip_revisions'
      AND policyname = 'Users can delete own clip revisions'
  ) THEN
    CREATE POLICY "Users can delete own clip revisions"
        ON clip_revisions FOR DELETE
        USING (user_id = auth.uid());
  END IF;
END $$;
