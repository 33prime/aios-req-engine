'use client'

import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { User, Session } from '@supabase/supabase-js'
import { supabase, isSupabaseConfigured } from '@/lib/supabase'
import { setAccessToken, clearAuth } from '@/lib/api'
import { analytics } from '@/lib/analytics'
import { Loader } from 'lucide-react'

interface AuthContextType {
  user: User | null
  session: Session | null
  loading: boolean
  providerToken: string | null
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  session: null,
  loading: true,
  providerToken: null,
  signOut: async () => {},
})

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

// Paths that don't require authentication
const PUBLIC_PATHS = [
  '/auth',
  '/auth/login',
  '/auth/accept-invite',
  '/auth/verify',
  '/invite',
]

const isPublicPath = (path: string) => {
  return PUBLIC_PATHS.some(publicPath => path.startsWith(publicPath))
}

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)
  const [providerToken, setProviderToken] = useState<string | null>(null)
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    // If Supabase is not configured, redirect to login
    if (!isSupabaseConfigured() || !supabase) {
      console.warn('Supabase not configured')
      setLoading(false)
      return
    }

    // Store reference after null check for TypeScript
    const client = supabase

    // Get initial session
    const initAuth = async () => {
      try {
        const { data: { session: initialSession } } = await client.auth.getSession()

        if (initialSession) {
          setSession(initialSession)
          setUser(initialSession.user)
          setAccessToken(initialSession.access_token)
        } else {
          // Clear any stale tokens
          clearAuth()
        }
      } catch (error) {
        console.error('Error getting session:', error)
        clearAuth()
      } finally {
        setLoading(false)
      }
    }

    initAuth()

    // Listen for auth state changes
    const { data: { subscription } } = client.auth.onAuthStateChange(
      async (event, newSession) => {
        if (newSession) {
          setSession(newSession)
          setUser(newSession.user)
          setAccessToken(newSession.access_token)

          // Capture provider token (e.g., Google OAuth) for server-side persistence
          if (newSession.provider_token) {
            setProviderToken(newSession.provider_token)
            // Persist Google refresh token to backend for Calendar API access
            _persistProviderToken(newSession.provider_token, newSession.provider_refresh_token ?? null)
          }
        } else {
          setSession(null)
          setUser(null)
          setProviderToken(null)
          clearAuth()
        }

        // Handle specific events
        if (event === 'SIGNED_IN') {
          analytics.signedIn(newSession?.user?.app_metadata?.provider || 'email')
          // Only redirect to /projects if coming from auth pages
          // This prevents unwanted redirects on page refresh (session restoration also triggers SIGNED_IN)
          const currentPath = typeof window !== 'undefined' ? window.location.pathname : pathname
          if (currentPath.startsWith('/auth')) {
            router.push('/projects')
          }
        } else if (event === 'SIGNED_OUT') {
          router.push('/auth/login')
        }
      }
    )

    return () => {
      subscription.unsubscribe()
    }
  }, [router])

  // Redirect unauthenticated users to login
  useEffect(() => {
    if (!loading && !user && !isPublicPath(pathname)) {
      router.push('/auth/login')
    }
  }, [user, loading, pathname, router])

  // Persist provider token (Google refresh token) to backend
  const _persistProviderToken = async (providerToken: string, refreshToken: string | null) => {
    if (!refreshToken) return
    try {
      const { connectGoogle } = await import('@/lib/api')
      await connectGoogle(refreshToken, ['https://www.googleapis.com/auth/calendar.events'])
    } catch (err) {
      console.error('Failed to persist Google token:', err)
    }
  }

  const signOut = async () => {
    try {
      if (supabase) {
        await supabase.auth.signOut()
      }
    } catch (error) {
      console.error('Error signing out:', error)
    } finally {
      // Always clear local state
      setUser(null)
      setSession(null)
      clearAuth()
      router.push('/auth/login')
    }
  }

  // Show loading screen while checking auth
  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-50 flex items-center justify-center">
        <div className="flex items-center gap-2 text-zinc-500">
          <Loader className="w-5 h-5 animate-spin" />
          <span className="text-sm">Loading...</span>
        </div>
      </div>
    )
  }

  // If not authenticated and not on public path, show nothing (redirect is happening)
  if (!user && !isPublicPath(pathname)) {
    return (
      <div className="min-h-screen bg-zinc-50 flex items-center justify-center">
        <div className="flex items-center gap-2 text-zinc-500">
          <Loader className="w-5 h-5 animate-spin" />
          <span className="text-sm">Redirecting to login...</span>
        </div>
      </div>
    )
  }

  return (
    <AuthContext.Provider value={{ user, session, loading, providerToken, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}
