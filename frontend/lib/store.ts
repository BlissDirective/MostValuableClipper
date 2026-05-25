import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SecureStore from 'expo-secure-store';
import { Platform, Linking } from 'react-native';
import { setApiToken, setRefreshCallback } from './api';
import { clipsApi, pipelinesApi, earningsApi } from './api';
import { mapBackendToPipeline } from './mappers';

// SecureStore is unavailable on web; fall back to AsyncStorage there.
const secureSet = async (key: string, value: string) => {
  if (Platform.OS === 'web') return AsyncStorage.setItem(key, value);
  return SecureStore.setItemAsync(key, value);
};
const secureGet = async (key: string): Promise<string | null> => {
  if (Platform.OS === 'web') return AsyncStorage.getItem(key);
  return SecureStore.getItemAsync(key);
};
const secureDelete = async (key: string) => {
  if (Platform.OS === 'web') return AsyncStorage.removeItem(key);
  return SecureStore.deleteItemAsync(key);
};

export type PlatformKey = 'tiktok' | 'instagram' | 'youtube';

export type PipelineStatus = 'running' | 'paused' | 'errored' | 'setup-incomplete';
export type AutonomyMode = 'fullAuto' | 'approveEach' | 'suggestOnly';
export type RetentionPolicy = 'minimal' | 'moderate' | 'maximum' | 'aggressive' | 'indefinite';
export const DEFAULT_WARNING_CATEGORIES: Record<WarningCategoryKey, boolean> = {
  newsPolitical: false,
  health: false,
  finance: false,
  children: false,
  identifiableIndividual: false,
  violentGraphic: false,
};

export type WarningCategoryKey = 'newsPolitical' | 'health' | 'finance' | 'children' | 'identifiableIndividual' | 'violentGraphic';

export interface PipelineSource {
  id: string;
  kind: 'upload' | 'creator-licensed' | 'cc-archive';
  name: string;
  status: 'ingested' | 'pending' | 'failed';
  sourceType?: string;
  sourceUrl?: string;
}

export interface Pipeline {
  id: string;
  themeName: string;
  niche: string;
  status: PipelineStatus;
  clipsThisWeek: number;
  viewDelta: string;
  deltaVariant: 'positive' | 'negative' | 'default';
  clipsPerDay: number;
  platforms: PlatformKey[];
  autonomy: AutonomyMode;
  resolverOn: boolean;
  retention: RetentionPolicy;
  warningCategories: Record<WarningCategoryKey, boolean>;
  sources: PipelineSource[];
  sourcePlan: { uploads: boolean; creatorLicensed: boolean; ccArchive: boolean };
}

interface SocialAccount {
  platform: PlatformKey;
  handle?: string;
  connected: boolean;
}

interface EarningsSummary {
  total_earnings: number;
  pending_earnings: number;
  total_clips_monetized: number;
  by_platform: Record<string, number>;
}

export type SubscriptionTier = 'free' | 'basic' | 'pro' | 'premium' | 'enterprise';

export interface SubscriptionData {
  tier: SubscriptionTier;
  status: string;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  trial_end: string | null;
}

// ─── Auth store ───────────────────────────────────────────────────────────────

interface AuthState {
  token: string | null;
  user: { id: string; email: string; full_name?: string } | null;
  clips: any[];
  clipsLoading: boolean;
  pipelines: Pipeline[];
  pipelinesLoading: boolean;

  // Subscription + social
  subscriptionTier: string;
  subscription: SubscriptionData;
  socialAccounts: SocialAccount[];
  draft: { connected: Record<PlatformKey, boolean>; cohortOptIn?: boolean; autonomy?: AutonomyMode; theme?: string; warningCategories?: Record<WarningCategoryKey, boolean> };

  // Earnings
  earningsSummary: EarningsSummary | null;

  // Auth status
  isAuthenticated: boolean;
  hasOnboarded: boolean;
  isLoading: boolean;

