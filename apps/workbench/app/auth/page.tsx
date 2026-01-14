'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { supabase, isSupabaseConfigured } from '@/lib/supabase'

export default function AuthPage() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const router = useRouter()

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!isSupabaseConfigured() || !supabase) {
      setError('Authentication is not configured. Please contact support.')
      return
    }

    if (!email.trim()) {
      setError('Please enter your email address')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const redirectUrl = `${window.location.origin}/auth/verify`
      console.log('🔐 Sending magic link to:', email.trim())
      console.log('🔗 Redirect URL:', redirectUrl)

      const { data, error: authError } = await supabase.auth.signInWithOtp({
        email: email.trim(),
        options: {
          emailRedirectTo: redirectUrl,
        },
      })

      console.log('📧 Supabase response:', { data, error: authError })

      if (authError) {
        console.error('❌ Auth error:', authError)
        setError(authError.message)
      } else {
        console.log('✅ Magic link sent successfully')
        setSuccess(true)
      }
    } catch (err) {
      setError('An unexpected error occurred. Please try again.')
      console.error('Sign in error:', err)
    } finally {
      setLoading(false)
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
            Enter your email to receive a magic link
          </p>

          {success ? (
            <div className="text-center py-8">
              <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg
                  className="w-8 h-8 text-emerald-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                  />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-zinc-900 mb-2">
                Check your email
              </h3>
              <p className="text-zinc-500">
                We sent a sign-in link to <span className="font-medium text-zinc-700">{email}</span>
              </p>
              <button
                onClick={() => {
                  setSuccess(false)
                  setEmail('')
                }}
                className="mt-6 text-sm text-emerald-600 hover:text-emerald-700 font-medium"
              >
                Use a different email
              </button>
            </div>
          ) : (
            <form onSubmit={handleSignIn}>
              {error && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              )}

              <div className="mb-6">
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

              <button
                type="submit"
                disabled={loading || !email.trim()}
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
                    Sending link...
                  </span>
                ) : (
                  'Sign in'
                )}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
