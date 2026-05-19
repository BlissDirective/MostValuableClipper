-- MVC Database Schema for Supabase
-- Run this in the Supabase SQL Editor

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================
-- USERS & AUTH (handled by Supabase Auth)
-- ============================================
-- Profiles table extends Supabase Auth users
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    full_name TEXT,
    avatar_url TEXT,
    subscription_tier TEXT DEFAULT 'free' CHECK (subscription_tier IN ('free', 'basic', 'pro', 'enterprise')),
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    autonomy_mode TEXT DEFAULT 'approveEach' CHECK (autonomy_mode IN ('fullAuto', 'approveEach', 'suggestOnly')),
    cohort_opt_in BOOLEAN DEFAULT FALSE,
    onboarding_completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trigger to create profile on user signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, email, full_name, created_at, updated_at)
    VALUES (NEW.id, NEW.email, NEW.raw_user_meta_data->>'full_name', NOW(), NOW());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

-- ============================================
-- SUBSCRIPTIONS
-- ============================================
CREATE TABLE IF NOT EXISTS public.subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    stripe_price_id TEXT,
    tier TEXT NOT NULL CHECK (tier IN ('free', 'basic', 'pro', 'enterprise')),
    status TEXT NOT NULL CHECK (status IN ('active', 'canceled', 'past_due', 'unpaid', 'trialing')),
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- SOCIAL ACCOUNTS
-- ============================================
CREATE TABLE IF NOT EXISTS public.social_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    platform TEXT NOT NULL CHECK (platform IN ('tiktok', 'instagram', 'youtube', 'facebook')),
    handle TEXT,
    account_id TEXT,
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at TIMESTAMPTZ,
    follower_count INTEGER DEFAULT 0,
    eligible_for_program BOOLEAN DEFAULT FALSE,
    connected_at TIMESTAMPTZ DEFAULT NOW(),
    last_synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, platform)
);

-- ============================================
-- PIPELINES
-- ============================================
CREATE TABLE IF NOT EXISTS public.pipelines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    theme TEXT NOT NULL,
    niche TEXT,
    status TEXT DEFAULT 'setup-incomplete' CHECK (status IN ('running', 'paused', 'errored', 'setup-incomplete')),
    retention_policy TEXT DEFAULT 'moderate' CHECK (retention_policy IN ('aggressive', 'moderate', 'indefinite')),
    min_clip_length_seconds INTEGER DEFAULT 15,
    max_clip_length_seconds INTEGER DEFAULT 90,
    post_schedule JSONB DEFAULT '{"weekdays": [1,2,3,4,5], "times": ["09:00", "15:00", "19:00"]}',
    target_platforms TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- CLIPS
-- ============================================
CREATE TABLE IF NOT EXISTS public.clips (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    pipeline_id UUID REFERENCES public.pipelines(id) ON DELETE SET NULL,
    source_id UUID,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'queued', 'generating', 'ready_for_review', 'approved', 'posted', 'rejected', 'failed')),
    caption TEXT,
    description TEXT,
    tags TEXT[] DEFAULT '{}',
    thumbnail_url TEXT,
    video_url TEXT,
    video_duration INTEGER,
    platform_posts JSONB DEFAULT '{}',
    safety_flags JSONB DEFAULT '[]',
    metrics JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    posted_at TIMESTAMPTZ
);

-- ============================================
-- SOURCES (Raw video sources)
-- ============================================
CREATE TABLE IF NOT EXISTS public.sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    pipeline_id UUID REFERENCES public.pipelines(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    description TEXT,
    original_url TEXT,
    storage_path TEXT,
    duration INTEGER,
    status TEXT DEFAULT 'processing' CHECK (status IN ('uploading', 'processing', 'ready', 'failed')),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add clips foreign key to sources (must be after sources table exists)
ALTER TABLE public.clips ADD CONSTRAINT fk_clips_source
    FOREIGN KEY (source_id) REFERENCES public.sources(id) ON DELETE SET NULL;

-- ============================================
-- PLATFORM POSTS (Individual platform postings)
-- ============================================
CREATE TABLE IF NOT EXISTS public.platform_posts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    clip_id UUID NOT NULL REFERENCES public.clips(id) ON DELETE CASCADE,
    platform TEXT NOT NULL CHECK (platform IN ('tiktok', 'instagram', 'youtube', 'facebook')),
    post_id TEXT,
    post_url TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'posted', 'failed', 'removed')),
    posted_at TIMESTAMPTZ,
    metrics JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- EARNINGS
-- ============================================
CREATE TABLE IF NOT EXISTS public.earnings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    revenue_cents INTEGER DEFAULT 0,
    currency TEXT DEFAULT 'USD',
    views INTEGER DEFAULT 0,
    breakdown JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, platform, period_start)
);

