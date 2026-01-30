/**
 * PersonaDetailDrawer - Right-slide drawer for persona details
 *
 * Opens when clicking a persona card in the canvas.
 * 4 tabs: Profile, Journey, Features, Gaps
 */

'use client'

import { useState, useEffect } from 'react'
import {
  X,
  User,
  CheckCircle,
  AlertCircle,
  Target,
  Footprints,
  Boxes,
  AlertTriangle,
} from 'lucide-react'
import {
  getPersonas,
  getPersonaCoverage,
} from '@/lib/api'
import type { PersonaFeatureCoverage } from '@/lib/api'
import type { CanvasData, VpStepSummary, FeatureSummary } from '@/types/workspace'

interface PersonaDetailDrawerProps {
  personaId: string
  projectId: string
  canvasData: CanvasData
  onClose: () => void
}

type TabId = 'profile' | 'journey' | 'features' | 'gaps'

const TABS: { id: TabId; label: string; icon: typeof Target }[] = [
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'journey', label: 'Journey', icon: Footprints },
  { id: 'features', label: 'Features', icon: Boxes },
  { id: 'gaps', label: 'Gaps', icon: AlertTriangle },
]

function getStatusBadge(status?: string | null) {
  switch (status) {
    case 'confirmed_client':
      return { label: 'Client Confirmed', color: 'bg-green-100 text-green-700', icon: CheckCircle }
    case 'confirmed_consultant':
      return { label: 'Confirmed', color: 'bg-blue-100 text-blue-700', icon: CheckCircle }
    case 'needs_client':
    case 'needs_confirmation':
      return { label: 'Needs Review', color: 'bg-amber-100 text-amber-700', icon: AlertCircle }
    default:
      return { label: 'AI Generated', color: 'bg-gray-100 text-gray-600', icon: AlertCircle }
  }
}

