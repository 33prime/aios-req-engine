'use client'

import { useState, useEffect } from 'react'
import { Check, X, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/Button'

interface Patch {
  id: string
  title: string
  finding: string
  status: 'queued' | 'applied' | 'dismissed'
  auto_apply_ok: boolean
  parent_insight_id: string
  patch_data: {
    target_entity_type: 'prd_section' | 'feature' | 'vp_step'
    allowed_fields: string[]
    proposed_changes: Record<string, any>
    rationale: string
  }
  created_at: string
}

interface PatchesTabProps {
  projectId: string
}

export function PatchesTab({ projectId }: PatchesTabProps) {
  const [patches, setPatches] = useState<Patch[]>([])
  const [selectedPatch, setSelectedPatch] = useState<Patch | null>(null)
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState<'queued' | 'applied' | 'dismissed' | 'all'>('queued')
  const [applying, setApplying] = useState(false)

  useEffect(() => {
    loadPatches()
  }, [projectId, statusFilter])

  const loadPatches = async () => {
    try {
      setLoading(true)
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE}/v1/projects/${projectId}/patches?status=${statusFilter === 'all' ? '' : statusFilter}`
      )

      if (response.ok) {
        const data = await response.json()
        setPatches(data.patches || [])
        if (!selectedPatch && data.patches?.length > 0) {
          setSelectedPatch(data.patches[0])
        }
      }
    } catch (error) {
      console.error('❌ Failed to load patches:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleApplyPatch = async (patchId: string) => {
    try {
      setApplying(true)
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE}/v1/insights/${patchId}/apply-patch`,
        { method: 'POST' }
      )

      if (response.ok) {
        alert('Patch applied successfully!')
        loadPatches()
      } else {
        throw new Error(await response.text())
      }
    } catch (error) {
      console.error('❌ Failed to apply patch:', error)
      alert('Failed to apply patch')
    } finally {
      setApplying(false)
    }
  }

  const handleDismissPatch = async (patchId: string) => {
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE}/v1/insights/${patchId}/dismiss-patch`,
        { method: 'POST' }
      )

      if (response.ok) {
        alert('Patch dismissed')
        loadPatches()
      } else {
        throw new Error(await response.text())
      }
    } catch (error) {
      console.error('❌ Failed to dismiss patch:', error)
      alert('Failed to dismiss patch')
    }
  }

  if (loading) {
    return <div className="p-6 text-center text-ui-text-tertiary">Loading patches...</div>
  }

  return (
    <div className="flex h-full">
      {/* Left Panel - Patches List */}
      <div className="w-1/3 border-r border-ui-cardBorder flex flex-col">
        {/* Filter Tabs */}
        <div className="flex border-b border-ui-cardBorder">
          <button
            onClick={() => setStatusFilter('queued')}
            className={`flex-1 px-4 py-3 text-sm font-medium ${
              statusFilter === 'queued'
                ? 'text-brand-blue border-b-2 border-brand-blue'
                : 'text-ui-text-tertiary hover:text-ui-text-primary'
            }`}
          >
            Queued ({patches.filter((p) => p.status === 'queued').length})
          </button>
          <button
            onClick={() => setStatusFilter('applied')}
            className={`flex-1 px-4 py-3 text-sm font-medium ${
              statusFilter === 'applied'
                ? 'text-brand-blue border-b-2 border-brand-blue'
                : 'text-ui-text-tertiary hover:text-ui-text-primary'
            }`}
          >
            Applied ({patches.filter((p) => p.status === 'applied').length})
          </button>
          <button
            onClick={() => setStatusFilter('dismissed')}
            className={`flex-1 px-4 py-3 text-sm font-medium ${
              statusFilter === 'dismissed'
                ? 'text-brand-blue border-b-2 border-brand-blue'
                : 'text-ui-text-tertiary hover:text-ui-text-primary'
            }`}
          >
            Dismissed ({patches.filter((p) => p.status === 'dismissed').length})
          </button>
        </div>

        {/* Patches List */}
        <div className="flex-1 overflow-y-auto">
          {patches.length === 0 ? (
            <div className="p-6 text-center text-ui-text-tertiary">
              No {statusFilter} patches
            </div>
          ) : (
            <div className="divide-y divide-ui-cardBorder">
              {patches.map((patch) => (
                <button
                  key={patch.id}
                  onClick={() => setSelectedPatch(patch)}
                  className={`w-full p-4 text-left hover:bg-ui-cardBg transition-colors ${
                    selectedPatch?.id === patch.id ? 'bg-ui-cardBg border-l-2 border-brand-blue' : ''
                  }`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="text-sm font-medium text-ui-text-primary truncate pr-2">
                      {patch.title}
                    </div>
                    {patch.status === 'applied' && (
                      <Check className="h-4 w-4 text-green-600 flex-shrink-0" />
                    )}
                    {patch.status === 'dismissed' && (
                      <X className="h-4 w-4 text-gray-400 flex-shrink-0" />
                    )}
                  </div>
                  <div className="text-xs text-ui-text-tertiary line-clamp-2 mb-2">
                    {patch.finding}
                  </div>
                  <div className="flex items-center gap-2 text-xs">
                    <span className="px-2 py-1 bg-ui-cardBg border border-ui-cardBorder rounded text-ui-text-tertiary">
                      {patch.patch_data.target_entity_type}
                    </span>
                    {patch.auto_apply_ok && (
                      <span className="px-2 py-1 bg-green-50 text-green-700 rounded">
                        Safe
                      </span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Right Panel - Patch Detail */}
      <div className="flex-1 overflow-y-auto">
        {selectedPatch ? (
          <div className="p-6">
            {/* Header */}
            <div className="mb-6">
              <h2 className="text-xl font-semibold text-ui-text-primary mb-2">
                {selectedPatch.title}
              </h2>
              <div className="flex items-center gap-2 text-sm">
                <span className="px-2 py-1 bg-ui-cardBg border border-ui-cardBorder rounded text-ui-text-tertiary">
                  {selectedPatch.patch_data.target_entity_type}
                </span>
                <span className={`px-2 py-1 rounded ${
                  selectedPatch.status === 'queued' ? 'bg-yellow-50 text-yellow-700' :
                  selectedPatch.status === 'applied' ? 'bg-green-50 text-green-700' :
                  'bg-gray-50 text-gray-700'
                }`}>
                  {selectedPatch.status}
                </span>
                {selectedPatch.auto_apply_ok && (
                  <span className="px-2 py-1 bg-green-50 text-green-700 rounded flex items-center gap-1">
                    <Check className="h-3 w-3" />
                    Safe to auto-apply
                  </span>
                )}
              </div>
            </div>

            {/* Rationale */}
            <div className="mb-6">
              <h3 className="text-sm font-medium text-ui-text-primary mb-2">Rationale</h3>
              <p className="text-sm text-ui-text-secondary">
                {selectedPatch.patch_data.rationale}
              </p>
            </div>

            {/* Proposed Changes */}
            <div className="mb-6">
              <h3 className="text-sm font-medium text-ui-text-primary mb-2">Proposed Changes</h3>
              <div className="bg-ui-cardBg border border-ui-cardBorder rounded-lg p-4">
                <div className="text-xs text-ui-text-tertiary mb-2">
                  Allowed fields: {selectedPatch.patch_data.allowed_fields.join(', ')}
                </div>
                <div className="space-y-3">
                  {Object.entries(selectedPatch.patch_data.proposed_changes).map(([field, value]) => (
                    <div key={field}>
                      <div className="text-xs font-medium text-ui-text-tertiary mb-1">
                        {field}:
                      </div>
                      <div className="text-sm text-ui-text-primary bg-white border border-ui-cardBorder rounded p-2">
                        {typeof value === 'string' ? value : JSON.stringify(value, null, 2)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Actions */}
            {selectedPatch.status === 'queued' && (
              <div className="flex items-center gap-3 pt-6 border-t border-ui-cardBorder">
                <Button
                  variant="primary"
                  onClick={() => handleApplyPatch(selectedPatch.id)}
                  disabled={applying}
                  loading={applying}
                  icon={<Check className="h-4 w-4" />}
                >
                  Apply Patch
                </Button>
                <Button
                  variant="outline"
                  onClick={() => handleDismissPatch(selectedPatch.id)}
                  disabled={applying}
                  icon={<X className="h-4 w-4" />}
                >
                  Dismiss
                </Button>
              </div>
            )}

            {/* Safety Warning */}
            {!selectedPatch.auto_apply_ok && selectedPatch.status === 'queued' && (
              <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg flex items-start gap-2">
                <AlertCircle className="h-4 w-4 text-yellow-600 mt-0.5" />
                <div className="text-sm text-yellow-800">
                  <strong>Review Required:</strong> This patch was flagged for manual review due to
                  change type or severity. Please verify the changes carefully before applying.
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="h-full flex items-center justify-center text-ui-text-tertiary">
            Select a patch to view details
          </div>
        )}
      </div>
    </div>
  )
}
