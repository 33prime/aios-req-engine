'use client'

import { useState } from 'react'
import { UserPlus, Mail, X, Loader, CheckCircle, AlertCircle } from 'lucide-react'
import { sendInvitation } from '@/lib/api'
import type { OrganizationRole } from '@/types/api'

interface InviteMemberModalProps {
  organizationId: string
  organizationName: string
  isOpen: boolean
  onClose: () => void
  onSuccess?: () => void
}

export default function InviteMemberModal({
  organizationId,
  organizationName,
  isOpen,
  onClose,
  onSuccess,
}: InviteMemberModalProps) {
  const [email, setEmail] = useState('')
  const [role, setRole] = useState<OrganizationRole>('Member')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim()) return

    setIsLoading(true)
    setError(null)

    try {
      await sendInvitation(organizationId, {
        email: email.trim(),
        organization_role: role,
      })
      setSuccess(true)
      setTimeout(() => {
        onSuccess?.()
        handleClose()
      }, 1500)
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to send invitation'
      try {
        const parsed = JSON.parse(errorMessage)
        setError(parsed.detail || errorMessage)
      } catch {
        setError(errorMessage)
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleClose = () => {
    setEmail('')
    setRole('Member')
    setError(null)
    setSuccess(false)
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between p-4 border-b border-zinc-200">
          <div className="flex items-center gap-3">
            <div className="p-1.5 rounded-full bg-emerald-600/10 text-emerald-600">
              <UserPlus className="w-4 h-4" />
            </div>
            <h2 className="text-[14px] font-semibold text-zinc-900">Invite Team Member</h2>
          </div>
          <button
            onClick={handleClose}
            className="p-1 hover:bg-zinc-100 rounded-lg transition-colors text-zinc-500"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {success ? (
          <div className="p-8 text-center">
            <div className="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center mx-auto mb-4">
              <CheckCircle className="w-6 h-6 text-emerald-600" />
            </div>
            <h3 className="text-[14px] font-semibold text-zinc-900 mb-2">
              Invitation Sent!
            </h3>
            <p className="text-[13px] text-zinc-600">
              We&apos;ve sent an invitation to <span className="font-medium">{email}</span>
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-4 space-y-4">
            <div>
              <label className="text-[12px] text-zinc-600 block mb-1">
                Email Address
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full text-[13px] text-zinc-700 border border-zinc-300 rounded-md pl-10 pr-3 py-2 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                  placeholder="colleague@company.com"
                  required
                />
              </div>
            </div>

            <div>
              <label className="text-[12px] text-zinc-600 block mb-1">
                Role
              </label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value as OrganizationRole)}
                className="w-full text-[13px] text-zinc-700 border border-zinc-300 rounded-md px-3 py-2 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              >
                <option value="Member">Member - Can view organization and projects</option>
                <option value="Admin">Admin - Can manage members and settings</option>
              </select>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
              <div className="flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-brand-primary flex-shrink-0 mt-0.5" />
                <p className="text-[12px] text-brand-primary-hover">
                  They&apos;ll receive an email invitation to join <span className="font-medium">{organizationName}</span>.
                  The invitation expires in 7 days.
                </p>
              </div>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                <p className="text-[12px] text-red-700">{error}</p>
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={handleClose}
                disabled={isLoading}
                className="px-4 py-2 text-[13px] text-zinc-700 hover:bg-zinc-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isLoading || !email.trim()}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors text-[13px] font-medium disabled:opacity-50"
              >
                {isLoading ? (
                  <>
                    <Loader className="w-4 h-4 animate-spin" />
                    Sending...
                  </>
                ) : (
                  <>
                    <Mail className="w-4 h-4" />
                    Send Invitation
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