-- ============================================
-- ANALYTICS EVENTS
-- ============================================
CREATE TABLE IF NOT EXISTS public.analytics_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    event_data JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- INDEXES
-- ============================================
CREATE INDEX IF NOT EXISTS idx_clips_user_status ON public.clips(user_id, status);
CREATE INDEX IF NOT EXISTS idx_clips_pipeline ON public.clips(pipeline_id);
CREATE INDEX IF NOT EXISTS idx_sources_user ON public.sources(user_id);
CREATE INDEX IF NOT EXISTS idx_pipelines_user ON public.pipelines(user_id);
CREATE INDEX IF NOT EXISTS idx_platform_posts_clip ON public.platform_posts(clip_id);
CREATE INDEX IF NOT EXISTS idx_earnings_user_period ON public.earnings(user_id, period_start);
CREATE INDEX IF NOT EXISTS idx_analytics_events_user ON public.analytics_events(user_id, created_at);

-- ============================================
-- ROW LEVEL SECURITY POLICIES
-- ============================================
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.social_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pipelines ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.clips ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.platform_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.earnings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analytics_events ENABLE ROW LEVEL SECURITY;

-- Users can only see their own data
CREATE POLICY "Users can view own profile" ON public.profiles
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON public.profiles
    FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Users can view own subscriptions" ON public.subscriptions
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can view own social accounts" ON public.social_accounts
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can view own pipelines" ON public.pipelines
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can view own clips" ON public.clips
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can view own sources" ON public.sources
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can view own earnings" ON public.earnings
    FOR SELECT USING (auth.uid() = user_id);

-- ============================================
-- REALTIME SUBSCRIPTIONS (for live updates)
-- ============================================
BEGIN;
  -- Enable realtime for key tables
  ALTER PUBLICATION supabase_realtime ADD TABLE public.clips;
  ALTER PUBLICATION supabase_realtime ADD TABLE public.pipelines;
  ALTER PUBLICATION supabase_realtime ADD TABLE public.platform_posts;
COMMIT;

-- ============================================
-- SWARM SYSTEM
-- ============================================

-- User swarm configuration (agent allocation, tier, budgets)
CREATE TABLE IF NOT EXISTS public.swarm_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    tier TEXT DEFAULT 'free' CHECK (tier IN ('free', 'basic', 'pro', 'enterprise')),
    total_max_agents INTEGER DEFAULT 1,
    auto_balance BOOLEAN DEFAULT TRUE,
    enabled_pools TEXT[] DEFAULT ARRAY['hook','remix','post','ab_test','music_match','thumbnail','safety','hooks_analysis','segment_analyze','edit'],
    agent_allocation JSONB DEFAULT '{"hook": 1, "remix": 1, "post": 1}',
    agent_behavior JSONB DEFAULT '{}',
    daily_budget_cents INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);