export function PersonaDetailDrawer({
  personaId,
  projectId,
  canvasData,
  onClose,
}: PersonaDetailDrawerProps) {
  const [activeTab, setActiveTab] = useState<TabId>('profile')
  const [persona, setPersona] = useState<any | null>(null)
  const [coverage, setCoverage] = useState<PersonaFeatureCoverage | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Related data from canvas
  const relatedSteps = canvasData.vp_steps.filter(
    (s) => s.actor_persona_id === personaId
  )
  const relatedFeatureIds = new Set(
    relatedSteps.flatMap((s) => s.features.map((f) => f.id))
  )
  const relatedFeatures = canvasData.features.filter((f) => relatedFeatureIds.has(f.id))

  useEffect(() => {
    setIsLoading(true)
    Promise.all([
      getPersonas(projectId).catch(() => []),
      getPersonaCoverage(personaId).catch(() => null),
    ])
      .then(([personas, cov]) => {
        const found = personas.find((p: any) => p.id === personaId)
        setPersona(found || null)
        setCoverage(cov)
      })
      .finally(() => setIsLoading(false))
  }, [projectId, personaId])

  const statusBadge = getStatusBadge(persona?.confirmation_status)
  const StatusIcon = statusBadge.icon

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 z-40"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-[560px] max-w-[calc(100vw-80px)] bg-white shadow-xl z-50 flex flex-col animate-slide-in-right">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-ui-cardBorder">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-10 h-10 rounded-full bg-brand-teal/10 flex items-center justify-center flex-shrink-0">
              <User className="w-5 h-5 text-brand-teal" />
            </div>
            <div className="min-w-0">
              <h2 className="text-lg font-semibold text-ui-headingDark truncate">
                {persona?.name || 'Loading...'}
              </h2>
              {persona?.role && (
                <p className="text-sm text-ui-supportText truncate">{persona.role}</p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium ${statusBadge.color}`}>
              <StatusIcon className="w-3 h-3" />
              {statusBadge.label}
            </span>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-ui-supportText hover:bg-ui-background hover:text-ui-headingDark transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-ui-cardBorder px-6">
          {TABS.map((tab) => {
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 px-3 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-brand-teal text-brand-teal'
                    : 'border-transparent text-ui-supportText hover:text-ui-headingDark'
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            )
          })}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-teal" />
            </div>
          ) : !persona ? (
            <p className="text-sm text-ui-supportText text-center py-8">
              Persona data not available.
            </p>
          ) : (
            <>
              {activeTab === 'profile' && (
                <ProfileTab persona={persona} coverage={coverage} />
              )}
              {activeTab === 'journey' && (
                <JourneyTab steps={relatedSteps} personaName={persona.name} />
              )}
              {activeTab === 'features' && (
                <FeaturesTab features={relatedFeatures} />
              )}
              {activeTab === 'gaps' && (
                <GapsTab coverage={coverage} />
              )}
            </>
          )}
        </div>
      </div>
    </>
  )
}

function ProfileTab({ persona, coverage }: { persona: any; coverage: PersonaFeatureCoverage | null }) {
  return (
    <div className="space-y-5">
      {/* Description */}
      {persona.description && (
        <div>
          <h4 className="text-sm font-semibold text-ui-headingDark mb-1.5">Overview</h4>
          <p className="text-sm text-ui-bodyText">{persona.description}</p>
        </div>
      )}

      {/* Demographics */}
      {persona.demographics && Object.keys(persona.demographics).length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-ui-headingDark mb-2">Demographics</h4>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(persona.demographics).map(([key, value]) => (
              <div key={key} className="bg-ui-background rounded-lg px-3 py-2">
                <span className="text-[11px] text-ui-supportText capitalize">{key.replace(/_/g, ' ')}</span>
                <p className="text-sm text-ui-bodyText">{String(value)}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Psychographics */}
      {persona.psychographics && Object.keys(persona.psychographics).length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-ui-headingDark mb-2">Psychographics</h4>
          <div className="space-y-2">
            {Object.entries(persona.psychographics).map(([key, value]) => (
              <div key={key} className="bg-ui-background rounded-lg px-3 py-2">
                <span className="text-[11px] text-ui-supportText capitalize">{key.replace(/_/g, ' ')}</span>
                <p className="text-sm text-ui-bodyText">{String(value)}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Goals */}
      {persona.goals && persona.goals.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-ui-headingDark mb-2">Goals</h4>
          <ul className="space-y-1.5">
            {persona.goals.map((goal: string, i: number) => {
              const isAddressed = coverage?.addressed_goals?.includes(goal)
              return (
                <li key={i} className="flex items-start gap-2 text-sm">
                  {isAddressed ? (
                    <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
                  ) : (
                    <div className="w-4 h-4 rounded-full border-2 border-gray-300 flex-shrink-0 mt-0.5" />
                  )}
                  <span className="text-ui-bodyText">{goal}</span>
                </li>
              )
            })}
          </ul>
        </div>
      )}

      {/* Pain Points */}
      {persona.pain_points && persona.pain_points.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-ui-headingDark mb-2">Pain Points</h4>
          <ul className="space-y-1.5">
            {persona.pain_points.map((pain: string, i: number) => (
              <li key={i} className="flex items-start gap-2 text-sm text-ui-bodyText">
                <AlertCircle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
                {pain}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Type badge */}
      {persona.persona_type && (
        <div className="pt-2">
          <span className="inline-block px-2 py-0.5 text-badge rounded-full bg-ui-background text-ui-bodyText capitalize">
            {persona.persona_type.replace('_', ' ')}
          </span>
        </div>
      )}
    </div>
  )
}

function JourneyTab({ steps, personaName }: { steps: VpStepSummary[]; personaName: string }) {
  if (steps.length === 0) {
    return (
      <p className="text-sm text-ui-supportText text-center py-8">
        No journey steps assigned to {personaName}.
      </p>
    )
  }

  return (
    <div className="space-y-3">
      {steps
        .sort((a, b) => a.step_index - b.step_index)
        .map((step) => (
          <div
            key={step.id}
            className="bg-ui-background rounded-lg p-4 border border-ui-cardBorder"
          >
            <div className="flex items-center gap-2 mb-1.5">
              <span className="flex items-center justify-center w-6 h-6 rounded-full bg-brand-teal text-white text-xs font-bold">
                {step.step_index + 1}
              </span>
              <h4 className="text-sm font-semibold text-ui-headingDark">{step.title}</h4>
            </div>
            {step.description && (
              <p className="text-sm text-ui-bodyText mt-1">{step.description}</p>
            )}
            {step.features.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {step.features.map((f) => (
                  <span
                    key={f.id}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-brand-teal/10 text-brand-teal"
                  >
                    {f.name}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
    </div>
  )
}

function FeaturesTab({ features }: { features: FeatureSummary[] }) {
  if (features.length === 0) {
    return (
      <p className="text-sm text-ui-supportText text-center py-8">
        No features linked to this persona&apos;s journey steps.
      </p>
    )
  }

  return (
    <div className="space-y-2">
      {features.map((f) => {
        const badge = getStatusBadge(f.confirmation_status)
        const BadgeIcon = badge.icon
        return (
          <div
            key={f.id}
            className="flex items-start gap-3 bg-ui-background rounded-lg p-3 border border-ui-cardBorder"
          >
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-ui-headingDark">{f.name}</span>
                {f.is_mvp && (
                  <span className="px-1.5 py-0.5 text-[10px] font-bold rounded bg-amber-100 text-amber-700">
                    MVP
                  </span>
                )}
              </div>
              {f.description && (
                <p className="text-sm text-ui-supportText mt-0.5 line-clamp-2">{f.description}</p>
              )}
            </div>
            <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-medium flex-shrink-0 ${badge.color}`}>
              <BadgeIcon className="w-3 h-3" />
            </span>
          </div>
        )
      })}
    </div>
  )
}

