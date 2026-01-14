'use client'

import { useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { supabase, isSupabaseConfigured } from '@/lib/supabase'

export default function AuthVerifyPage() {
  const [error, setError] = useState<string | null>(null)
  const [verifying, setVerifying] = useState(true)
  const router = useRouter()
  const searchParams = useSearchParams()

  useEffect(() => {
    const verifyToken = async () => {
      if (!isSupabaseConfigured() || !supabase) {
        setError('Authentication is not configured.')
        setVerifying(false)
        return
      }

      try {
        // Get token from URL params
        const tokenHash = searchParams.get('token_hash')
        const type = searchParams.get('type') as 'magiclink' | 'email' | null

        if (!tokenHash || !type) {
          // Check for error in URL params
          const errorDescription = searchParams.get('error_description')
          if (errorDescription) {
            setError(errorDescription)
          } else {
            setError('Invalid verification link. Please request a new one.')
          }
          setVerifying(false)
          return
        }

        // Verify the OTP token
        const { error: verifyError } = await supabase.auth.verifyOtp({
          token_hash: tokenHash,
          type: type === 'magiclink' ? 'magiclink' : 'email',
        })

        if (verifyError) {
          setError(verifyError.message)
          setVerifying(false)
          return
        }

        // Verification successful - the auth state change listener will handle redirect
        // But we can also redirect here as a backup
        setTimeout(() => {
          router.push('/projects')
        }, 500)
      } catch (err) {
        console.error('Verification error:', err)
        setError('An unexpected error occurred during verification.')
        setVerifying(false)
      }
    }

    verifyToken()
  }, [router, searchParams])

  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-50 p-6">
      <div className="w-full max-w-md bg-white rounded-xl shadow-sm border border-zinc-200 p-8 text-center">
        {verifying && !error ? (
          <>
            <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg
                className="animate-spin h-8 w-8 text-emerald-600"
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
            </div>
            <h2 className="text-xl font-semibold text-zinc-900 mb-2">
              Verifying your sign in...
            </h2>
            <p className="text-zinc-500">
              Please wait while we verify your credentials.
            </p>
          </>
        ) : error ? (
          <>
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
              Verification failed
            </h2>
            <p className="text-zinc-500 mb-6">{error}</p>
            <button
              onClick={() => router.push('/auth')}
              className="bg-gradient-to-br from-emerald-600 to-emerald-400 text-white px-6 py-2.5 rounded-lg font-medium hover:from-emerald-700 hover:to-emerald-500 transition-all"
            >
              Back to sign in
            </button>
          </>
        ) : (
          <>
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
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-zinc-900 mb-2">
              Success!
            </h2>
            <p className="text-zinc-500">
              Redirecting you to your dashboard...
            </p>
          </>
        )}
      </div>
    </div>
  )
}
