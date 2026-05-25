import { Platform } from "react-native";

/**
 * API Client with Resilient Fetch
 * 
 * Features:
 * - Automatic retry with exponential backoff + jitter
 * - Request deduplication (concurrent identical requests share one promise)
 * - Circuit breaker for repeated failures
 * - 429 rate limit handling with Retry-After header
 * - Timeout support
 */

const BASE = (
  process.env.EXPO_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1'
).replace(/\/+$/, '');

let _token: string | null = null;
export function setApiToken(t: string | null) {
  _token = t;
}

// Callback supplied by store.ts so the API layer can retrieve the refresh token
// and re-authenticate without importing the store (avoids circular deps).
type RefreshCallback = () => Promise<string | null>;
let _refreshCallback: RefreshCallback | null = null;
export function setRefreshCallback(cb: RefreshCallback) {
  _refreshCallback = cb;
}

let _isRefreshing = false;
let _refreshWaiters: Array<(token: string | null) => void> = [];

async function refreshAccessToken(): Promise<string | null> {
  if (_isRefreshing) {
    // Queue callers while a refresh is in flight
    return new Promise((resolve) => _refreshWaiters.push(resolve));
  }
  _isRefreshing = true;
  try {
    const refreshToken = await _refreshCallback?.();
    if (!refreshToken) return null;

    const res = await fetch(`${BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) return null;

    const data = await res.json();
    const newToken: string | null = data.access_token ?? null;
    if (newToken) {
      setApiToken(newToken);
      // Persist back to SecureStore via the same callback infrastructure
      // (store.ts handles persistence when setApiToken is called externally)
    }
    _refreshWaiters.forEach((r) => r(newToken));
    return newToken;
  } catch {
    _refreshWaiters.forEach((r) => r(null));
    return null;
  } finally {
    _isRefreshing = false;
    _refreshWaiters = [];
  }
}

/* ── Deduplication ── */
const inFlight = new Map<string, Promise<any>>();
function getDedupeKey(method: string, url: string, body?: string): string {
  return `${method}:${url}:${body || ""}`;
}

/* ── Circuit Breaker ── */
interface CircuitState {
  failures: number;
  lastFailure: number;
  state: "closed" | "open" | "half-open";
}
const circuits = new Map<string, CircuitState>();
const CIRCUIT_THRESHOLD = 5;
const CIRCUIT_TIMEOUT = 30000;

function getCircuitKey(url: string): string {
  try {
    const u = new URL(url);
    return `${u.protocol}//${u.host}`;
  } catch {
    return url.split("/").slice(0, 3).join("/");
  }
}

function checkCircuit(url: string): boolean {
  const key = getCircuitKey(url);
  const state = circuits.get(key);
  if (!state || state.state === "closed") return true;
  if (state.state === "open") {
    if (Date.now() - state.lastFailure > CIRCUIT_TIMEOUT) {
      state.state = "half-open";
      return true;
    }
    return false;
  }
  return true;
}

function recordSuccess(url: string): void {
  const key = getCircuitKey(url);
  const state = circuits.get(key);
  if (state) {
    state.failures = 0;
    state.state = "closed";
  }
}

function recordFailure(url: string): void {
  const key = getCircuitKey(url);
  let state = circuits.get(key);
  if (!state) {
    state = { failures: 0, lastFailure: 0, state: "closed" };
    circuits.set(key, state);
  }
  state.failures++;
  state.lastFailure = Date.now();
  if (state.failures >= CIRCUIT_THRESHOLD) {
    state.state = "open";
  }
}

/* ── Retry Configuration ── */
const MAX_RETRIES = 3;
const BASE_DELAY_MS = 500;
const MAX_DELAY_MS = 8000;
const RETRYABLE_STATUS_CODES = [408, 429, 500, 502, 503, 504];

function backoff(attempt: number): number {
  const exp = Math.min(attempt, 6);
  const base = BASE_DELAY_MS * Math.pow(2, exp);
  const jitter = Math.random() * 0.3 * base;
  return Math.min(base + jitter, MAX_DELAY_MS);
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/* ── Core resilient fetch ── */
async function resilientFetchInternal(
  url: string,
  init: RequestInit,
  retries = MAX_RETRIES,
): Promise<Response> {
  if (!checkCircuit(url)) {
    throw new Error("Circuit breaker open — too many failures. Retry shortly.");
  }

  let lastErr: any;
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000);

      const res = await fetch(url, { ...init, signal: controller.signal });
      clearTimeout(timeoutId);

      if (res.ok) {
        recordSuccess(url);
        return res;
      }

      // Retry on retryable status codes
      if (RETRYABLE_STATUS_CODES.includes(res.status) && attempt < retries) {
        if (res.status === 429) {
          const retryAfter = res.headers.get("Retry-After");
          if (retryAfter) {
            await sleep(parseInt(retryAfter) * 1000);
          } else {
            await sleep(backoff(attempt));
          }
        } else {
          await sleep(backoff(attempt));
        }
        continue;
      }

      // Non-retryable error
      lastErr = new Error(`HTTP ${res.status}: ${res.statusText}`);
      break;
    } catch (err: any) {
      lastErr = err;
      const isRetryable =
        err.name === "TypeError" ||
        err.name === "AbortError" ||
        err.message?.includes("Network") ||
        err.message?.includes("fetch");
      if (isRetryable && attempt < retries) {
        await sleep(backoff(attempt));
        continue;
      }
      break;
    }
  }

  recordFailure(url);
  throw lastErr || new Error(`Request failed after ${retries} retries`);
}

