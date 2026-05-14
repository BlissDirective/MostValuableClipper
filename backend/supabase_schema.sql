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