  checkSession: () => Promise<void>;

  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, fullName?: string) => Promise<void>;
  doSignOut: () => void;
  fetchClips: () => Promise<void>;
  approveClip: (id: string) => void;
  rejectClip: (id: string) => void;
  deleteClip: (id: string) => void;

  // Pipelines
  fetchPipelines: () => Promise<void>;
  updatePipeline: (id: string, patch: Partial<Pipeline>) => Promise<void>;
  removePipeline: (id: string) => Promise<void>;

  // Subscription
  fetchSubscription: () => Promise<SubscriptionData>;
  createCheckoutSession: (tierName: string) => Promise<{ checkout_url: string }>;
  cancelSubscription: () => Promise<void>;

  // Social accounts
  fetchSocialAccounts: () => Promise<void>;
  togglePlatform: (platform: PlatformKey) => Promise<void>;
  startOAuth: (platform: PlatformKey) => Promise<{ auth_url: string }>;
  connectPlatform: (platform: PlatformKey, handle: string) => Promise<void>;
  disconnectPlatform: (platform: PlatformKey) => Promise<void>;

  // Earnings
  fetchEarnings: () => Promise<void>;

  // Sources
  fetchSources: () => Promise<void>;
  addSource: (pipelineId: string, source: Omit<PipelineSource, 'id'>) => Promise<void>;
  removeSource: (pipelineId: string, sourceId: string) => Promise<void>;

  // Onboarding
  finishOnboarding: () => Promise<void>;
  setTheme: (theme: string) => void;
  setCohortOptIn: (optIn: boolean) => void;
  setAutonomy: (mode: AutonomyMode) => void;
  setWarningCategories: (cats: Record<WarningCategoryKey, boolean>) => void;

  // Pipeline creation
  addPipeline: (pipeline: Omit<Pipeline, 'id' | 'clipsThisWeek' | 'viewDelta' | 'deltaVariant' | 'sources'>) => Promise<void>;
}

const BASE = (
  process.env.EXPO_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1'
).replace(/\/$/, '');

async function authPost(path: string, body: unknown, token?: string | null) {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(BASE + path, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? res.statusText);
  }
  return res.json();
}

async function authGet(path: string, token?: string | null) {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(BASE + path, {
    method: 'GET',
    headers,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? res.statusText);
  }
  return res.json();
}

