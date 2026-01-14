'use client'

import { X, User, Target, AlertCircle, Lightbulb, Zap, Star, CheckCircle, Clock, TrendingUp, Search, AlertTriangle, ChevronRight, Sparkles, Trash2, RotateCcw, Loader2, History } from 'lucide-react'
import { Persona, PersonaWorkflow, getPersonaInitials, getPersonaColor, formatDemographicsOrPsychographics } from '@/lib/persona-utils'
import { DeleteConfirmationModal } from '@/components/ui/DeleteConfirmationModal'
import ChangeLogTimeline from '@/components/revisions/ChangeLogTimeline'
import { useState } from 'react'

type TabType = 'goals' | 'journey' | 'features' | 'gaps' | 'research' | 'history'

interface PersonaModalProps {
  persona: Persona | null
  relatedFeatures?: any[]
  relatedVpSteps?: any[]
  featureCoverage?: {
    addressed_goals: string[]
    unaddressed_goals: string[]
    feature_matches: Array<{ goal: string; features: Array<{ id: string; name: string; match_type: string }> }>
    coverage_score: number
  }
  isOpen: boolean
  onClose: () => void
  onConfirmationChange?: (personaId: string, newStatus: string) => Promise<void>
  onRunResearch?: (personaId: string) => Promise<void>
  onGenerateSuggestions?: (personaId: string) => Promise<void>
  onDelete?: (personaId: string) => void
  onBulkRebuild?: () => void
}

