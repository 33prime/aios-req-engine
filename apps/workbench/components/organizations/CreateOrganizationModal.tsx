'use client'

import { useState } from 'react'
import { Building2, X, Loader, CheckCircle } from 'lucide-react'
import { createOrganization } from '@/lib/api'
import type { Organization } from '@/types/api'

interface CreateOrganizationModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess?: (org: Organization) => void
}

export default function CreateOrganizationModal({
  isOpen,
  onClose,
  onSuccess,
}: CreateOrganizationModalProps) {
  const [name, setName] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return

    setIsLoading(true)
    setError(null)

    try {
      const org = await createOrganization({ name: name.trim() })
      setSuccess(true)
      setTimeout(() => {
        onSuccess?.(org)
        handleClose()
      }, 1000)
    } catch (err: any) {
      const errorMessage = err.message || 'Failed to create organization'
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
    setName('')
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
              <Building2 className="w-4 h-4" />
            </div>
            <h2 className="text-[14px] font-semibold text-zinc-900">Create Organization</h2>
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
              Organization Created!
            </h3>
            <p className="text-[13px] text-zinc-600">
              <span className="font-medium">{name}</span> is ready to use.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-4 space-y-4">
            <div>
              <label className="text-[12px] text-zinc-600 block mb-1">
                Organization Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full text-[13px] text-zinc-700 border border-zinc-300 rounded-md px-3 py-2 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                placeholder="My Company"
                required
                autoFocus
              />
              <p className="text-[11px] text-zinc-500 mt-1">
                You&apos;ll be the owner of this organization.
              </p>
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
                disabled={isLoading || !name.trim()}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors text-[13px] font-medium disabled:opacity-50"
              >
                {isLoading ? (
                  <>
                    <Loader className="w-4 h-4 animate-spin" />
                    Creating...
                  </>
                ) : (
                  'Create Organization'
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
