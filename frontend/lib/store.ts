import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { setApiToken } from './api';
import { clipsApi } from './api';

// ─── Auth store ───────────────────────────────────────────────────────────────

interface AuthState {
  token: string | null;
  user: { id: string; email: string; full_name?: string } | null;
  clips: any[];
  clipsLoading: boolean;
  pipelines: any[];

  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, fullName?: string) => Promise<void>;
  doSignOut: () => void;
  fetchClips: () => Promise<void>;
  approveClip: (id: string) => void;
  rejectClip: (id: string) => void;
  deleteClip: (id: string) => void;
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

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  user: null,
  clips: [],
  clipsLoading: false,
  pipelines: [],

  signIn: async (email, password) => {
    const data = await authPost('/auth/login', { email, password });
    const { access_token, user } = data;
    setApiToken(access_token);
    await AsyncStorage.setItem('auth_token', access_token);
    set({ token: access_token, user });
  },

  signUp: async (email, password, fullName) => {
    const data = await authPost('/auth/register', {
      email,
      password,
      full_name: fullName,
    });
    const { access_token, user } = data;
    setApiToken(access_token);
    await AsyncStorage.setItem('auth_token', access_token);
    set({ token: access_token, user });
  },

  doSignOut: () => {
    setApiToken(null);
    AsyncStorage.removeItem('auth_token').catch(() => null);
    set({ token: null, user: null, clips: [], pipelines: [] });
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
}));

// Restore persisted token on module load
AsyncStorage.getItem('auth_token')
  .then((token) => {
    if (token) {
      setApiToken(token);
      useAuthStore.setState({ token });
    }
  })
  .catch(() => null);

// ─── App store ────────────────────────────────────────────────────────────────

interface AppState {
  user: { id: string; email: string } | null;
}

export const useAppStore = create<AppState>(() => ({ user: null }));

useAuthStore.subscribe((s) => {
  useAppStore.setState({ user: s.user });
});