async function retryFetch(
  url: string,
  init: RequestInit,
  retries = MAX_RETRIES,
): Promise<Response> {
  const body = init.body ? String(init.body) : "";
  const dedupeKey = getDedupeKey(init.method || "GET", url, body);

  const existing = inFlight.get(dedupeKey);
  if (existing) {
    const response = await existing;
    return response.clone();
  }

  const promise = resilientFetchInternal(url, init, retries);
  inFlight.set(dedupeKey, promise);

  try {
    const response = await promise;
    return response;
  } finally {
    setTimeout(() => inFlight.delete(dedupeKey), 100);
  }
}

export function getCircuitStatus(): { host: string; state: string; failures: number }[] {
  return Array.from(circuits.entries()).map(([host, state]) => ({
    host,
    state: state.state,
    failures: state.failures,
  }));
}

export function resetCircuits(): void {
  circuits.clear();
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
  const fetchOpts = {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  };

  let res = await retryFetch(url, fetchOpts);

  // On 401, attempt a single token refresh and retry the original request
  if (res.status === 401 && _refreshCallback) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      const retryHeaders = { ...headers, Authorization: `Bearer ${newToken}` };
      res = await retryFetch(url, { ...fetchOpts, headers: retryHeaders }, 0);
    }
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const e: any = new Error(err.detail ?? res.statusText);
    e.status = res.status;
    e.detail = err.detail;
    // On persistent 401 after refresh, signal the app to log out
    if (res.status === 401) {
      e.isAuthError = true;
    }
    throw e;
  }
  const text = await res.text();
  return text ? JSON.parse(text) : ({} as T);
}

export type HookArchetype = {
  name: string;
  description: string;
  usage_count: number;
  avg_retention: number;
};

export type SubscriptionTier = 'free' | 'basic' | 'pro' | 'enterprise';

export type Pipeline = Record<string, any>;

export type VideoSource = Record<string, any>;

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
  views?: number;
  likes?: number;
  shares?: number;
  comments?: number;
  watch_time_seconds?: number;
  retention_pct?: number;
  earnings_cents?: number;
  metrics_synced_at?: string;
  platform_metrics?: Record<string, any>;
  platform_posts?: Record<string, any>;
  musicTrackId?: string;
  musicDuckFactor?: number;
  platform?: string;
}

