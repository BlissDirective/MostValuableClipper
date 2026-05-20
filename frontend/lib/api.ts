const BASE = (
  process.env.EXPO_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1'
).replace(/\/$/, '');

let _token: string | null = null;
export function setApiToken(t: string | null) {
  _token = t;
}

async function req<T = any>(
  method: string,
  path: string,
  body?: unknown,
  params?: Record<string, any>,
): Promise<T> {
  let url = BASE + path;
  if (params) {
    const qs = new URLSearchParams(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null)
        .map(([k, v]) => [k, String(v)]),
    ).toString();
    if (qs) url += '?' + qs;
  }
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (_token) headers['Authorization'] = `Bearer ${_token}`;
  const res = await fetch(url, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const e: any = new Error(err.detail ?? res.statusText);
    e.detail = err.detail;
    throw e;
  }
  const text = await res.text();
  return text ? JSON.parse(text) : ({} as T);
}

export interface Clip {
  id: string;
  title?: string;
  caption?: string;
  video_url?: string;
  thumbnail_url?: string;
  status?: string;
  safety_flags?: string[];
  duration_seconds?: number;
  hashtags?: string[];
  created_at?: string;
}

export const clipsApi = {
  getAll: (params?: Record<string, any>) => req('GET', '/clips', undefined, params),
  getById: (id: string) => req<{ data: Clip }>('GET', `/clips/${id}`).then((r) => ({ data: r as any })),
  approve: (id: string) => req('POST', `/clips/${id}/approve`),
  reject: (id: string) => req('POST', `/clips/${id}/reject`),
  delete: (id: string) => req('DELETE', `/clips/${id}`),
  downloadUrl: (id: string) => req<{ url: string }>('POST', `/clips/${id}/download-url`),
  remix: (id: string, opts: Record<string, any>) => req('POST', `/clips/${id}/remix`, opts),
};

export const pipelinesApi = {
  getAll: () => req('GET', '/pipelines'),
  create: (data: Record<string, any>) => req('POST', '/pipelines', data),
  toggle: (id: string) => req('POST', `/pipelines/${id}/toggle`),
};

export const sourcesApi = {
  getAll: () => req('GET', '/sources'),
  create: (data: Record<string, any>) => req('POST', '/sources', data),
  delete: (id: string) => req('DELETE', `/sources/${id}`),
};

export const earningsApi = {
  get: () => req('GET', '/earnings'),
};

export const analyticsApi = {
  getDashboard: () => req('GET', '/analytics/dashboard'),
};

export const swarmApi = {
  getAllocation: () => req('GET', '/swarm/allocation'),
  setAllocation: (allocation: Record<string, number>) =>
    req('POST', '/swarm/allocation', { allocation }),
  autoBalance: () => req('POST', '/swarm/allocation/auto-balance'),
  getConfig: () => req('GET', '/swarm/config'),
  runHooks: (clipId: string, platform: string, opts?: Record<string, any>) =>
    req('POST', '/swarm/hooks', { clip_id: clipId, platform, ...opts }),
  runRemix: (clipId: string, opts?: Record<string, any>) =>
    req('POST', '/swarm/remix', { clip_id: clipId, ...opts }),
  runPost: (clipIds: string[], opts?: Record<string, any>) =>
    req('POST', '/swarm/post', { clip_ids: clipIds, ...opts }),
  runABTest: (clipId: string, variantId: string, opts?: Record<string, any>) =>
    req('POST', '/swarm/ab-test', { clip_id: clipId, variant_id: variantId, ...opts }),
  runMusicMatch: (clipId: string, opts?: Record<string, any>) =>
    req('POST', '/swarm/music-match', { clip_id: clipId, ...opts }),
  runThumbnail: (clipId: string, opts?: Record<string, any>) =>
    req('POST', '/swarm/thumbnail', { clip_id: clipId, ...opts }),
  runSafety: (clipId: string, opts?: Record<string, any>) =>
    req('POST', '/swarm/safety', { clip_id: clipId, ...opts }),
  runHooksAnalysis: (clipId: string, platform: string, opts?: Record<string, any>) =>
    req('POST', '/swarm/hooks-analysis', { clip_id: clipId, platform, ...opts }),
  runSegmentAnalyze: (clipId: string, opts?: Record<string, any>) =>
    req('POST', '/swarm/segment-analyze', { clip_id: clipId, ...opts }),
  runEdit: (clipId: string, opts?: Record<string, any>) =>
    req('POST', '/swarm/edit', { clip_id: clipId, ...opts }),
  runBatch: (data: Record<string, any>) => req('POST', '/swarm/batch', data),
  getBatchJobs: (limit?: number) => req('GET', '/swarm/batch', undefined, limit ? { limit } : undefined),
  getBatchJob: (batchId: string) => req('GET', `/swarm/batch/${batchId}`),
};
