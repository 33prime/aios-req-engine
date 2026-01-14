'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { Building2, CheckCircle, XCircle, Loader, Clock } from 'lucide-react'
import { getInvitationByToken, acceptInvitation, setCurrentOrganization } from '@/lib/api'
import type { InvitationWithOrg } from '@/types/api'

export default function InviteAcceptPage() {
  const params = useParams()
  const router = useRouter()
  const token = params.token as string

  const [invitation, setInvitation] = useState<InvitationWithOrg | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isAccepting, setIsAccepting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    loadInvitation()
  }, [token])

  const loadInvitation = async () => {
    try {
      const inv = await getInvitationByToken(token)
      setInvitation(inv)
    } catch (err: any) {
      const errorMessage = err.message || 'Failed to load invitation'
      try {
        const parsed = JSON.parse(errorMessage)
        if (parsed.detail?.includes('expired')) {
          setError('This invitation has expired.')
        } else {
          setError(parsed.detail || 'Invitation not found or has expired.')
        }
      } catch {
        setError('Invitation not found or has expired.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleAccept = async () => {
    setIsAccepting(true)
    setError(null)

    try {
      const result = await acceptInvitation(token)
      setSuccess(true)

      // Set the new org as current
      setCurrentOrganization(result.organization.id)
      localStorage.setItem('currentOrganizationId', result.organization.id)

      // Redirect after a short delay
      setTimeout(() => {
        router.push('/projects')
      }, 2000)
    } catch (err: any) {
      const errorMessage = err.message || 'Failed to accept invitation'
      try {
        const parsed = JSON.parse(errorMessage)
        setError(parsed.detail || errorMessage)
      } catch {
        setError(errorMessage)
      }
    } finally {
      setIsAccepting(false)
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-zinc-50 flex items-center justify-center">
        <div className="flex items-center gap-2 text-zinc-500">
          <Loader className="w-5 h-5 animate-spin" />
          <span className="text-[13px]">Loading invitation...</span>
        </div>
      </div>
    )
  }

  if (error && !invitation) {
    return (
      <div className="min-h-screen bg-zinc-50 flex items-center justify-center">
        <div className="bg-white rounded-xl shadow-sm border border-zinc-200 p-8 max-w-md w-full mx-4 text-center">
          <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center mx-auto mb-4">
            <XCircle className="w-6 h-6 text-red-600" />
          </div>
          <h1 className="text-[16px] font-semibold text-zinc-900 mb-2">
            Invalid Invitation
          </h1>
          <p className="text-[13px] text-zinc-600 mb-6">{error}</p>
          <button
            onClick={() => router.push('/projects')}
            className="px-4 py-2 bg-zinc-900 text-white rounded-lg hover:bg-zinc-800 transition-colors text-[13px] font-medium"
          >
            Go to Dashboard
          </button>
        </div>
      </div>
    )
  }

  if (success) {
    return (
      <div className="min-h-screen bg-zinc-50 flex items-center justify-center">
        <div className="bg-white rounded-xl shadow-sm border border-zinc-200 p-8 max-w-md w-full mx-4 text-center">
          <div className="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center mx-auto mb-4">
            <CheckCircle className="w-6 h-6 text-emerald-600" />
          </div>
          <h1 className="text-[16px] font-semibold text-zinc-900 mb-2">
            Welcome to {invitation?.organization_name}!
          </h1>
          <p className="text-[13px] text-zinc-600 mb-4">
            You&apos;ve successfully joined the organization.
          </p>
          <p className="text-[12px] text-zinc-500">
            Redirecting to dashboard...
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-zinc-50 flex items-center justify-center">
      <div className="bg-white rounded-xl shadow-sm border border-zinc-200 p-8 max-w-md w-full mx-4">
        <div className="text-center mb-6">
          <div className="w-16 h-16 rounded-full bg-emerald-600/10 flex items-center justify-center mx-auto mb-4">
            <Building2 className="w-8 h-8 text-emerald-600" />
          </div>
          <h1 className="text-[16px] font-semibold text-zinc-900 mb-2">
            You&apos;ve been invited to join
          </h1>
          <p className="text-[20px] font-bold text-zinc-900">
            {invitation?.organization_name}
          </p>
        </div>

        <div className="bg-zinc-50 rounded-lg p-4 mb-6 space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-[12px] text-zinc-500">Invited by</span>
            <span className="text-[13px] text-zinc-700 font-medium">
              {invitation?.invited_by_name || 'A team member'}
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-[12px] text-zinc-500">Your role</span>
            <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${
              invitation?.organization_role === 'Admin'
                ? 'bg-blue-100 text-blue-700'
                : 'bg-zinc-100 text-zinc-700'
            }`}>
              {invitation?.organization_role}
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-[12px] text-zinc-500">Expires</span>
            <span className="text-[13px] text-zinc-700 flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" />
              {invitation && new Date(invitation.expires_at).toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
              })}
            </span>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
            <p className="text-[12px] text-red-700">{error}</p>
          </div>
        )}

        <div className="flex gap-3">
          <button
            onClick={() => router.push('/projects')}
            disabled={isAccepting}
            className="flex-1 px-4 py-2.5 text-[13px] text-zinc-700 hover:bg-zinc-100 rounded-lg transition-colors border border-zinc-200"
          >
            Decline
          </button>
          <button
            onClick={handleAccept}
            disabled={isAccepting}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors text-[13px] font-medium disabled:opacity-50"
          >
            {isAccepting ? (
              <>
                <Loader className="w-4 h-4 animate-spin" />
                Joining...
              </>
            ) : (
              'Accept & Join'
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
