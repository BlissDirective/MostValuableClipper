import { Pipeline, PipelineStatus, PlatformKey, AutonomyMode, RetentionPolicy, PipelineSource, WarningCategoryKey } from './store';
import type { Pipeline as BackendPipeline, Clip as BackendClip, VideoSource as BackendSource } from './api';
import type { ClipCardData, ClipState } from '@/components/ClipCard';
import type { SafetyVariant } from '@/components/SafetyFlag';

/**
 * Maps a backend pipeline to the frontend Pipeline format.
 * Backend fields: id, name, theme, niche, status, retention_policy, target_platforms, clips_count, views_delta, etc.
 * Frontend fields: id, themeName, niche, status, clipsThisWeek, viewDelta, deltaVariant, clipsPerDay, platforms, autonomy, resolverOn, retention, warningCategories, sources, sourcePlan
 */
export function mapBackendToPipeline(backend: any): Pipeline {
  const statusMap: Record<string, PipelineStatus> = {
    'running': 'running',
    'paused': 'paused',
    'errored': 'errored',
    'setup-incomplete': 'setup-incomplete',
  };

  const platformMap: Record<string, PlatformKey> = {
    'tiktok': 'tiktok',
    'instagram': 'instagram',
    'youtube': 'youtube',
    'facebook': 'youtube', // fallback
  };

  const autonomy: AutonomyMode = 'fullAuto'; // default until backend stores this
  const retention: RetentionPolicy = (backend.retention_policy as RetentionPolicy) || 'moderate';
  const status = statusMap[backend.status] || 'setup-incomplete';

  // Compute delta variant from views_delta string
  let viewDelta = backend.views_delta || '—';
  let deltaVariant: 'positive' | 'negative' | 'default' = 'default';
  if (viewDelta.includes('+')) deltaVariant = 'positive';
  else if (viewDelta.includes('-')) deltaVariant = 'negative';

  // Derive clipsPerDay from post_schedule if available
  let clipsPerDay = 2;
  if (backend.post_schedule?.times) {
    clipsPerDay = backend.post_schedule.times.length;
  }

  // Map target_platforms
  const platforms: PlatformKey[] = (backend.target_platforms || [])
    .map((p: string) => platformMap[p])
    .filter(Boolean) as PlatformKey[];

  const defaultWarning: Record<WarningCategoryKey, boolean> = {
    newsPolitical: true,
    health: true,
    finance: true,
    children: true,
    identifiableIndividual: true,
    violentGraphic: true,
  };

  // Default sources (empty until sources API is wired in Phase 4)
  const sources: PipelineSource[] = [];

  return {
    id: backend.id,
    themeName: backend.name || backend.theme || 'Untitled',
    niche: backend.niche || '',
    status,
    clipsThisWeek: backend.clips_count || 0,
    viewDelta,
    deltaVariant,
    clipsPerDay,
    platforms: platforms.length > 0 ? platforms : ['tiktok'],
    autonomy,
    resolverOn: true,
    retention,
    warningCategories: defaultWarning,
    sources,
    sourcePlan: { uploads: true, creatorLicensed: false, ccArchive: false },
  };
}

/**
 * Maps frontend PipelineCreate fields to backend format.
 */
export function mapPipelineToBackend(frontend: Partial<Pipeline>): any {
  return {
    name: frontend.themeName,
    theme: frontend.themeName,
    niche: frontend.niche,
    target_platforms: frontend.platforms || ['tiktok'],
    retention_policy: frontend.retention || 'moderate',
    min_clip_length_seconds: 15,
    max_clip_length_seconds: 90,
  };
}

/**
 * Maps a backend Source to frontend PipelineSource.
 */
export function mapBackendToPipelineSource(backend: any): PipelineSource {
  const kindMap: Record<string, PipelineSource['kind']> = {
    'upload': 'upload',
    'creator-licensed': 'creator-licensed',
    'cc-archive': 'cc-archive',
    'youtube': 'creator-licensed',
    'rss': 'creator-licensed',
    'twitch': 'creator-licensed',
  };

  const statusMap: Record<string, PipelineSource['status']> = {
    'ingested': 'ingested',
    'pending': 'pending',
    'failed': 'failed',
    'processing': 'pending',
    'active': 'ingested',
    'inactive': 'failed',
  };

  return {
    id: backend.id,
    kind: kindMap[backend.source_type || backend.kind] || 'upload',
    name: backend.name || backend.title || 'Untitled source',
    status: statusMap[backend.status] || 'pending',
  };
}

// ── Clip Mappers ──────────────────────────────────────────────────

const statusToState: Record<string, ClipState> = {
  'pending': 'queued',
  'queued': 'queued',
  'generating': 'processing',
  'ready_for_review': 'queued',
  'approved': 'queued',
  'posted': 'posted',
  'rejected': 'failed',
  'failed': 'failed',
};

const platformMap: Record<string, PlatformKey> = {
  'tiktok': 'tiktok',
  'instagram': 'instagram',
  'youtube': 'youtube',
  'facebook': 'youtube',
};

/**
 * Maps a backend Clip to frontend ClipCardData.
 */
export function mapBackendToClipCard(backend: any): ClipCardData {
  // Derive state from backend status + safety flags
  let state: ClipState = statusToState[backend.status] || 'queued';

  // Override with safety if present
  const safetyFlags = backend.safety_flags || [];
  let safety = null;
  if (safetyFlags.length > 0) {
    const isBlock = safetyFlags.some((f: any) =>
      typeof f === 'string'
        ? f.toLowerCase().includes('copyright') || f.toLowerCase().includes('block')
        : f.severity === 'block' || f.type?.toLowerCase().includes('copyright')
    );
    const variant: SafetyVariant = isBlock ? 'block' : 'warn';
    state = isBlock ? 'held-safety-block' : 'held-safety-warn';
    safety = {
      variant,
      categories: safetyFlags.map((f: any) => typeof f === 'string' ? f : f.reason || f.type || 'Safety flag'),
    };
  }

  // Map platforms from platform_posts or fallback
  const platforms = Object.keys(backend.platform_posts || {})
    .map((p) => ({ platform: platformMap[p] || 'tiktok' as PlatformKey, handle: backend.user_id ? '@studio' : undefined }));

  // Metrics from backend metrics object
  const metrics = backend.metrics || {};
  const views = metrics.views ? String(metrics.views) : undefined;
  const retention = metrics.retention ? String(metrics.retention) : undefined;
  const earnings = metrics.earnings ? String(metrics.earnings) : undefined;

  return {
    id: backend.id,
    sourceName: backend.source_id || backend.pipeline_id || 'Unknown source',
    caption: backend.caption || backend.description || 'No caption',
    platforms: platforms.length > 0 ? platforms : [{ platform: 'tiktok' }],
    metrics: views || retention || earnings
      ? { views, retention, earnings, retentionVariant: 'default' }
      : undefined,
    safety,
    state,
    queuedFor: state === 'queued' ? 'pending' : undefined,
  };
}

/**
 * Counts clips by status for the approval banner.
 */
export function countPendingClips(clips: ClipCardData[]): number {
  return clips.filter(c => c.state === 'queued' || c.state === 'held-safety-warn').length;
}
