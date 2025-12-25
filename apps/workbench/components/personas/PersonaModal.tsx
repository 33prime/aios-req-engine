'use client'

import { X, User, Target, AlertCircle, Lightbulb, Zap, Star, CheckCircle, Clock } from 'lucide-react'
import { Persona, getPersonaInitials, getPersonaColor } from '@/lib/persona-utils'
import { useState } from 'react'

interface PersonaModalProps {
  persona: Persona | null
  relatedFeatures?: any[]
  relatedVpSteps?: any[]
  isOpen: boolean
  onClose: () => void
  onConfirmationChange?: (personaId: string, newStatus: string) => Promise<void>
}

export default function PersonaModal({
  persona,
  relatedFeatures = [],
  relatedVpSteps = [],
  isOpen,
  onClose,
  onConfirmationChange,
}: PersonaModalProps) {
  const [updating, setUpdating] = useState(false)

  if (!isOpen || !persona) return null

  const initials = getPersonaInitials(persona)
  const colors = getPersonaColor(persona)

  const handleConfirmationChange = async (newStatus: string) => {
    if (!onConfirmationChange) return

    try {
      setUpdating(true)
      await onConfirmationChange(persona.id, newStatus)
    } catch (error) {
      console.error('Failed to update confirmation status:', error)
    } finally {
      setUpdating(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto" onClick={onClose}>
      <div className="flex min-h-screen items-center justify-center p-4">
        {/* Overlay */}
        <div className="fixed inset-0 bg-black bg-opacity-50 transition-opacity" />

        {/* Modal */}
        <div
          className="relative bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-start justify-between">
            <div className="flex items-center gap-4">
              {/* Avatar */}
              <div
                className={`w-16 h-16 rounded-full ${colors.bg} ${colors.text} flex items-center justify-center font-semibold text-2xl`}
              >
                {initials}
              </div>

              {/* Name and Role */}
              <div>
                <h2 className="text-2xl font-bold text-gray-900">{persona.name}</h2>
                {persona.role && (
                  <p className="text-lg text-gray-600">{persona.role}</p>
                )}
              </div>
            </div>

            {/* Close Button */}
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <X className="h-6 w-6" />
            </button>
          </div>

          {/* Content */}
          <div className="p-6 space-y-6">
            {/* Description */}
            {persona.description && (
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Overview</h3>
                <p className="text-gray-700 whitespace-pre-wrap">{persona.description}</p>
              </div>
            )}

            {/* Demographics */}
            {persona.demographics && (
              <div className="bg-blue-50 rounded-lg p-4 border border-blue-100">
                <h3 className="text-sm font-semibold text-blue-900 mb-2 flex items-center gap-2">
                  <User className="h-4 w-4" />
                  Demographics
                </h3>
                <p className="text-blue-800">{persona.demographics}</p>
              </div>
            )}

            {/* Psychographics */}
            {persona.psychographics && (
              <div className="bg-purple-50 rounded-lg p-4 border border-purple-100">
                <h3 className="text-sm font-semibold text-purple-900 mb-2 flex items-center gap-2">
                  <Lightbulb className="h-4 w-4" />
                  Psychographics
                </h3>
                <p className="text-purple-800">{persona.psychographics}</p>
              </div>
            )}

            {/* Goals */}
            {persona.goals && persona.goals.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                  <Target className="h-5 w-5 text-green-600" />
                  Goals
                </h3>
                <ul className="space-y-2">
                  {persona.goals.map((goal, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <Star className="h-4 w-4 text-green-600 flex-shrink-0 mt-0.5" />
                      <span className="text-gray-700">{goal}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Pain Points */}
            {persona.pain_points && persona.pain_points.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                  <AlertCircle className="h-5 w-5 text-amber-600" />
                  Pain Points
                </h3>
                <ul className="space-y-2">
                  {persona.pain_points.map((pain, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <AlertCircle className="h-4 w-4 text-amber-600 flex-shrink-0 mt-0.5" />
                      <span className="text-gray-700">{pain}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Related Features */}
            {relatedFeatures.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-3">
                  Related Features ({relatedFeatures.length})
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {relatedFeatures.map((feature) => (
                    <div
                      key={feature.id}
                      className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg p-4 border border-blue-200"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <h4 className="font-semibold text-gray-900 flex-1">{feature.name}</h4>
                        {feature.is_mvp && (
                          <span className="text-xs font-medium text-blue-700 bg-blue-100 px-2 py-0.5 rounded">
                            MVP
                          </span>
                        )}
                      </div>
                      {feature.category && (
                        <p className="text-sm text-gray-600 mb-1">
                          <span className="font-medium">Category:</span> {feature.category}
                        </p>
                      )}
                      {feature.details?.summary && (
                        <p className="text-sm text-gray-700 line-clamp-2">
                          {feature.details.summary}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Related VP Steps */}
            {relatedVpSteps.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                  <Zap className="h-5 w-5 text-purple-600" />
                  Related Value Path Steps ({relatedVpSteps.length})
                </h3>
                <div className="space-y-3">
                  {relatedVpSteps.map((step) => (
                    <div
                      key={step.id}
                      className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-lg p-4 border border-purple-200"
                    >
                      <div className="flex items-start gap-3">
                        <div className="flex-shrink-0 w-8 h-8 bg-purple-600 text-white rounded-full flex items-center justify-center font-semibold text-sm">
                          {step.step_index}
                        </div>
                        <div className="flex-1">
                          <h4 className="font-semibold text-gray-900 mb-1">{step.label}</h4>
                          {step.description && (
                            <p className="text-sm text-gray-700 line-clamp-2">{step.description}</p>
                          )}
                          {step.user_benefit_pain && (
                            <p className="text-sm text-gray-600 mt-2 italic">
                              "{step.user_benefit_pain}"
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Empty State if no related items */}
            {relatedFeatures.length === 0 && relatedVpSteps.length === 0 && (
              <div className="text-center py-8 text-gray-500">
                <p>No related features or VP steps found</p>
                <p className="text-sm mt-1">These will appear as features and steps reference this persona</p>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 px-6 py-4">
            {onConfirmationChange && (
              <div className="mb-4">
                <h4 className="text-sm font-medium text-gray-700 mb-3">Confirmation Status</h4>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => handleConfirmationChange('confirmed_consultant')}
                    disabled={updating || persona.confirmation_status === 'confirmed_consultant'}
                    className={`flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                      persona.confirmation_status === 'confirmed_consultant'
                        ? 'bg-blue-600 text-white'
                        : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50'
                    }`}
                  >
                    <CheckCircle className="h-4 w-4" />
                    Confirm
                  </button>
                  <button
                    onClick={() => handleConfirmationChange('needs_client')}
                    disabled={updating || persona.confirmation_status === 'needs_client'}
                    className={`flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                      persona.confirmation_status === 'needs_client'
                        ? 'bg-amber-600 text-white'
                        : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50'
                    }`}
                  >
                    <Clock className="h-4 w-4" />
                    Needs Client Review
                  </button>
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  Confirm if the persona is accurate. Mark for client review if clarification is needed.
                </p>
              </div>
            )}

            <div className="flex justify-end">
              <button
                onClick={onClose}
                className="px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
