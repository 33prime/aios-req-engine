'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { supabase } from '@/lib/supabase';
import api from '@/lib/api';
import type { User } from '@/types';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  signOut: () => Promise<void>;
  refreshUser: () => Promise<void>;
  devMode: boolean;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  signOut: async () => {},
  refreshUser: async () => {},
  devMode: false,
});

export function useAuth() {
  return useContext(AuthContext);
}

const PUBLIC_PATHS = ['/auth', '/auth/verify'];

// Dev mode user for testing without Supabase auth
const DEV_USER: User = {
  id: 'dev-user-001',
  email: 'dev@example.com',
  user_type: 'client',
  first_name: 'Dev',
  last_name: 'User',
  company_name: 'Dev Company',
  has_seen_welcome: true,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  const isPublicPath = PUBLIC_PATHS.some((path) => pathname?.startsWith(path));
  const devMode = !supabase;

  useEffect(() => {
    const initAuth = async () => {
      // If no Supabase client, use dev mode
      if (!supabase) {
        console.warn('Running in dev mode without Supabase auth');
        setUser(DEV_USER);
        setLoading(false);
        return;
      }

      try {
        const { data: { session } } = await supabase.auth.getSession();

        if (session?.access_token) {
          api.setAccessToken(session.access_token);
          const userData = await api.getCurrentUser() as { user: User };
          setUser(userData.user);
        }
      } catch (error) {
        console.error('Auth init error:', error);
      } finally {
        setLoading(false);
      }
    };

    initAuth();

    // Listen for auth changes (only if supabase is available)
    if (!supabase) return;

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        if (event === 'SIGNED_IN' && session?.access_token) {
          api.setAccessToken(session.access_token);
          try {
            const userData = await api.getCurrentUser() as { user: User };
            setUser(userData.user);
          } catch (error) {
            console.error('Error fetching user:', error);
          }
        } else if (event === 'SIGNED_OUT') {
          api.setAccessToken(null);
          setUser(null);
        }
      }
    );

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  // Redirect unauthenticated users to login (skip in dev mode)
  useEffect(() => {
    if (!loading && !user && !isPublicPath && !devMode) {
      router.push('/auth');
    }
  }, [loading, user, isPublicPath, router, devMode]);

  const signOut = async () => {
    if (supabase) {
      await supabase.auth.signOut();
    }
    api.setAccessToken(null);
    setUser(null);
    if (!devMode) {
      router.push('/auth');
    }
  };

  const refreshUser = async () => {
    if (devMode) {
      setUser(DEV_USER);
      return;
    }
    try {
      const userData = await api.getCurrentUser() as { user: User };
      setUser(userData.user);
    } catch (error) {
      console.error('Error refreshing user:', error);
    }
  };

  // Show loading state
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="spinner" />
      </div>
    );
  }

  // Show children for public paths even without auth
  if (isPublicPath) {
    return (
      <AuthContext.Provider value={{ user, loading, signOut, refreshUser, devMode }}>
        {children}
      </AuthContext.Provider>
    );
  }

  // In dev mode, always show children
  if (devMode) {
    return (
      <AuthContext.Provider value={{ user: DEV_USER, loading, signOut, refreshUser, devMode }}>
        {/* Dev mode banner */}
        <div className="bg-amber-100 border-b border-amber-200 px-4 py-2 text-center text-sm text-amber-800">
          Dev Mode - Supabase auth not configured. Using mock user.
        </div>
        {children}
      </AuthContext.Provider>
    );
  }

  // Block render until we have a user for protected paths
  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{ user, loading, signOut, refreshUser, devMode }}>
      {children}
    </AuthContext.Provider>
  );
}
