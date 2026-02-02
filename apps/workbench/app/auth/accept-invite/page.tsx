'use client'

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { setAccessToken } from '@/lib/api'
import { API_BASE } from '@/lib/config'

interface InviteDetails {
  email: string
  platform_role: string
  first_name: string | null
  last_name: string | null
}

export default function AcceptInvitePage() {
  const [inviteDetails, setInviteDetails] = useState<InviteDetails | null>(null)
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()
  const searchParams = useSearchParams()
  const token = searchParams.get('token')

  useEffect(() => {
    if (!token) {
      setError('Invalid invitation link')
      setLoading(false)
      return
    }

    fetchInviteDetails()
  }, [token])

  const fetchInviteDetails = async () => {
    try {
      const response = await fetch(`${API_BASE}/v1/auth/invite/${token}`)
      const data = await response.json()

      if (!response.ok) {
        setError(data.detail || 'Invalid or expired invitation')
        return
      }

      setInviteDetails(data)
      setFirstName(data.first_name || '')
      setLastName(data.last_name || '')
    } catch (err) {
      setError('Failed to load invitation details')
      console.error('Error fetching invite:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }

    setSubmitting(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE}/v1/auth/accept-invite`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          invite_token: token,
          password,
          first_name: firstName || null,
          last_name: lastName || null,
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        setError(data.detail || 'Failed to create account')
        return
      }

      // Store the access token
      setAccessToken(data.access_token)

      // Store refresh token in localStorage for persistence
      if (data.refresh_token) {
        localStorage.setItem('refresh_token', data.refresh_token)
      }

      // Redirect to projects
      router.push('/projects')
    } catch (err) {
      setError('An unexpected error occurred. Please try again.')
      console.error('Accept invite error:', err)
    } finally {
      setSubmitting(false)
    }
  }

  const getRoleLabel = (role: string) => {
    switch (role) {
      case 'solution_architect':
        return 'Solution Architect'
      case 'sales_consultant':
        return 'Sales Consultant'
      default:
        return role
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600 mx-auto mb-4"></div>
          <p className="text-sm text-zinc-500">Loading invitation...</p>
        </div>
      </div>
    )
  }

  if (error && !inviteDetails) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-50 p-6">
        <div className="w-full max-w-md bg-white rounded-xl shadow-sm border border-zinc-200 p-8 text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg
              className="w-8 h-8 text-red-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-zinc-900 mb-2">
            Invalid Invitation
          </h2>
          <p className="text-zinc-500 mb-6">{error}</p>
          <Link
            href="/auth/login"
            className="inline-block px-4 py-2 bg-emerald-600 text-white rounded-lg font-medium hover:bg-emerald-700 transition-colors"
          >
            Go to Login
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex">
      {/* Left Hero Panel - Hidden on mobile */}
      <div className="hidden md:flex md:w-1/2 bg-gradient-to-br from-emerald-600 to-emerald-400 flex-col justify-center items-center p-12">
        <div className="max-w-md text-center">
          <h1 className="text-4xl font-bold text-white mb-4">
            Welcome to the Team!
          </h1>
          <p className="text-emerald-50 text-lg">
            Complete your account setup to start using the Consultant Workbench.
          </p>
        </div>
      </div>

      {/* Right Form Panel */}
      <div className="w-full md:w-1/2 flex items-center justify-center p-6 bg-zinc-50">
        <div className="w-full max-w-md bg-white rounded-xl shadow-sm border border-zinc-200 p-8">
          <h2 className="text-2xl font-semibold text-zinc-900 mb-2">
            Create Your Account
          </h2>
          <p className="text-zinc-500 mb-2">
            You&apos;ve been invited to join as a{' '}
            <span className="font-medium text-emerald-600">
              {getRoleLabel(inviteDetails?.platform_role || '')}
            </span>
          </p>
          <p className="text-sm text-zinc-400 mb-6">
            {inviteDetails?.email}
          </p>

          <form onSubmit={handleSubmit}>
            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label htmlFor="firstName" className="block text-sm font-medium text-zinc-700 mb-2">
                  First Name
                </label>
                <input
                  id="firstName"
                  type="text"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  placeholder="John"
                  className="w-full px-3 py-2 border border-zinc-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                  disabled={submitting}
                />
              </div>
              <div>
                <label htmlFor="lastName" className="block text-sm font-medium text-zinc-700 mb-2">
                  Last Name
                </label>
                <input
                  id="lastName"
                  type="text"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  placeholder="Doe"
                  className="w-full px-3 py-2 border border-zinc-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                  disabled={submitting}
                />
              </div>
            </div>

            <div className="mb-4">
              <label htmlFor="password" className="block text-sm font-medium text-zinc-700 mb-2">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 8 characters"
                className="w-full px-3 py-2 border border-zinc-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                disabled={submitting}
                autoComplete="new-password"
              />
            </div>

            <div className="mb-6">
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-zinc-700 mb-2">
                Confirm Password
              </label>
              <input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm your password"
                className="w-full px-3 py-2 border border-zinc-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                disabled={submitting}
                autoComplete="new-password"
              />
            </div>

            <button
              type="submit"
              disabled={submitting || !password || !confirmPassword}
              className="w-full bg-gradient-to-br from-emerald-600 to-emerald-400 text-white py-2.5 rounded-lg font-medium hover:from-emerald-700 hover:to-emerald-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submitting ? (
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
                  Creating account...
                </span>
              ) : (
                'Create Account'
              )}
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-zinc-200">
            <p className="text-sm text-zinc-500 text-center">
              Already have an account?{' '}
              <Link href="/auth/login" className="text-emerald-600 hover:text-emerald-700 font-medium">
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