function GapsTab({ coverage }: { coverage: PersonaFeatureCoverage | null }) {
  if (!coverage) {
    return (
      <p className="text-sm text-ui-supportText text-center py-8">
        Coverage analysis not available. Run the DI Agent to generate coverage data.
      </p>
    )
  }

  const score = Math.round(coverage.coverage_score * 100)

  return (
    <div className="space-y-5">
      {/* Coverage Score */}
      <div className="bg-ui-background rounded-lg p-4">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-sm font-semibold text-ui-headingDark">Coverage Score</h4>
          <span className={`text-lg font-bold ${score >= 70 ? 'text-green-600' : score >= 40 ? 'text-amber-600' : 'text-red-600'}`}>
            {score}%
          </span>
        </div>
        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${score >= 70 ? 'bg-green-500' : score >= 40 ? 'bg-amber-500' : 'bg-red-500'}`}
            style={{ width: `${score}%` }}
          />
        </div>
      </div>

      {/* Unaddressed Goals */}
      {coverage.unaddressed_goals.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-ui-headingDark mb-2">
            Unaddressed Goals ({coverage.unaddressed_goals.length})
          </h4>
          <ul className="space-y-1.5">
            {coverage.unaddressed_goals.map((goal, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-ui-bodyText bg-red-50 rounded-lg px-3 py-2">
                <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                {goal}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Addressed Goals */}
      {coverage.addressed_goals.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-ui-headingDark mb-2">
            Addressed Goals ({coverage.addressed_goals.length})
          </h4>
          <ul className="space-y-1.5">
            {coverage.addressed_goals.map((goal, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-ui-bodyText bg-green-50 rounded-lg px-3 py-2">
                <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
                {goal}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Feature Matches */}
      {coverage.feature_matches.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-ui-headingDark mb-2">Feature Coverage</h4>
          <div className="space-y-2">
            {coverage.feature_matches.map((match, i) => (
              <div key={i} className="bg-ui-background rounded-lg px-3 py-2">
                <p className="text-sm font-medium text-ui-headingDark mb-1">{match.goal}</p>
                <div className="flex flex-wrap gap-1">
                  {match.features.map((f) => (
                    <span
                      key={f.id}
                      className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-brand-teal/10 text-brand-teal"
                    >
                      {f.name}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default PersonaDetailDrawer