export const clipsApi = {
  getAll: (params?: Record<string, any>) => req('GET', '/clips', undefined, params),
  getById: (id: string) => req<{ data: Clip }>('GET', `/clips/${id}`).then((r) => ({ data: r as any })),
  approve: (id: string) => req('POST', `/clips/${id}/approve`),
  reject: (id: string) => req('POST', `/clips/${id}/reject`),
  delete: (id: string) => req('DELETE', `/clips/${id}`),
  downloadUrl: (id: string) => req<{ url: string }>('POST', `/clips/${id}/download-url`),
  remix: (id: string, opts: Record<string, any>) => req('POST', `/clips/${id}/remix`, opts),
  edit: (id: string, recipe: Record<string, any>) => req('POST', `/clips/${id}/edit`, recipe),
  previewMusic: (id: string, trackId: string, profile?: string, previewDuration?: number, duckFactor?: number) =>
    req<{ success: boolean; preview_url: string; job_id: string; duration: number; profile: string; duck_factor: number; expires_at: number }>(
      'POST', `/clips/${id}/preview-music`, undefined, { track_id: trackId, profile: profile || 'background', preview_duration: previewDuration, custom_duck_factor: duckFactor }
    ),
  getEditStatus: (id: string) => req('GET', `/clips/${id}/edit-status`),
  thumbnails: (id: string) => req<{ thumbnails: string[] }>('GET', `/clips/${id}/thumbnails`),
  runEditAgents: (id: string, opts?: Record<string, any>) => req('POST', `/swarm/edit`, { clip_id: id, ...opts }),
};

export const pipelinesApi = {
  getAll: () => req('GET', '/pipelines'),
  getById: (id: string) => req('GET', `/pipelines/${id}`),
  create: (data: Record<string, any>) => req('POST', '/pipelines', data),
  update: (id: string, data: Record<string, any>) => req('PATCH', `/pipelines/${id}`, data),
  delete: (id: string) => req('DELETE', `/pipelines/${id}`),
  toggle: (id: string) => req('POST', `/pipelines/${id}/toggle`),
};

export const sourcesApi = {
  getAll: () => req('GET', '/sources'),
  create: (data: Record<string, any>) => req('POST', '/sources', data),
  delete: (id: string) => req('DELETE', `/sources/${id}`),
};

export const earningsApi = {
  get: (params?: { start_date?: string; end_date?: string; platform?: string }) =>
    req('GET', '/earnings', undefined, params),
  getSummary: (period?: string) =>
    req<{ total_earnings: number; pending_earnings: number; total_clips_monetized: number; by_platform: Record<string, number> }>('GET', '/earnings/summary', undefined, period ? { period } : undefined),
  getDashboard: () => req('GET', '/earnings/dashboard'),
  requestWithdrawal: (amount: number, method: string) => req('POST', '/earnings/withdrawal', { amount, method }),
};