async function authDelete(path: string, token?: string | null) {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(BASE + path, {
    method: 'DELETE',
    headers,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? res.statusText);
  }
  return res.json();
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: null,
  user: null,
  isAuthenticated: false,
  hasOnboarded: false,
  isLoading: true,
  clips: [],
  clipsLoading: false,
  pipelines: [],
  pipelinesLoading: false,
  subscriptionTier: 'free',
  subscription: {
    tier: 'free',
    status: 'active',
    current_period_end: null,
    cancel_at_period_end: false,
    trial_end: null,
  },
  socialAccounts: [],
  draft: { connected: { tiktok: false, instagram: false, youtube: false }, cohortOptIn: false, autonomy: 'suggestOnly', theme: 'system' },
  earningsSummary: null,

  checkSession: async () => {
    try {
      const token = await secureGet('auth_token');
      const hasOnboarded = (await AsyncStorage.getItem('has_onboarded')) === 'true';
      if (token) {
        setApiToken(token);
        // Wire up refresh callback so the API client can refresh the session
        setRefreshCallback(async () => {
          const refresh = await secureGet('refresh_token');
          return refresh;
        });
        set({ token, isAuthenticated: true, hasOnboarded, isLoading: false });
      } else {
        set({ isAuthenticated: false, hasOnboarded, isLoading: false });
      }
    } catch {
      set({ isAuthenticated: false, isLoading: false });
    }
  },

  signIn: async (email, password) => {
    const data = await authPost('/auth/login', { email, password });
    const { access_token, refresh_token, user } = data;
    setApiToken(access_token);
    await secureSet('auth_token', access_token);
    if (refresh_token) await secureSet('refresh_token', refresh_token);
    setRefreshCallback(async () => secureGet('refresh_token'));
    set({ token: access_token, user, isAuthenticated: true });
  },

  signUp: async (email, password, fullName) => {
    const data = await authPost('/auth/register', {
      email,
      password,
      full_name: fullName,
    });
    const { access_token, refresh_token, user } = data;
    setApiToken(access_token);
    await secureSet('auth_token', access_token);
    if (refresh_token) await secureSet('refresh_token', refresh_token);
    setRefreshCallback(async () => secureGet('refresh_token'));
    set({ token: access_token, user, isAuthenticated: true, hasOnboarded: false });
  },

  doSignOut: () => {
    setApiToken(null);
    secureDelete('auth_token').catch(() => null);
    secureDelete('refresh_token').catch(() => null);
    set({
      token: null,
      user: null,
      isAuthenticated: false,
      hasOnboarded: false,
      clips: [],
      pipelines: [],
      pipelinesLoading: false,
      subscriptionTier: 'free',
      subscription: {
        tier: 'free',
        status: 'active',
        current_period_end: null,
        cancel_at_period_end: false,
        trial_end: null,
      },
      socialAccounts: [],
      draft: { connected: { tiktok: false, instagram: false, youtube: false }, cohortOptIn: false, autonomy: 'suggestOnly', theme: 'system' },
      earningsSummary: null,
    });
  },

  fetchClips: async () => {
    set({ clipsLoading: true });
    try {
      const raw: any = await clipsApi.getAll();
      const list: any[] = raw?.clips ?? raw ?? [];
      const clips = list.map((c: any) => ({
        id: c.id,
        sourceName: c.title ?? 'Untitled',
        caption: c.caption ?? '',
        platforms: [],
        state:
          c.status === 'approved'
            ? 'posted'
            : c.status === 'ready_for_review'
            ? 'queued'
            : c.status ?? 'queued',
        safety: c.safety_flags?.length
          ? { variant: 'warn' as const, categories: c.safety_flags }
          : null,
      }));
      set({ clips });
    } catch {
      // silently fail — stale data is fine
    } finally {
      set({ clipsLoading: false });
    }
  },

  approveClip: (id) => {
    clipsApi.approve(id).catch(() => null);
    set((s) => ({
      clips: s.clips.map((c) => (c.id === id ? { ...c, state: 'posted' } : c)),
    }));
  },

  rejectClip: (id) => {
    clipsApi.reject(id).catch(() => null);
    set((s) => ({ clips: s.clips.filter((c) => c.id !== id) }));
  },

  deleteClip: (id) => {
    clipsApi.delete(id).catch(() => null);
    set((s) => ({ clips: s.clips.filter((c) => c.id !== id) }));
  },

  fetchPipelines: async () => {
    set({ pipelinesLoading: true });
    try {
      const raw: any = await pipelinesApi.getAll();
      const list: any[] = raw?.pipelines ?? raw ?? [];
      const pipelines = list.map(mapBackendToPipeline);
      set({ pipelines });
    } catch {
      // silently fail
    } finally {
      set({ pipelinesLoading: false });
    }
  },

  updatePipeline: async (id, patch) => {
    try {
      await pipelinesApi.update?.(id, patch);
    } catch {
      // silently fail
    }
    set((s) => ({
      pipelines: s.pipelines.map((p) =>
        p.id === id ? { ...p, ...patch } : p
      ),
    }));
  },

  removePipeline: async (id) => {
    try {
      await pipelinesApi.delete?.(id);
    } catch {
      // silently fail
    }
    set((s) => ({ pipelines: s.pipelines.filter((p) => p.id !== id) }));
  },

  fetchSubscription: async () => {
    try {
      const token = get().token;
      const data = await authGet('/users/me/subscription', token);
      const sub: SubscriptionData = {
        tier: data.tier ?? 'free',
        status: data.status ?? 'active',
        current_period_end: data.current_period_end ?? null,
        cancel_at_period_end: data.cancel_at_period_end ?? false,
        trial_end: data.trial_end ?? null,
      };
      set({ subscriptionTier: sub.tier, subscription: sub });
      return sub;
    } catch {
      const fallback: SubscriptionData = { tier: 'free', status: 'active', current_period_end: null, cancel_at_period_end: false, trial_end: null };
      set({ subscriptionTier: 'free', subscription: fallback });
      return fallback;
    }
  },

  createCheckoutSession: async (tierName: string) => {
    // placeholder – wire to paymentsApi when backend endpoint is ready
    return { checkout_url: `https://checkout.stripe.com/pay?prefilled_email=${encodeURIComponent(get().user?.email ?? '')}&tier=${encodeURIComponent(tierName)}` };
  },

  cancelSubscription: async () => {
    // placeholder – wire to paymentsApi when backend endpoint is ready
    set({ subscriptionTier: 'free', subscription: { tier: 'free', status: 'cancelled', current_period_end: null, cancel_at_period_end: false, trial_end: null } });
  },

  fetchSocialAccounts: async () => {
    try {
      const token = get().token;
      const data = await authGet('/social/accounts', token);
      const accounts: SocialAccount[] = (data.accounts ?? []).map((a: any) => ({
        platform: a.platform as PlatformKey,
        handle: a.handle,
        connected: a.connected === true || a.status === 'active',
      }));
      const connected: Record<PlatformKey, boolean> = {
        tiktok: false,
        instagram: false,
        youtube: false,
      };
      for (const a of accounts) {
        if (connected[a.platform] !== undefined) {
          connected[a.platform] = a.connected;
        }
      }
      set({ socialAccounts: accounts, draft: { connected } });
    } catch {
      // silently fail
    }
  },

  togglePlatform: async (platform) => {
    const state = get();
    const isConnected = state.draft.connected[platform];
    if (isConnected) {
      await get().disconnectPlatform(platform);
    } else {
      // Start OAuth flow
      try {
        await get().startOAuth(platform);
      } catch (err: any) {
        console.error('[store] startOAuth failed:', err.message);
        throw err;
      }
    }
  },

  startOAuth: async (platform) => {
    try {
      const token = get().token;
      const data = await authGet(`/social/oauth/${platform}`, token);
      const authUrl = data.auth_url;
      if (!authUrl) {
        throw new Error('No auth URL returned from server');
      }
      // Open OAuth URL in system browser
      const supported = await Linking.canOpenURL(authUrl);
      if (supported) {
        await Linking.openURL(authUrl);
      } else {
        throw new Error('Cannot open OAuth URL');
      }
      return { auth_url: authUrl };
    } catch (err: any) {
      console.error('[store] startOAuth failed:', err.message);
      throw err;
    }
  },

  connectPlatform: async (platform, handle) => {
    try {
      const token = get().token;
      await authPost('/social/connect-manual', { platform, handle }, token);
      await get().fetchSocialAccounts();
    } catch (err: any) {
      console.error('[store] connectPlatform failed:', err.message);
      throw err;
    }
  },

  disconnectPlatform: async (platform) => {
    try {
      const token = get().token;
      await authDelete(`/social/${platform}`, token);
      await get().fetchSocialAccounts();
    } catch (err: any) {
      console.error('[store] disconnectPlatform failed:', err.message);
      throw err;
    }
  },

  finishOnboarding: async () => {
    await AsyncStorage.setItem('has_onboarded', 'true');
    set({ hasOnboarded: true });
  },
  setTheme: (theme) => set((s) => ({ draft: { ...s.draft, theme } })),
  setCohortOptIn: (optIn) => set((s) => ({ draft: { ...s.draft, cohortOptIn: optIn } })),
  setAutonomy: (mode) => set((s) => ({ draft: { ...s.draft, autonomy: mode } })),
  setWarningCategories: (cats) => set((s) => ({ draft: { ...s.draft, warningCategories: cats } })),

  fetchSources: async () => {},
  addSource: async (_pipelineId: string, _source: Omit<PipelineSource, 'id'>) => {},
  removeSource: async (_pipelineId: string, _sourceId: string) => {},
  addPipeline: async () => {},

  fetchEarnings: async () => {
    try {
      const data = await earningsApi.getSummary();
      set({ earningsSummary: data });
    } catch {
      // silently fail
    }
  },
}));

// Restore persisted token on module load (uses SecureStore / AsyncStorage on web)
secureGet('auth_token')
  .then((token) => {
    if (token) {
      setApiToken(token);
      setRefreshCallback(async () => secureGet('refresh_token'));
      useAuthStore.setState({ token, isAuthenticated: true, isLoading: false });
    } else {
      useAuthStore.setState({ isAuthenticated: false, isLoading: false });
    }
  })
  .catch(() => {
    useAuthStore.setState({ isAuthenticated: false, isLoading: false });
  });

// ─── App store ────────────────────────────────────────────────────────────────

interface AppState {
  user: { id: string; email: string } | null;
}

export const useAppStore = create<AppState>(() => ({ user: null }));
