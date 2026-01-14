/**
 * DeleteConfirmationModal Component
 *
 * Modal for confirming entity deletion with cascade impact analysis.
 * Shows what will be affected and suggests bulk rebuild if impact > 50%.
 */

'use client'

import React, { useEffect, useState } from 'react'
import {
  AlertTriangle,
  Trash2,
  Loader2,
  Users,
  Target,
  Route,
  RefreshCw,
} from 'lucide-react'
import { Modal } from './Modal'
import {
  getFeatureCascadeImpact,
  getPersonaCascadeImpact,
  deleteFeature,
  deletePersona,
  type FeatureCascadeImpact,
  type PersonaCascadeImpact,
} from '@/lib/api'

type EntityType = 'feature' | 'persona'

interface DeleteConfirmationModalProps {
  isOpen: boolean
  onClose: () => void
  entityType: EntityType
  entityId: string
  entityName: string
  onDeleted: () => void
  onBulkRebuild?: () => void
}

export function DeleteConfirmationModal({
  isOpen,
  onClose,
  entityType,
  entityId,
  entityName,
  onDeleted,
  onBulkRebuild,
}: DeleteConfirmationModalProps) {
  const [loading, setLoading] = useState(true)
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [impact, setImpact] = useState<FeatureCascadeImpact | PersonaCascadeImpact | null>(null)

  // Fetch impact analysis when modal opens
  useEffect(() => {
    if (isOpen && entityId) {
      fetchImpact()
    }
  }, [isOpen, entityId, entityType])

  const fetchImpact = async () => {
    setLoading(true)
    setError(null)
    try {
      if (entityType === 'feature') {
        const result = await getFeatureCascadeImpact(entityId)
        setImpact(result)
      } else {
        const result = await getPersonaCascadeImpact(entityId)
        setImpact(result)
      }
    } catch (e) {
      setError('Failed to analyze cascade impact')
      console.error('Error fetching cascade impact:', e)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async () => {
    setDeleting(true)
    setError(null)
    try {
      if (entityType === 'feature') {
        await deleteFeature(entityId, true)
      } else {
        await deletePersona(entityId, true)
      }
      onDeleted()
      onClose()
    } catch (e) {
      setError('Failed to delete. Please try again.')
      console.error('Error deleting:', e)
    } finally {
      setDeleting(false)
    }
  }

  const handleBulkRebuild = () => {
    if (onBulkRebuild) {
      onBulkRebuild()
    }
    onClose()
  }

  // Type guards for impact
  const isFeatureImpact = (imp: any): imp is FeatureCascadeImpact => {
    return 'affected_personas' in imp
  }

  const isPersonaImpact = (imp: any): imp is PersonaCascadeImpact => {
    return 'affected_features' in imp
  }

  const renderImpactSection = () => {
    if (!impact) return null

    const hasAffected = entityType === 'feature'
      ? (impact as FeatureCascadeImpact).affected_vp_count > 0 || (impact as FeatureCascadeImpact).affected_persona_count > 0
      : (impact as PersonaCascadeImpact).affected_feature_count > 0 || (impact as PersonaCascadeImpact).affected_vp_count > 0

    if (!hasAffected) {
      return (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
          <p className="text-sm text-green-800">
            No other entities reference this {entityType}. It can be safely deleted.
          </p>
        </div>
      )
    }

    return (
      <div className="space-y-4">
        {/* Impact warning */}
        <div className={`rounded-lg p-4 ${
          impact.suggest_bulk_rebuild
            ? 'bg-amber-50 border border-amber-200'
            : 'bg-yellow-50 border border-yellow-200'
        }`}>
          <div className="flex items-start gap-3">
            <AlertTriangle className={`h-5 w-5 flex-shrink-0 mt-0.5 ${
              impact.suggest_bulk_rebuild ? 'text-amber-600' : 'text-yellow-600'
            }`} />
            <div>
              <p className={`text-sm font-medium ${
                impact.suggest_bulk_rebuild ? 'text-amber-800' : 'text-yellow-800'
              }`}>
                {impact.suggest_bulk_rebuild
                  ? `High Impact: ${impact.impact_percentage}% of related entities affected`
                  : `This will affect ${impact.impact_percentage}% of related entities`
                }
              </p>
              <p className={`text-sm mt-1 ${
                impact.suggest_bulk_rebuild ? 'text-amber-700' : 'text-yellow-700'
              }`}>
                {impact.suggest_bulk_rebuild
                  ? 'Consider rebuilding affected entities instead of just removing references.'
                  : 'References will be cleaned up from affected entities.'
                }
              </p>
            </div>
          </div>
        </div>

        {/* Affected entities list */}
        <div className="space-y-3">
          {entityType === 'feature' && isFeatureImpact(impact) && (
            <>
              {impact.affected_vp_steps.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                    <Route className="h-4 w-4" />
                    <span>Affected Value Path Steps ({impact.affected_vp_steps.length})</span>
                  </div>
                  <ul className="text-sm text-gray-600 space-y-1 ml-6">
                    {impact.affected_vp_steps.slice(0, 5).map((step) => (
                      <li key={step.id}>
                        Step {step.step_index}: {step.label}
                      </li>
                    ))}
                    {impact.affected_vp_steps.length > 5 && (
                      <li className="text-gray-400">
                        +{impact.affected_vp_steps.length - 5} more
                      </li>
                    )}
                  </ul>
                </div>
              )}
              {impact.affected_personas.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                    <Users className="h-4 w-4" />
                    <span>Affected Personas ({impact.affected_personas.length})</span>
                  </div>
                  <ul className="text-sm text-gray-600 space-y-1 ml-6">
                    {impact.affected_personas.slice(0, 5).map((persona) => (
                      <li key={persona.id}>{persona.name}</li>
                    ))}
                    {impact.affected_personas.length > 5 && (
                      <li className="text-gray-400">
                        +{impact.affected_personas.length - 5} more
                      </li>
                    )}
                  </ul>
                </div>
              )}
            </>
          )}

          {entityType === 'persona' && isPersonaImpact(impact) && (
            <>
              {impact.affected_features.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                    <Target className="h-4 w-4" />
                    <span>Affected Features ({impact.affected_features.length})</span>
                  </div>
                  <ul className="text-sm text-gray-600 space-y-1 ml-6">
                    {impact.affected_features.slice(0, 5).map((feature) => (
                      <li key={feature.id}>{feature.name}</li>
                    ))}
                    {impact.affected_features.length > 5 && (
                      <li className="text-gray-400">
                        +{impact.affected_features.length - 5} more
                      </li>
                    )}
                  </ul>
                </div>
              )}
              {impact.affected_vp_steps.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                    <Route className="h-4 w-4" />
                    <span>Affected Value Path Steps ({impact.affected_vp_steps.length})</span>
                  </div>
                  <ul className="text-sm text-gray-600 space-y-1 ml-6">
                    {impact.affected_vp_steps.slice(0, 5).map((step) => (
                      <li key={step.id}>
                        Step {step.step_index}: {step.label}
                      </li>
                    ))}
                    {impact.affected_vp_steps.length > 5 && (
                      <li className="text-gray-400">
                        +{impact.affected_vp_steps.length - 5} more
                      </li>
                    )}
                  </ul>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    )
  }

  const footer = (
    <>
      <button
        onClick={onClose}
        className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
        disabled={deleting}
      >
        Cancel
      </button>
      {impact?.suggest_bulk_rebuild && onBulkRebuild && (
        <button
          onClick={handleBulkRebuild}
          className="px-4 py-2 text-sm font-medium text-amber-700 bg-amber-50 border border-amber-300 rounded-lg hover:bg-amber-100 flex items-center gap-2"
          disabled={deleting}
        >
          <RefreshCw className="h-4 w-4" />
          Rebuild Affected
        </button>
      )}
      <button
        onClick={handleDelete}
        className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 flex items-center gap-2"
        disabled={deleting}
      >
        {deleting ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Trash2 className="h-4 w-4" />
        )}
        {deleting ? 'Deleting...' : 'Delete'}
      </button>
    </>
  )

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Delete ${entityType === 'feature' ? 'Feature' : 'Persona'}`}
      size="md"
      footer={footer}
    >
      <div className="space-y-4">
        {/* Entity being deleted */}
        <div className="flex items-start gap-3 p-4 bg-gray-50 rounded-lg">
          {entityType === 'feature' ? (
            <Target className="h-5 w-5 text-gray-500 flex-shrink-0 mt-0.5" />
          ) : (
            <Users className="h-5 w-5 text-gray-500 flex-shrink-0 mt-0.5" />
          )}
          <div>
            <p className="text-sm font-medium text-gray-900">{entityName}</p>
            <p className="text-sm text-gray-500">
              This {entityType} will be permanently deleted.
            </p>
          </div>
        </div>

        {/* Loading state */}
        {loading && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-blue-500 mr-2" />
            <span className="text-sm text-gray-500">Analyzing impact...</span>
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Impact analysis */}
        {!loading && !error && renderImpactSection()}
      </div>
    </Modal>
  )
}
