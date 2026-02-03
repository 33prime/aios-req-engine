'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { setAccessToken } from '@/lib/api'
import { API_BASE } from '@/lib/config'
import { supabase } from '@/lib/supabase'

const GOOGLE_CALENDAR_SCOPE = 'https://www.googleapis.com/auth/calendar.events'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [googleLoading, setGoogleLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!email.trim() || !password) {
      setError('Please enter your email and password')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE}/v1/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: email.trim(),
          password,
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        setError(data.detail || 'Login failed. Please check your credentials.')
        return
      }

      // Store the access token
      setAccessToken(data.access_token)

      // Store refresh token in localStorage for persistence
      if (data.refresh_token) {
        localStorage.setItem('refresh_token', data.refresh_token)
      }

      // Set Supabase session so AuthProvider recognizes we're logged in
      if (supabase && data.access_token && data.refresh_token) {
        await supabase.auth.setSession({
          access_token: data.access_token,
          refresh_token: data.refresh_token,
        })
      }

      // Redirect to projects
      router.push('/projects')
    } catch (err) {
      setError('An unexpected error occurred. Please try again.')
      console.error('Login error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleGoogleSignIn = async () => {
    if (!supabase) {
      setError('Authentication service not configured')
      return
    }

    setGoogleLoading(true)
    setError(null)

    try {
      const { error: oauthError } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          scopes: GOOGLE_CALENDAR_SCOPE,
          redirectTo: `${window.location.origin}/projects`,
        },
      })

      if (oauthError) {
        setError(oauthError.message || 'Google sign-in failed')
      }
    } catch (err) {
      setError('An unexpected error occurred with Google sign-in')
      console.error('Google sign-in error:', err)
    } finally {
      setGoogleLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Left Hero Panel - Hidden on mobile */}
      <div className="hidden md:flex md:w-1/2 bg-gradient-to-br from-emerald-600 to-emerald-400 flex-col justify-center items-center p-12">
        <div className="max-w-md text-center">
          <h1 className="text-4xl font-bold text-white mb-4">
            Consultant Workbench
          </h1>
          <p className="text-emerald-50 text-lg">
            Streamline your discovery process with AI-powered requirements gathering and analysis.
          </p>
        </div>
      </div>

      {/* Right Form Panel */}
      <div className="w-full md:w-1/2 flex items-center justify-center p-6 bg-zinc-50">
        <div className="w-full max-w-md bg-white rounded-xl shadow-sm border border-zinc-200 p-8">
          {/* Logo/Title for mobile */}
          <div className="md:hidden mb-8 text-center">
            <h1 className="text-2xl font-bold text-zinc-900">
              Consultant Workbench
            </h1>
          </div>

          <h2 className="text-2xl font-semibold text-zinc-900 mb-2">
            Sign in
          </h2>
          <p className="text-zinc-500 mb-8">
            Enter your credentials to access your account
          </p>

          <form onSubmit={handleLogin}>
            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}

            <div className="mb-4">
              <label htmlFor="email" className="block text-sm font-medium text-zinc-700 mb-2">
                Email address
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full px-3 py-2 border border-zinc-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                disabled={loading}
                autoComplete="email"
                autoFocus
              />
            </div>

            <div className="mb-6">
              <label htmlFor="password" className="block text-sm font-medium text-zinc-700 mb-2">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                className="w-full px-3 py-2 border border-zinc-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                disabled={loading}
                autoComplete="current-password"
              />
            </div>

            <button
              type="submit"
              disabled={loading || !email.trim() || !password}
              className="w-full bg-gradient-to-br from-emerald-600 to-emerald-400 text-white py-2.5 rounded-lg font-medium hover:from-emerald-700 hover:to-emerald-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <span className="flex items-center justify-center">
                  <svg
                    className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  Signing in...
                </span>
              ) : (
                'Sign in'
              )}
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-zinc-200">
            <p className="text-sm text-zinc-500 text-center mb-4">or</p>
            <button
              type="button"
              onClick={handleGoogleSignIn}
              disabled={googleLoading || loading}
              className="w-full flex items-center justify-center gap-3 bg-white border border-zinc-300 text-zinc-700 py-2.5 rounded-lg font-medium hover:bg-zinc-50 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {googleLoading ? (
                <span className="flex items-center justify-center">
                  <svg
                    className="animate-spin -ml-1 mr-2 h-4 w-4 text-zinc-500"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  Connecting...
                </span>
              ) : (
                <>
                  <svg className="w-5 h-5" viewBox="0 0 24 24">
                    <path
                      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
                      fill="#4285F4"
                    />
                    <path
                      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                      fill="#34A853"
                    />
                    <path
                      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                      fill="#FBBC05"
                    />
                    <path
                      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                      fill="#EA4335"
                    />
                  </svg>
                  Continue with Google
                </>
              )}
            </button>
          </div>

          <div className="mt-4 pt-4 border-t border-zinc-200">
            <p className="text-sm text-zinc-500 text-center">
              Are you a client?{' '}
              <Link href="/auth" className="text-emerald-600 hover:text-emerald-700 font-medium">
                Sign in with magic link
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
