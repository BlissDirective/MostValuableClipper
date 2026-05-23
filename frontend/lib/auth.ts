import { supabase } from './supabase';
import { setApiToken } from './api';
const saveToken = (t: string) => setApiToken(t);
const clearToken = () => setApiToken(null);

export interface AuthUser {
  id: string;
  email: string;
  full_name?: string | null;
  avatar_url?: string | null;
}

export interface AuthSession {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

export interface AuthResult {
  user: AuthUser;
  session: AuthSession;
}

/**
 * Sign up with email and password via Supabase Auth.
 */
export async function signUp(email: string, password: string, fullName?: string): Promise<AuthResult> {
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      data: {
        full_name: fullName || '',
      },
    },
  });

  if (error) throw new Error(error.message);
  if (!data.session || !data.user) throw new Error('Registration failed — no session returned');

  await saveToken(data.session.access_token);

  return {
    user: {
      id: data.user.id,
      email: data.user.email!,
      full_name: data.user.user_metadata?.full_name,
    },
    session: {
      access_token: data.session.access_token,
      refresh_token: data.session.refresh_token,
      expires_in: data.session.expires_in,
    },
  };
}

/**
 * Sign in with email and password via Supabase Auth.
 */
export async function signIn(email: string, password: string): Promise<AuthResult> {
  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password,
  });

  if (error) throw new Error(error.message);
  if (!data.session || !data.user) throw new Error('Login failed — no session returned');

  await saveToken(data.session.access_token);

  return {
    user: {
      id: data.user.id,
      email: data.user.email!,
      full_name: data.user.user_metadata?.full_name,
    },
    session: {
      access_token: data.session.access_token,
      refresh_token: data.session.refresh_token,
      expires_in: data.session.expires_in,
    },
  };
}

/**
 * Update user password via Supabase Auth.
 */
export async function changePassword(newPassword: string): Promise<void> {
  const { error } = await supabase.auth.updateUser({
    password: newPassword,
  });
  if (error) throw new Error(error.message);
}

/**
 * Send password reset email via Supabase Auth.
 */
export async function resetPasswordEmail(email: string): Promise<void> {
  const { error } = await supabase.auth.resetPasswordForEmail(email, {
    redirectTo: typeof window !== 'undefined' ? window.location.origin + '/reset-password' : undefined,
  });
  if (error) throw new Error(error.message);
}

/**
 * Sign out current user.
 */
export async function signOut(): Promise<void> {
  await supabase.auth.signOut();
  await clearToken();
}

/**
 * Get current session (if any).
 */
export async function getCurrentSession() {
  const { data, error } = await supabase.auth.getSession();
  if (error) throw new Error(error.message);
  return data.session;
}

/**
 * Get current user (if authenticated).
 */
export async function getCurrentUser(): Promise<AuthUser | null> {
  const { data, error } = await supabase.auth.getUser();
  if (error || !data.user) return null;

  return {
    id: data.user.id,
    email: data.user.email!,
    full_name: data.user.user_metadata?.full_name,
    avatar_url: data.user.user_metadata?.avatar_url,
  };
}