export default function PersonaModal({
  persona,
  relatedFeatures = [],
  relatedVpSteps = [],
  featureCoverage,
  isOpen,
  onClose,
  onConfirmationChange,
  onRunResearch,
  onGenerateSuggestions,
  onDelete,
  onBulkRebuild,
}: PersonaModalProps) {
  const [activeTab, setActiveTab] = useState<TabType>('goals')
  const [updating, setUpdating] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)

  // Check if persona is confirmed
  const isConfirmed = () => {
    const status = persona?.confirmation_status || 'ai_generated'
    return status === 'confirmed_consultant' || status === 'confirmed_client'
  }

  // Handle revert to draft
  const handleRevertToDraft = async () => {
    if (!onConfirmationChange || !persona?.id) return
    try {
      setUpdating(true)
      await onConfirmationChange(persona.id, 'ai_generated')
    } catch (error) {
      console.error('Failed to revert to draft:', error)
    } finally {
      setUpdating(false)
    }
  }

  // Handle delete
  const handleDeleted = () => {
    if (onDelete && persona?.id) {
      onDelete(persona.id)
    }
    setShowDeleteModal(false)
    onClose()
  }

  if (!isOpen || !persona) return null

  const initials = getPersonaInitials(persona)
  const colors = getPersonaColor(persona)

  const handleConfirmationChange = async (newStatus: string) => {
    if (!onConfirmationChange || !persona.id) return

    try {
      setUpdating(true)
      await onConfirmationChange(persona.id, newStatus)
    } catch (error) {
      console.error('Failed to update confirmation status:', error)
    } finally {
      setUpdating(false)
    }
  }

  const tabs: { id: TabType; label: string; icon: React.ReactNode }[] = [
    { id: 'goals', label: 'Goals', icon: <Target className="h-4 w-4" /> },
    { id: 'journey', label: 'Journey', icon: <Zap className="h-4 w-4" /> },
    { id: 'features', label: 'Features', icon: <Star className="h-4 w-4" /> },
    { id: 'gaps', label: 'Gaps', icon: <AlertTriangle className="h-4 w-4" /> },
    { id: 'research', label: 'Research', icon: <Search className="h-4 w-4" /> },
    { id: 'history', label: 'History', icon: <History className="h-4 w-4" /> },
  ]

  const coverageScore = persona.coverage_score ?? featureCoverage?.coverage_score ?? null
  const healthScore = persona.health_score ?? null

  const getCoverageColor = (score: number) => {
    if (score >= 70) return 'text-green-600'
    if (score >= 40) return 'text-amber-600'
    return 'text-red-600'
  }

  const getHealthColor = (score: number) => {
    if (score >= 70) return 'text-green-500'
    if (score >= 40) return 'text-amber-500'
    return 'text-red-500'
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto" onClick={onClose}>
      <div className="flex min-h-screen items-center justify-center p-4">
        {/* Overlay */}
        <div className="fixed inset-0 bg-black bg-opacity-50 transition-opacity" />

        {/* Modal */}
        <div
          className="relative bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex-shrink-0 bg-white border-b border-gray-200 px-6 py-4">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-4">
                {/* Avatar */}
                <div
                  className={`w-16 h-16 rounded-full ${colors.bg} ${colors.text} flex items-center justify-center font-semibold text-2xl`}
                >
                  {initials}
                </div>

                {/* Name, Role, and Scores */}
                <div>
                  <h2 className="text-2xl font-bold text-gray-900">{persona.name}</h2>
                  {persona.role && (
                    <p className="text-lg text-gray-600">{persona.role}</p>
                  )}
                  {/* Score badges */}
                  <div className="flex items-center gap-4 mt-2">
                    {coverageScore !== null && (
                      <div className={`flex items-center gap-1 text-sm font-medium ${getCoverageColor(coverageScore)}`}>
                        <TrendingUp className="h-4 w-4" />
                        <span>{coverageScore.toFixed(0)}% coverage</span>
                      </div>
                    )}
                    {healthScore !== null && (
                      <div className={`flex items-center gap-1 text-sm font-medium ${getHealthColor(healthScore)}`}>
                        <span className={`w-2 h-2 rounded-full ${healthScore >= 70 ? 'bg-green-500' : healthScore >= 40 ? 'bg-amber-500' : 'bg-red-500'}`} />
                        <span>{healthScore.toFixed(0)}% health</span>
                      </div>
                    )}
                  </div>
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

            {/* Tab Navigation */}
            <div className="flex gap-1 mt-4 border-b border-gray-200 -mb-4 -mx-6 px-6">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === tab.id
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  {tab.icon}
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6">
            {/* Goals & Pain Points Tab */}
            {activeTab === 'goals' && (
              <div className="space-y-6">
                {/* V2 Overview (enriched) or fallback to description */}
                {(persona.overview || persona.description) && (
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2 flex items-center gap-2">
                      Overview
                      {persona.enrichment_status === 'enriched' && (
                        <Sparkles className="h-4 w-4 text-amber-500" />
                      )}
                    </h3>
                    <p className="text-gray-700 whitespace-pre-wrap">{persona.overview || persona.description}</p>
                  </div>
                )}

                {/* Demographics */}
                {persona.demographics && formatDemographicsOrPsychographics(persona.demographics) && (
                  <div className="bg-blue-50 rounded-lg p-4 border border-blue-100">
                    <h3 className="text-sm font-semibold text-blue-900 mb-2 flex items-center gap-2">
                      <User className="h-4 w-4" />
                      Demographics
                    </h3>
                    <p className="text-blue-800">{formatDemographicsOrPsychographics(persona.demographics)}</p>
                  </div>
                )}

                {/* Psychographics */}
                {persona.psychographics && formatDemographicsOrPsychographics(persona.psychographics) && (
                  <div className="bg-purple-50 rounded-lg p-4 border border-purple-100">
                    <h3 className="text-sm font-semibold text-purple-900 mb-2 flex items-center gap-2">
                      <Lightbulb className="h-4 w-4" />
                      Psychographics
                    </h3>
                    <p className="text-purple-800">{formatDemographicsOrPsychographics(persona.psychographics)}</p>
                  </div>
                )}

                {/* Goals */}
                {persona.goals && persona.goals.length > 0 && (
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                      <Target className="h-5 w-5 text-green-600" />
                      Goals ({persona.goals.length})
                    </h3>
                    <ul className="space-y-2">
                      {persona.goals.map((goal, idx) => {
                        const isAddressed = featureCoverage?.addressed_goals?.includes(goal)
                        return (
                          <li key={idx} className="flex items-start gap-2">
                            {isAddressed ? (
                              <CheckCircle className="h-4 w-4 text-green-600 flex-shrink-0 mt-0.5" />
                            ) : (
                              <Star className="h-4 w-4 text-gray-400 flex-shrink-0 mt-0.5" />
                            )}
                            <span className={isAddressed ? 'text-gray-700' : 'text-gray-500'}>{goal}</span>
                          </li>
                        )
                      })}
                    </ul>
                  </div>
                )}

                {/* Pain Points */}
                {persona.pain_points && persona.pain_points.length > 0 && (
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                      <AlertCircle className="h-5 w-5 text-amber-600" />
                      Pain Points ({persona.pain_points.length})
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
              </div>
            )}

            {/* Journey Tab */}
            {activeTab === 'journey' && (
              <div className="space-y-6">
                {/* V2 Key Workflows (from enrichment) */}
                {persona.key_workflows && persona.key_workflows.length > 0 && (
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                      <Sparkles className="h-5 w-5 text-amber-500" />
                      Key Workflows ({persona.key_workflows.length})
                    </h3>
                    <div className="space-y-4">
                      {persona.key_workflows.map((workflow, idx) => (
                        <div
                          key={idx}
                          className="bg-gradient-to-br from-amber-50 to-orange-50 rounded-lg p-4 border border-amber-200"
                        >
                          <h4 className="font-semibold text-gray-900 mb-2">{workflow.name}</h4>
                          {workflow.description && (
                            <p className="text-sm text-gray-600 mb-3">{workflow.description}</p>
                          )}
                          {workflow.steps && workflow.steps.length > 0 && (
                            <div className="mb-3">
                              <p className="text-xs font-medium text-gray-500 uppercase mb-2">Steps</p>
                              <ol className="space-y-1.5">
                                {workflow.steps.map((step, stepIdx) => (
                                  <li key={stepIdx} className="flex items-start gap-2 text-sm text-gray-700">
                                    <span className="flex-shrink-0 w-5 h-5 bg-amber-600 text-white rounded-full flex items-center justify-center text-xs font-medium">
                                      {stepIdx + 1}
                                    </span>
                                    <span>{step.replace(/^Step \d+:\s*/i, '')}</span>
                                  </li>
                                ))}
                              </ol>
                            </div>
                          )}
                          {workflow.features_used && workflow.features_used.length > 0 && (
                            <div>
                              <p className="text-xs font-medium text-gray-500 uppercase mb-2">Features Used</p>
                              <div className="flex flex-wrap gap-1.5">
                                {workflow.features_used.map((feature, fIdx) => (
                                  <span
                                    key={fIdx}
                                    className="inline-flex items-center px-2 py-0.5 bg-white text-amber-800 text-xs rounded border border-amber-200"
                                  >
                                    {feature}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Value Path Steps */}
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                    <Zap className="h-5 w-5 text-purple-600" />
                    Value Path Steps ({relatedVpSteps.length})
                  </h3>
                  {relatedVpSteps.length > 0 ? (
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
                                <p className="text-sm text-gray-700 mb-2">{step.description}</p>
                              )}
                              {step.user_benefit_pain && (
                                <p className="text-sm text-gray-600 italic">
                                  "{step.user_benefit_pain}"
                                </p>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-4 text-gray-500 bg-gray-50 rounded-lg">
                      <p className="text-sm">No VP steps linked to this persona yet</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Features Tab */}
            {activeTab === 'features' && (
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-gray-900 mb-3">
                  Related Features ({relatedFeatures.length})
                </h3>
                {relatedFeatures.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {relatedFeatures.map((feature) => {
                      // Find this persona's context from the feature's target_personas
                      const personaContext = feature.target_personas?.find(
                        (tp: any) => tp.persona_name?.toLowerCase() === persona?.name?.toLowerCase()
                      )
                      return (
                        <div
                          key={feature.id}
                          className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg p-4 border border-blue-200"
                        >
                          <div className="flex items-start justify-between mb-2">
                            <h4 className="font-semibold text-gray-900 flex-1">{feature.name}</h4>
                            <div className="flex items-center gap-1.5">
                              {personaContext?.role && (
                                <span className={`text-xs font-medium px-2 py-0.5 rounded ${
                                  personaContext.role === 'primary'
                                    ? 'text-green-700 bg-green-100'
                                    : 'text-gray-600 bg-gray-100'
                                }`}>
                                  {personaContext.role === 'primary' ? 'Primary' : 'Secondary'}
                                </span>
                              )}
                              {feature.is_mvp && (
                                <span className="text-xs font-medium text-blue-700 bg-blue-100 px-2 py-0.5 rounded">
                                  MVP
                                </span>
                              )}
                            </div>
                          </div>
                          {feature.category && (
                            <p className="text-sm text-gray-600 mb-1">
                              <span className="font-medium">Category:</span> {feature.category}
                            </p>
                          )}
                          {/* Show persona-specific context if available */}
                          {personaContext?.context && (
                            <p className="text-sm text-gray-700 mb-2 italic">
                              "{personaContext.context}"
                            </p>
                          )}
                          {/* Fallback to overview or summary */}
                          {!personaContext?.context && (feature.overview || feature.details?.summary) && (
                            <p className="text-sm text-gray-700 line-clamp-2">
                              {feature.overview || feature.details.summary}
                            </p>
                          )}
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    <p>No features linked to this persona yet</p>
                    <p className="text-sm mt-1">Enrich features to link them to personas</p>
                  </div>
                )}
              </div>
            )}

            {/* Gaps Tab */}
            {activeTab === 'gaps' && (
              <div className="space-y-6">
                {/* Unaddressed Goals */}
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                    <AlertTriangle className="h-5 w-5 text-amber-600" />
                    Unaddressed Goals
                  </h3>
                  {featureCoverage?.unaddressed_goals && featureCoverage.unaddressed_goals.length > 0 ? (
                    <ul className="space-y-2">
                      {featureCoverage.unaddressed_goals.map((goal, idx) => (
                        <li key={idx} className="flex items-start gap-2 p-3 bg-amber-50 rounded-lg border border-amber-200">
                          <AlertTriangle className="h-4 w-4 text-amber-600 flex-shrink-0 mt-0.5" />
                          <span className="text-gray-700">{goal}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div className="text-center py-4 text-green-600 bg-green-50 rounded-lg">
                      <CheckCircle className="h-8 w-8 mx-auto mb-2" />
                      <p className="font-medium">All goals addressed!</p>
                      <p className="text-sm text-gray-600">Features cover all identified goals for this persona</p>
                    </div>
                  )}
                </div>

                {/* Feature Suggestions */}
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                    <Lightbulb className="h-5 w-5 text-blue-600" />
                    Suggested Features
                  </h3>
                  {onGenerateSuggestions ? (
                    <button
                      onClick={() => persona.id && onGenerateSuggestions(persona.id)}
                      className="w-full py-3 px-4 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-lg text-blue-700 font-medium transition-colors flex items-center justify-center gap-2"
                    >
                      <Lightbulb className="h-5 w-5" />
                      Generate Feature Suggestions
                    </button>
                  ) : (
                    <div className="text-center py-4 text-gray-500 bg-gray-50 rounded-lg">
                      <p className="text-sm">Feature suggestions not available</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Research Tab */}
            {activeTab === 'research' && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                    <Search className="h-5 w-5 text-blue-600" />
                    Research & Validation
                  </h3>
                  <p className="text-gray-600 mb-4">
                    Run targeted research to validate this persona's goals, pain points, and feature preferences.
                  </p>
                  {onRunResearch ? (
                    <button
                      onClick={() => persona.id && onRunResearch(persona.id)}
                      className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
                    >
                      <Search className="h-5 w-5" />
                      Run Persona Research
                    </button>
                  ) : (
                    <div className="text-center py-4 text-gray-500 bg-gray-50 rounded-lg">
                      <p className="text-sm">Research not available</p>
                    </div>
                  )}
                </div>

                {/* Research History Placeholder */}
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">Research History</h4>
                  <div className="text-center py-8 text-gray-500 bg-gray-50 rounded-lg">
                    <p>No research conducted yet</p>
                    <p className="text-sm mt-1">Research results will appear here</p>
                  </div>
                </div>
              </div>
            )}

            {/* History Tab */}
            {activeTab === 'history' && persona.id && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                    <History className="h-5 w-5 text-gray-600" />
                    Change History
                  </h3>
                  <p className="text-gray-600 mb-4">
                    View all changes made to this persona over time.
                  </p>
                </div>
                <ChangeLogTimeline entityType="persona" entityId={persona.id} limit={20} />
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex-shrink-0 bg-gray-50 border-t border-gray-200 px-6 py-4">
            {onConfirmationChange && persona.id && (
              <div className="mb-4">
                <h4 className="text-sm font-medium text-gray-700 mb-3">Actions</h4>
                <div className="flex flex-wrap gap-2">
                  {isConfirmed() ? (
                    <>
                      {/* Confirmed state - show status badge, revert, and delete */}
                      <span className="flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-blue-600 text-white">
                        <CheckCircle className="h-4 w-4" />
                        Confirmed
                      </span>
                      <button
                        onClick={handleRevertToDraft}
                        disabled={updating}
                        className="flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                      >
                        {updating ? <Loader2 className="h-4 w-4 animate-spin" /> : <RotateCcw className="h-4 w-4" />}
                        Revert to Draft
                      </button>
                      <button
                        onClick={() => setShowDeleteModal(true)}
                        className="flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-white border border-red-200 text-red-600 hover:bg-red-50"
                      >
                        <Trash2 className="h-4 w-4" />
                        Delete
                      </button>
                    </>
                  ) : (
                    <>
                      {/* Draft state - show confirm, needs review, and delete */}
                      <button
                        onClick={() => handleConfirmationChange('confirmed_consultant')}
                        disabled={updating}
                        className="flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                      >
                        {updating ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle className="h-4 w-4" />}
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
                        Needs Review
                      </button>
                      <button
                        onClick={() => setShowDeleteModal(true)}
                        className="flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-white border border-red-200 text-red-600 hover:bg-red-50"
                      >
                        <Trash2 className="h-4 w-4" />
                        Delete
                      </button>
                    </>
                  )}
                </div>
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

      {/* Delete Confirmation Modal */}
      {showDeleteModal && persona && (
        <DeleteConfirmationModal
          isOpen={true}
          onClose={() => setShowDeleteModal(false)}
          entityType="persona"
          entityId={persona.id || ''}
          entityName={persona.name}
          onDeleted={handleDeleted}
          onBulkRebuild={onBulkRebuild}
        />
      )}
    </div>
  )
}
