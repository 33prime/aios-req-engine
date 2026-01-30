'use client'

import { X, User, Target, AlertCircle, Lightbulb, Zap, Star, CheckCircle, Clock, TrendingUp, Search, AlertTriangle, Sparkles, Trash2, RotateCcw, Loader2, History, Bot } from 'lucide-react'
import { Persona, getPersonaInitials, formatDemographicsOrPsychographics } from '@/lib/persona-utils'
import { DeleteConfirmationModal } from '@/components/ui/DeleteConfirmationModal'
import ChangeLogTimeline from '@/components/revisions/ChangeLogTimeline'
import { markEntityNeedsReview } from '@/lib/api'
import { useState } from 'react'

type TabType = 'goals' | 'journey' | 'features' | 'gaps' | 'research' | 'history'

interface PersonaModalProps {
  persona: Persona | null
  projectId?: string
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
  projectId,
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

  if (!persona) return null

  const initials = getPersonaInitials(persona)

  const handleConfirmationChange = async (newStatus: string) => {
    if (!persona.id) return

    try {
      setUpdating(true)

      // Use the new API for "needs_client" status if projectId is provided
      if (newStatus === 'needs_client' && projectId) {
        await markEntityNeedsReview(projectId, 'persona', persona.id)
      } else if (onConfirmationChange) {
        // Use legacy callback for other statuses
        await onConfirmationChange(persona.id, newStatus)
      }
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

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 bg-black bg-opacity-50 z-40 transition-opacity duration-300 ${
          isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
        }`}
        onClick={onClose}
      />

      {/* Side Panel */}
      <div
        className={`fixed top-0 right-0 h-full w-[600px] max-w-full bg-white shadow-xl z-50 transform transition-transform duration-300 ease-in-out flex flex-col ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        {/* Sticky Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 z-10">
          {/* Header content */}
          <div className="flex items-center justify-between p-6">
            <div className="flex items-center gap-3">
              {/* Emerald Avatar */}
              <div className="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center text-lg font-semibold text-emerald-700">
                {initials}
              </div>
              <div>
                <h2 className="text-xl font-semibold text-gray-900">{persona.name}</h2>
                {persona.role && (
                  <p className="text-sm text-gray-600">{persona.role}</p>
                )}
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          {/* Coverage badge */}
          {coverageScore !== null && (
            <div className="px-6 pb-4">
              <div className="flex items-center gap-1 text-xs text-gray-600">
                <TrendingUp className="w-4 h-4" />
                <span className="font-medium">{coverageScore.toFixed(0)}% coverage</span>
                {healthScore !== null && healthScore < 50 && (
                  <span className="ml-2 text-amber-600 flex items-center gap-1">
                    <AlertTriangle className="h-3 w-3" />
                    Needs update
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Tab navigation with teal active state */}
          <div className="border-b border-gray-200 px-6">
            <nav className="-mb-px flex space-x-6 overflow-x-auto">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center py-3 px-1 border-b-2 font-medium text-sm transition-colors whitespace-nowrap ${
                    activeTab === tab.id
                      ? 'border-[#009b87] text-[#009b87]'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  {tab.icon}
                  <span className="ml-2">{tab.label}</span>
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* Content - Scrollable */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Goals & Pain Points Tab */}
          {activeTab === 'goals' && (
            <div className="space-y-6">
              {/* Overview */}
              {(persona.overview || persona.description) && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 mb-2 flex items-center gap-2">
                    Overview
                    {persona.enrichment_status === 'enriched' && (
                      <Sparkles className="h-4 w-4 text-amber-500" />
                    )}
                  </h3>
                  <p className="text-sm text-gray-700 whitespace-pre-wrap">{persona.overview || persona.description}</p>
                </div>
              )}

              {/* Demographics - Emerald box */}
              {persona.demographics && formatDemographicsOrPsychographics(persona.demographics) && (
                <div>
                  <h4 className="text-xs font-semibold text-[#009b87] uppercase tracking-wide mb-3 flex items-center gap-2">
                    <User className="w-4 h-4" /> Demographics
                  </h4>
                  <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3">
                    <p className="text-sm text-emerald-700">{formatDemographicsOrPsychographics(persona.demographics)}</p>
                  </div>
                </div>
              )}

              {/* Psychographics - Gray box */}
              {persona.psychographics && formatDemographicsOrPsychographics(persona.psychographics) && (
                <div>
                  <h4 className="text-xs font-semibold text-[#009b87] uppercase tracking-wide mb-3 flex items-center gap-2">
                    <Lightbulb className="w-4 h-4" /> Psychographics
                  </h4>
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                    <p className="text-sm text-gray-700">{formatDemographicsOrPsychographics(persona.psychographics)}</p>
                  </div>
                </div>
              )}

              {/* Goals with star icons */}
              {persona.goals && persona.goals.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-[#009b87] uppercase tracking-wide mb-3 flex items-center gap-2">
                    <Target className="w-4 h-4" /> Goals ({persona.goals.length})
                  </h4>
                  <div className="space-y-2">
                    {persona.goals.map((goal, idx) => {
                      const isAddressed = featureCoverage?.addressed_goals?.includes(goal)
                      return (
                        <div key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                          {isAddressed ? (
                            <CheckCircle className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                          ) : (
                            <Star className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
                          )}
                          <span className={isAddressed ? '' : 'text-gray-500'}>{goal}</span>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}

              {/* Pain Points */}
              {persona.pain_points && persona.pain_points.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-[#009b87] uppercase tracking-wide mb-3 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4" /> Pain Points ({persona.pain_points.length})
                  </h4>
                  <div className="space-y-2">
                    {persona.pain_points.map((pain, idx) => (
                      <div key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                        <AlertCircle className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />
                        <span>{pain}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Journey Tab */}
          {activeTab === 'journey' && (
            <div className="space-y-6">
              {/* Key Workflows */}
              {persona.key_workflows && persona.key_workflows.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-[#009b87] uppercase tracking-wide mb-3 flex items-center gap-2">
                    <Sparkles className="w-4 h-4" /> Key Workflows ({persona.key_workflows.length})
                  </h4>
                  <div className="space-y-4">
                    {persona.key_workflows.map((workflow, idx) => (
                      <div
                        key={idx}
                        className="bg-white border-2 border-gray-200 rounded-lg p-4"
                      >
                        <h4 className="text-sm font-semibold text-gray-900 mb-2">{workflow.name}</h4>
                        {workflow.description && (
                          <p className="text-sm text-gray-700 mb-3">{workflow.description}</p>
                        )}

                        {workflow.steps && workflow.steps.length > 0 && (
                          <div className="mb-3">
                            <h5 className="text-xs font-semibold text-[#009b87] uppercase tracking-wide mb-2">Steps</h5>
                            <div className="space-y-2">
                              {workflow.steps.map((step, stepIdx) => (
                                <div key={stepIdx} className="flex items-start gap-2 text-sm">
                                  <div className="w-5 h-5 rounded-full bg-[#009b87] text-white flex items-center justify-center text-xs font-semibold flex-shrink-0 mt-0.5">
                                    {stepIdx + 1}
                                  </div>
                                  <span className="text-gray-700">{step.replace(/^Step \d+:\s*/i, '')}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {workflow.features_used && workflow.features_used.length > 0 && (
                          <div>
                            <h5 className="text-xs font-semibold text-[#009b87] uppercase tracking-wide mb-2">Features Used</h5>
                            <div className="flex flex-wrap gap-2">
                              {workflow.features_used.map((feature, fIdx) => (
                                <span
                                  key={fIdx}
                                  className="px-2 py-1 text-xs bg-gray-50 border border-gray-200 rounded text-gray-700"
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

              {/* Value Path Steps - Teal styling */}
              <div>
                <h4 className="text-xs font-semibold text-[#009b87] uppercase tracking-wide mb-3 flex items-center gap-2">
                  <Zap className="w-4 h-4" /> Value Path Steps ({relatedVpSteps.length})
                </h4>
                {relatedVpSteps.length > 0 ? (
                  <div className="space-y-3">
                    {relatedVpSteps.map((step) => (
                      <div
                        key={step.id}
                        className="bg-emerald-50 border-2 border-[#009b87] rounded-lg p-4"
                      >
                        <div className="flex items-start gap-3 mb-2">
                          <div className="w-7 h-7 rounded-full bg-[#009b87] text-white flex items-center justify-center text-sm font-semibold flex-shrink-0">
                            {step.step_index}
                          </div>
                          <h4 className="text-sm font-semibold text-gray-900">{step.label}</h4>
                        </div>
                        {step.description && (
                          <p className="text-sm text-gray-700 ml-10">{step.description}</p>
                        )}
                        {step.value_created && (
                          <p className="text-xs text-gray-600 italic ml-10 mt-2">"{step.value_created}"</p>
                        )}
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
              <h4 className="text-xs font-semibold text-[#009b87] uppercase tracking-wide mb-3 flex items-center gap-2">
                <Star className="w-4 h-4" /> Related Features ({relatedFeatures.length})
              </h4>
              {relatedFeatures.length > 0 ? (
                <div className="space-y-3">
                  {relatedFeatures.map((feature) => {
                    const personaContext = feature.target_personas?.find(
                      (tp: any) => tp.persona_name?.toLowerCase() === persona?.name?.toLowerCase()
                    )
                    return (
                      <div
                        key={feature.id}
                        className="bg-white border border-gray-200 rounded-lg p-4"
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
                              <span className="text-xs font-medium text-white bg-[#009b87] px-2 py-0.5 rounded">
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
                        {personaContext?.context && (
                          <p className="text-sm text-gray-700 italic">
                            "{personaContext.context}"
                          </p>
                        )}
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
                <div className="text-center py-8 text-gray-500 bg-gray-50 rounded-lg">
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
                <h4 className="text-xs font-semibold text-[#009b87] uppercase tracking-wide mb-3 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" /> Unaddressed Goals
                </h4>
                {featureCoverage?.unaddressed_goals && featureCoverage.unaddressed_goals.length > 0 ? (
                  <div className="space-y-2">
                    {featureCoverage.unaddressed_goals.map((goal, idx) => (
                      <div key={idx} className="flex items-start gap-2 p-3 bg-amber-50 rounded-lg border border-amber-200">
                        <AlertTriangle className="h-4 w-4 text-amber-600 flex-shrink-0 mt-0.5" />
                        <span className="text-sm text-gray-700">{goal}</span>
                      </div>
                    ))}
                  </div>
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
                <h4 className="text-xs font-semibold text-[#009b87] uppercase tracking-wide mb-3 flex items-center gap-2">
                  <Lightbulb className="w-4 h-4" /> Suggested Features
                </h4>
                {onGenerateSuggestions ? (
                  <button
                    onClick={() => persona.id && onGenerateSuggestions(persona.id)}
                    className="w-full py-3 px-4 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 rounded-lg text-[#009b87] font-medium transition-colors flex items-center justify-center gap-2"
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
                <h4 className="text-xs font-semibold text-[#009b87] uppercase tracking-wide mb-3 flex items-center gap-2">
                  <Search className="w-4 h-4" /> Research & Validation
                </h4>
                <p className="text-sm text-gray-600 mb-4">
                  Run targeted research to validate this persona's goals, pain points, and feature preferences.
                </p>
                {onRunResearch ? (
                  <button
                    onClick={() => persona.id && onRunResearch(persona.id)}
                    className="w-full py-3 px-4 bg-[#009b87] hover:bg-[#007a6b] text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
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

              <div>
                <h4 className="text-xs font-semibold text-[#009b87] uppercase tracking-wide mb-3">Research History</h4>
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
                <h4 className="text-xs font-semibold text-[#009b87] uppercase tracking-wide mb-3 flex items-center gap-2">
                  <History className="w-4 h-4" /> Change History
                </h4>
                <p className="text-sm text-gray-600 mb-4">
                  View all changes made to this persona over time.
                </p>
              </div>
              <ChangeLogTimeline entityType="persona" entityId={persona.id} limit={20} />
            </div>
          )}
        </div>

        {/* Sticky Footer */}
        <div className="sticky bottom-0 bg-white border-t border-gray-200 p-6">
          {onConfirmationChange && persona.id && (
            <div className="mb-4">
              <div className="text-xs text-gray-500 mb-3">Actions</div>
              <div className="flex items-center gap-3">
                {isConfirmed() ? (
                  <>
                    <button
                      className="px-4 py-2 bg-[#009b87] text-white rounded-lg flex items-center gap-2"
                      disabled
                    >
                      <CheckCircle className="w-4 h-4" /> Confirmed
                    </button>
                    <button
                      onClick={handleRevertToDraft}
                      disabled={updating}
                      className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors flex items-center gap-2 disabled:opacity-50"
                    >
                      {updating ? <Loader2 className="w-4 h-4 animate-spin" /> : <RotateCcw className="w-4 h-4" />}
                      Revert to Draft
                    </button>
                    <button
                      onClick={() => setShowDeleteModal(true)}
                      className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors flex items-center gap-2"
                    >
                      <Trash2 className="w-4 h-4" />
                      Delete
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={() => handleConfirmationChange('confirmed_consultant')}
                      disabled={updating}
                      className="px-4 py-2 bg-[#009b87] text-white rounded-lg hover:bg-[#007a6b] transition-colors flex items-center gap-2 disabled:opacity-50"
                    >
                      {updating ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
                      Confirm
                    </button>
                    <button
                      onClick={() => handleConfirmationChange('needs_client')}
                      disabled={updating || persona.confirmation_status === 'needs_client'}
                      className={`px-4 py-2 border rounded-lg transition-colors flex items-center gap-2 ${
                        persona.confirmation_status === 'needs_client'
                          ? 'border-amber-400 bg-amber-50 text-amber-700'
                          : 'border-gray-300 text-gray-700 hover:bg-gray-50'
                      } disabled:opacity-50`}
                    >
                      <Clock className="w-4 h-4" />
                      Needs Review
                    </button>
                    <button
                      onClick={() => setShowDeleteModal(true)}
                      className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors flex items-center gap-2"
                    >
                      <Trash2 className="w-4 h-4" />
                      Delete
                    </button>
                  </>
                )}
              </div>
            </div>
          )}

          <button
            onClick={onClose}
            className="w-full px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Close
          </button>
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
    </>
  )
}
