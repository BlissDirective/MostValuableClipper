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

CREATE INDEX IF NOT EXISTS idx_swarm_batch_templates_user ON public.swarm_batch_templates(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_swarm_rate_limits_reset ON public.swarm_rate_limits(last_reset);

ALTER TABLE public.swarm_batch_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.swarm_rate_limits ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own batch templates" ON public.swarm_batch_templates FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can view own rate limits" ON public.swarm_rate_limits FOR ALL USING (auth.uid() = user_id);

ALTER PUBLICATION supabase_realtime ADD TABLE public.swarm_batch_templates;
