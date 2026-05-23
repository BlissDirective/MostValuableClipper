
-- ============================================
-- Analytics Aggregation Functions (P1 Fix)
-- True DB-level aggregation for O(1) performance regardless of clip count
-- ============================================

-- User-level stats: total clips, views, revenue
CREATE OR REPLACE FUNCTION get_user_stats(p_user_id UUID)
RETURNS TABLE (
    total_clips BIGINT,
    total_views BIGINT,
    total_revenue NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::BIGINT as total_clips,
        COALESCE(SUM(views), 0)::BIGINT as total_views,
        COALESCE(SUM(revenue), 0)::NUMERIC as total_revenue
    FROM clips
    WHERE user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- Platform breakdown for a user
CREATE OR REPLACE FUNCTION get_user_platform_breakdown(p_user_id UUID)
RETURNS TABLE (
    platform TEXT,
    count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COALESCE(post->>'platform', 'unknown') as platform,
        COUNT(*)::BIGINT
    FROM clips
    CROSS JOIN LATERAL jsonb_array_elements(COALESCE(platform_posts, '[]'::jsonb)) as post
    WHERE user_id = p_user_id
    GROUP BY COALESCE(post->>'platform', 'unknown');
END;
$$ LANGUAGE plpgsql;

-- Daily stats for last N days
CREATE OR REPLACE FUNCTION get_user_daily_stats(p_user_id UUID, p_days INTEGER DEFAULT 30)
RETURNS TABLE (
    date TEXT,
    clips BIGINT,
    views BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        created_at::DATE::TEXT as date,
        COUNT(*)::BIGINT as clips,
        COALESCE(SUM(views), 0)::BIGINT as views
    FROM clips
    WHERE user_id = p_user_id
      AND created_at >= (CURRENT_DATE - (p_days || ' days')::INTERVAL)
    GROUP BY created_at::DATE
    ORDER BY date DESC;
END;
$$ LANGUAGE plpgsql;

-- Pipeline-level stats
CREATE OR REPLACE FUNCTION get_pipeline_stats(p_pipeline_id UUID, p_user_id UUID)
RETURNS TABLE (
    total_clips BIGINT,
    posted_clips BIGINT,
    total_views BIGINT,
    engagement_rate NUMERIC
) AS $$
DECLARE
    v_total_views BIGINT;
    v_engagement BIGINT;
BEGIN
    -- Count total and posted clips
    RETURN QUERY
    SELECT 
        COUNT(*)::BIGINT,
        COUNT(*) FILTER (WHERE status = 'posted')::BIGINT,
        COALESCE(SUM(views), 0)::BIGINT,
        CASE 
            WHEN COALESCE(SUM(views), 0) = 0 THEN 0::NUMERIC
            ELSE ROUND(
                (COALESCE(SUM(likes), 0) + COALESCE(SUM(comments), 0) + COALESCE(SUM(shares), 0))::NUMERIC 
                / NULLIF(SUM(views), 0) * 100, 
                2
            )
        END
    FROM clips
    WHERE pipeline_id = p_pipeline_id AND user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- Grant execute to authenticated users via RLS
GRANT EXECUTE ON FUNCTION get_user_stats(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION get_user_platform_breakdown(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION get_user_daily_stats(UUID, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION get_pipeline_stats(UUID, UUID) TO authenticated;