-- Swarm execution jobs
CREATE TABLE IF NOT EXISTS public.swarm_jobs (
    job_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    job_type TEXT NOT NULL CHECK (job_type IN ('hook','remix','post','ab_test','music_match','thumbnail','safety','hooks_analysis','segment_analyze','edit')),
    status TEXT DEFAULT 'queued' CHECK (status IN ('queued','running','completed','failed','partial')),
    total_agents INTEGER DEFAULT 0,
    completed_agents INTEGER DEFAULT 0,
    failed_agents INTEGER DEFAULT 0,
    results_summary JSONB DEFAULT '{}',
    cost_cents INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Per-agent results within a swarm job
CREATE TABLE IF NOT EXISTS public.swarm_agent_results (
    result_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES public.swarm_jobs(job_id) ON DELETE CASCADE,
    agent_index INTEGER DEFAULT 0,
    agent_persona TEXT,
    status TEXT DEFAULT 'pending',
    result_data JSONB DEFAULT '{}',
    cost_cents INTEGER DEFAULT 0,
    duration_ms INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- BATCH SWARM JOBS (Phase 1: Cost-Optimized Batch Execution)
-- ============================================

-- Batch job tracking for multi-clip swarm execution
CREATE TABLE IF NOT EXISTS public.swarm_batch_jobs (
    batch_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    pool_type TEXT NOT NULL CHECK (pool_type IN ('hook', 'remix', 'post', 'ab_test', 'music_match', 'thumbnail', 'safety', 'hooks_analysis', 'segment_analyze', 'edit')),
    clip_ids UUID[] NOT NULL,
    total_clips INTEGER NOT NULL DEFAULT 0,
    processed_clips INTEGER DEFAULT 0,
    failed_clips INTEGER DEFAULT 0,
    current_clip_id UUID,
    status TEXT DEFAULT 'queued' CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled')),
    shared_context JSONB DEFAULT '{}',
    agent_count INTEGER DEFAULT 1,
    strategy_filter TEXT[],
    custom_options JSONB DEFAULT '{}',
    results_summary JSONB DEFAULT '{}',
    cost_cents INTEGER DEFAULT 0,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Per-clip results within a batch job
CREATE TABLE IF NOT EXISTS public.swarm_batch_clip_results (
    result_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    batch_id UUID NOT NULL REFERENCES public.swarm_batch_jobs(batch_id) ON DELETE CASCADE,
    clip_id UUID NOT NULL REFERENCES public.clips(id) ON DELETE CASCADE,
    agent_index INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    result_data JSONB DEFAULT '{}',
    cost_cents INTEGER DEFAULT 0,
    duration_ms INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- INDEXES (Batch Swarm)
-- ============================================
CREATE INDEX IF NOT EXISTS idx_swarm_batch_jobs_user ON public.swarm_batch_jobs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_swarm_batch_jobs_status ON public.swarm_batch_jobs(status);
CREATE INDEX IF NOT EXISTS idx_swarm_batch_clip_results_batch ON public.swarm_batch_clip_results(batch_id);
CREATE INDEX IF NOT EXISTS idx_swarm_batch_clip_results_clip ON public.swarm_batch_clip_results(clip_id);

-- ============================================
-- ROW LEVEL SECURITY (Batch Swarm)
-- ============================================
ALTER TABLE public.swarm_batch_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.swarm_batch_clip_results ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own batch jobs" ON public.swarm_batch_jobs
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can view own batch clip results" ON public.swarm_batch_clip_results
    FOR ALL USING (
        batch_id IN (
            SELECT batch_id FROM public.swarm_batch_jobs WHERE user_id = auth.uid()
        )
    );

-- ============================================
-- REALTIME SUBSCRIPTIONS (Batch Swarm)
-- ============================================
BEGIN;
  ALTER PUBLICATION supabase_realtime ADD TABLE public.swarm_batch_jobs;
COMMIT;

-- Batch templates for saved configurations
CREATE TABLE IF NOT EXISTS public.swarm_batch_templates (
    template_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    pool_type TEXT NOT NULL CHECK (pool_type IN ('hook', 'remix', 'post', 'ab_test', 'music_match', 'thumbnail', 'safety', 'hooks_analysis', 'segment_analyze', 'edit')),
    agent_count INTEGER DEFAULT 1,
    strategy_filter TEXT[],
    priority TEXT DEFAULT 'balanced',
    shared_context BOOLEAN DEFAULT true,
    custom_options JSONB DEFAULT '{}',
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Rate limit tracking per user
CREATE TABLE IF NOT EXISTS public.swarm_rate_limits (
    user_id UUID PRIMARY KEY REFERENCES public.profiles(id) ON DELETE CASCADE,
    concurrent_batches INTEGER DEFAULT 0,
    max_concurrent INTEGER DEFAULT 2,
    daily_clip_count INTEGER DEFAULT 0,
    max_daily_clips INTEGER DEFAULT 500,
    last_reset TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- INDEXES (Batch Templates & Rate Limits)
-- ============================================
CREATE INDEX IF NOT EXISTS idx_swarm_batch_templates_user ON public.swarm_batch_templates(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_swarm_rate_limits_reset ON public.swarm_rate_limits(last_reset);

-- ============================================
-- ROW LEVEL SECURITY (Batch Templates & Rate Limits)
-- ============================================
ALTER TABLE public.swarm_batch_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.swarm_rate_limits ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own batch templates" ON public.swarm_batch_templates
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can view own rate limits" ON public.swarm_rate_limits
    FOR ALL USING (auth.uid() = user_id);

-- ============================================
-- REALTIME SUBSCRIPTIONS (Batch Templates)
-- ============================================
BEGIN;
  ALTER PUBLICATION supabase_realtime ADD TABLE public.swarm_batch_templates;
COMMIT;
-- ============================================
CREATE INDEX IF NOT EXISTS idx_swarm_configs_user ON public.swarm_configs(user_id);
CREATE INDEX IF NOT EXISTS idx_swarm_jobs_user ON public.swarm_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_swarm_jobs_status ON public.swarm_jobs(status);
CREATE INDEX IF NOT EXISTS idx_swarm_jobs_created ON public.swarm_jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_swarm_agent_results_job ON public.swarm_agent_results(job_id);

-- ============================================
-- ROW LEVEL SECURITY (Swarm)
-- ============================================
ALTER TABLE public.swarm_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.swarm_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.swarm_agent_results ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own swarm config" ON public.swarm_configs
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can view own swarm jobs" ON public.swarm_jobs
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can view own swarm agent results" ON public.swarm_agent_results
    FOR ALL USING (
        job_id IN (
            SELECT job_id FROM public.swarm_jobs WHERE user_id = auth.uid()
        )
    );

-- ============================================
-- REALTIME SUBSCRIPTIONS (Swarm)
-- ============================================
BEGIN;
  ALTER PUBLICATION supabase_realtime ADD TABLE public.swarm_jobs;
COMMIT;
