-- Migration 005: Missing FK and lookup indexes (L-05)
-- Covers: proven_hooks.test_id, ab_tests.pipeline_id,
-- and other FK columns that lack backing indexes.

-- proven_hooks.test_id → ab_tests(id) lookups
CREATE INDEX IF NOT EXISTS idx_proven_hooks_test_id
    ON proven_hooks (test_id);

-- ab_tests.pipeline_id — used in WHERE clauses when filtering by pipeline
CREATE INDEX IF NOT EXISTS idx_ab_tests_pipeline_id
    ON ab_tests (pipeline_id);

-- ab_tests.user_id + status — most common query pattern for listing tests
CREATE INDEX IF NOT EXISTS idx_ab_tests_user_status
    ON ab_tests (user_id, status);

-- ab_tests.original_clip_id — looked up in get_ab_test_status
CREATE INDEX IF NOT EXISTS idx_ab_tests_original_clip_id
    ON ab_tests (original_clip_id);

-- clip_revisions.clip_id — used when fetching revision history for a clip
CREATE INDEX IF NOT EXISTS idx_clip_revisions_clip_id
    ON clip_revisions (clip_id);

-- swarm_batch_jobs.user_id (simple, if not already covered by migration 004)
CREATE INDEX IF NOT EXISTS idx_swarm_batch_jobs_user_id
    ON swarm_batch_jobs (user_id);