export const analyticsApi = {
  trackEvent: (event_type: string, event_data?: Record<string, any>) =>
    req('POST', '/analytics/events', { event_type, event_data }),
  getDashboard: () => req<{ total_clips: number; total_views: number; total_revenue: number; platform_breakdown: Record<string, number>; daily_stats: any[] }>('GET', '/analytics/dashboard'),
  getHookAnalysis: () => req<{ archetypes: any[]; insights: string[]; critic_card: string; total_clips_analyzed: number }>('GET', '/analytics/hooks'),
  getCaptionStyles: () => req<{ styles: Array<{ name: string; body: string; delta_pct: number; variant: string; sample_size: number }>; baseline_views: number; total_clips_analyzed: number }>('GET', '/analytics/caption-styles'),
  getPipelineAnalytics: (pipeline_id: string) => req('GET', `/analytics/pipeline/${pipeline_id}`),
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

export const subscriptionsApi = {
  getCurrent: () =>
    req<{ tier: string; status: string }>('GET', '/subscriptions/current'),
  createCheckoutSession: (tier: string) =>
    req<{ checkout_url: string }>('POST', '/subscriptions/checkout', { tier }),
  createCustomerPortal: () =>
    req<{ portal_url: string }>('POST', '/subscriptions/portal'),
  cancel: () =>
    req<{ success: boolean; message?: string }>('POST', '/subscriptions/cancel'),
};

export const musicApi = {
  getTracks: (filters?: { mood?: string; genre?: string; vibe?: string; source?: string; search?: string }) =>
    req<{ tracks: any[]; total: number; filters: Record<string, string[]>; sources: Record<string, string> }>('GET', '/clips/music/tracks', undefined, filters),
  getProfiles: () =>
    req<{ profiles: any[] }>('GET', '/clips/music/profiles'),
  uploadTrack: (formData: FormData) =>
    req<{ success: boolean; track: any; message: string }>('POST', '/clips/music/upload', formData),
  reloadCatalog: () =>
    req<{ success: boolean; total_tracks: number; filters: Record<string, string[]> }>('POST', '/clips/music/reload-catalog'),
};

export const workerApi = {
  start: () => req('POST', '/worker/start'),
  stop: () => req('POST', '/worker/stop'),
  status: () => req('GET', '/worker/status'),
};

export const usersApi = {
  login: (email: string, password: string) =>
    req<{ access_token: string; user: any }>('POST', '/auth/login', { email, password }),
  register: (email: string, password: string, full_name: string) =>
    req<{ access_token: string; user: any }>('POST', '/auth/register', { email, password, full_name }),
  getMe: () => req('GET', '/users/me'),
  updateMe: (data: Record<string, any>) => req('PATCH', '/users/me', data),
  getPreferences: () => req('GET', '/users/me/preferences'),
  updatePreferences: (data: Record<string, any>) => req('PATCH', '/users/me/preferences', data),
  getUsage: () => req<{ clips_used: number; clips_quota: number; resets_at: string; tier: string }>('GET', '/users/me/usage'),
  getBilling: () => req('GET', '/users/me/billing'),
  deleteAccount: () => req('DELETE', '/users/me'),
  exportData: () => req('GET', '/users/me/export'),
};

export const agentsApi = {
  // Discovery
  discover: (pipelineId: string, maxProposals?: number) =>
    req('POST', '/agents/discover', { pipeline_id: pipelineId, max_proposals: maxProposals ?? 5 }),
  getDiscoveryStatus: (pipelineId: string) =>
    req('GET', `/agents/discover/${pipelineId}/status`),
  
  // Sources
  getSources: (pipelineId: string) =>
    req('GET', `/agents/sources/${pipelineId}`),
  createSource: (data: Record<string, any>) =>
    req('POST', '/agents/sources', data),
  refreshSource: (sourceId: string) =>
    req('POST', `/agents/sources/${sourceId}/refresh`),
  deleteSource: (sourceId: string) =>
    req('DELETE', `/agents/sources/${sourceId}`),
  discoverSources: (topic: string, platform?: string, maxResults?: number) =>
    req('GET', `/agents/sources/discover/${encodeURIComponent(topic)}`, undefined, { platform: platform ?? 'youtube', max_results: maxResults ?? 5 }),
  
  // Proposals
  proposalAction: (clipId: string, action: 'approve' | 'reject' | 'edit', edits?: Record<string, any>) =>
    req('POST', '/agents/proposals/action', { clip_id: clipId, action, edits }),
  
  // Status
  getAgentStatus: () =>
    req('GET', '/agents/status'),
};


export const socialApi = {
  getAccounts: () => req('GET', '/social-accounts'),
  connect: (platform: string, redirect_uri?: string) => req<{ auth_url: string }>('POST', '/social-accounts/connect', { platform, redirect_uri: redirect_uri ?? 'mvc-app://callback' }),
  disconnect: (id: string) => req('DELETE', `/social-accounts/${id}`),
  startOAuth: (platform: string) => req('GET', `/social/oauth/${platform}`),
  connectManual: (platform: string, handle: string) => req('POST', '/social/connect-manual', { platform, handle }),
};

// Convenience alias for legacy imports

export const api = { users: usersApi, clips: clipsApi, pipelines: pipelinesApi, sources: sourcesApi, earnings: earningsApi, analytics: analyticsApi, swarm: swarmApi, subscriptions: subscriptionsApi, agents: agentsApi, worker: workerApi };

