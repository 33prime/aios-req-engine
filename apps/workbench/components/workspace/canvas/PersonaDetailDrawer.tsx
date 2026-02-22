/**
 * PersonaDetailDrawer - Right-slide drawer for persona details
 *
 * Opens when clicking a persona card in the canvas.
 * 4 tabs: Profile, Journey, Features, Gaps
 */

'use client'

import { useState, useEffect } from 'react'
import {
  User,
  CheckCircle,
  AlertCircle,
  Target,
  Footprints,
  Boxes,
  AlertTriangle,
} from 'lucide-react'
import { DrawerShell, type DrawerTab } from '@/components/ui/DrawerShell'
import { Spinner } from '@/components/ui/Spinner'
import { BRDStatusBadge } from '@/components/workspace/brd/components/StatusBadge'
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

const TABS: DrawerTab[] = [
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'journey', label: 'Journey', icon: Footprints },
  { id: 'features', label: 'Features', icon: Boxes },
  { id: 'gaps', label: 'Gaps', icon: AlertTriangle },
]

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

  return (
    <DrawerShell
      onClose={onClose}
      icon={User}
      entityLabel="Persona"
      title={persona?.name || 'Loading...'}
      headerExtra={
        persona?.role ? (
          <p className="text-[13px] text-[#999999] truncate mt-0.5">{persona.role}</p>
        ) : undefined
      }
      headerRight={
        <BRDStatusBadge status={persona?.confirmation_status} />
      }
      tabs={TABS}
      activeTab={activeTab}
      onTabChange={(id) => setActiveTab(id as TabId)}
    >
      {isLoading ? (
        <Spinner label="Loading persona..." />
      ) : !persona ? (
        <p className="text-[13px] text-[#999999] text-center py-8">
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
    </DrawerShell>
  )
}

function ProfileTab({ persona, coverage }: { persona: any; coverage: PersonaFeatureCoverage | null }) {
  return (
    <div className="space-y-5">
      {/* Description */}
      {persona.description && (
        <div>
          <h4 className="text-[13px] font-semibold text-[#333333] mb-1.5">Overview</h4>
          <p className="text-[13px] text-[#666666]">{persona.description}</p>
        </div>
      )}

      {/* Demographics */}
      {persona.demographics && Object.keys(persona.demographics).length > 0 && (
        <div>
          <h4 className="text-[13px] font-semibold text-[#333333] mb-2">Demographics</h4>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(persona.demographics).map(([key, value]) => (
              <div key={key} className="bg-[#F9F9F9] rounded-lg px-3 py-2">
                <span className="text-[11px] text-[#999999] capitalize">{key.replace(/_/g, ' ')}</span>
                <p className="text-[13px] text-[#666666]">{String(value)}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Psychographics */}
      {persona.psychographics && Object.keys(persona.psychographics).length > 0 && (
        <div>
          <h4 className="text-[13px] font-semibold text-[#333333] mb-2">Psychographics</h4>
          <div className="space-y-2">
            {Object.entries(persona.psychographics).map(([key, value]) => (
              <div key={key} className="bg-[#F9F9F9] rounded-lg px-3 py-2">
                <span className="text-[11px] text-[#999999] capitalize">{key.replace(/_/g, ' ')}</span>
                <p className="text-[13px] text-[#666666]">{String(value)}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Goals */}
      {persona.goals && persona.goals.length > 0 && (
        <div>
          <h4 className="text-[13px] font-semibold text-[#333333] mb-2">Goals</h4>
          <ul className="space-y-1.5">
            {persona.goals.map((goal: string, i: number) => {
              const isAddressed = coverage?.addressed_goals?.includes(goal)
              return (
                <li key={i} className="flex items-start gap-2 text-[13px]">
                  {isAddressed ? (
                    <CheckCircle className="w-4 h-4 text-[#3FAF7A] flex-shrink-0 mt-0.5" />
                  ) : (
                    <div className="w-4 h-4 rounded-full border-2 border-[#E5E5E5] flex-shrink-0 mt-0.5" />
                  )}
                  <span className="text-[#666666]">{goal}</span>
                </li>
              )
            })}
          </ul>
        </div>
      )}

      {/* Pain Points */}
      {persona.pain_points && persona.pain_points.length > 0 && (
        <div>
          <h4 className="text-[13px] font-semibold text-[#333333] mb-2">Pain Points</h4>
          <ul className="space-y-1.5">
            {persona.pain_points.map((pain: string, i: number) => (
              <li key={i} className="flex items-start gap-2 text-[13px] text-[#666666]">
                <AlertCircle className="w-4 h-4 text-[#999999] flex-shrink-0 mt-0.5" />
                {pain}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Type badge */}
      {persona.persona_type && (
        <div className="pt-2">
          <span className="inline-block px-2 py-0.5 text-xs font-semibold rounded-full bg-[#F9F9F9] text-[#666666] capitalize">
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
      <p className="text-[13px] text-[#999999] text-center py-8">
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
            className="bg-[#F9F9F9] rounded-lg p-4 border border-[#E5E5E5]"
          >
            <div className="flex items-center gap-2 mb-1.5">
              <span className="flex items-center justify-center w-6 h-6 rounded-full bg-[#3FAF7A] text-white text-[11px] font-bold">
                {step.step_index + 1}
              </span>
              <h4 className="text-[13px] font-semibold text-[#333333]">{step.title}</h4>
            </div>
            {step.description && (
              <p className="text-[13px] text-[#666666] mt-1">{step.description}</p>
            )}
            {step.features.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {step.features.map((f) => (
                  <span
                    key={f.id}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-[#E8F5E9] text-[#25785A]"
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
      <p className="text-[13px] text-[#999999] text-center py-8">
        No features linked to this persona&apos;s journey steps.
      </p>
    )
  }

  return (
    <div className="space-y-2">
      {features.map((f) => (
        <div
          key={f.id}
          className="flex items-start gap-3 bg-[#F9F9F9] rounded-lg p-3 border border-[#E5E5E5]"
        >
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-[13px] font-medium text-[#333333]">{f.name}</span>
              {f.is_mvp && (
                <span className="px-1.5 py-0.5 text-[10px] font-bold rounded bg-[#E8F5E9] text-[#25785A]">
                  MVP
                </span>
              )}
            </div>
            {f.description && (
              <p className="text-[13px] text-[#999999] mt-0.5 line-clamp-2">{f.description}</p>
            )}
          </div>
          <BRDStatusBadge status={f.confirmation_status} className="flex-shrink-0" />
        </div>
      ))}
    </div>
  )
}

function GapsTab({ coverage }: { coverage: PersonaFeatureCoverage | null }) {
  if (!coverage) {
    return (
      <p className="text-[13px] text-[#999999] text-center py-8">
        Coverage analysis not available. Run the DI Agent to generate coverage data.
      </p>
    )
  }

  const score = Math.round(coverage.coverage_score * 100)

  return (
    <div className="space-y-5">
      {/* Coverage Score */}
      <div className="bg-[#F9F9F9] rounded-lg p-4">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-[13px] font-semibold text-[#333333]">Coverage Score</h4>
          <span className={`text-[16px] font-bold ${score >= 70 ? 'text-[#3FAF7A]' : score >= 40 ? 'text-[#999999]' : 'text-red-600'}`}>
            {score}%
          </span>
        </div>
        <div className="h-2 bg-[#E5E5E5] rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${score >= 70 ? 'bg-[#3FAF7A]' : score >= 40 ? 'bg-[#999999]' : 'bg-red-500'}`}
            style={{ width: `${score}%` }}
          />
        </div>
      </div>

      {/* Unaddressed Goals */}
      {coverage.unaddressed_goals.length > 0 && (
        <div>
          <h4 className="text-[13px] font-semibold text-[#333333] mb-2">
            Unaddressed Goals ({coverage.unaddressed_goals.length})
          </h4>
          <ul className="space-y-1.5">
            {coverage.unaddressed_goals.map((goal, i) => (
              <li key={i} className="flex items-start gap-2 text-[13px] text-[#666666] bg-red-50 rounded-lg px-3 py-2">
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
          <h4 className="text-[13px] font-semibold text-[#333333] mb-2">
            Addressed Goals ({coverage.addressed_goals.length})
          </h4>
          <ul className="space-y-1.5">
            {coverage.addressed_goals.map((goal, i) => (
              <li key={i} className="flex items-start gap-2 text-[13px] text-[#666666] bg-[#E8F5E9] rounded-lg px-3 py-2">
                <CheckCircle className="w-4 h-4 text-[#3FAF7A] flex-shrink-0 mt-0.5" />
                {goal}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Feature Matches */}
      {coverage.feature_matches.length > 0 && (
        <div>
          <h4 className="text-[13px] font-semibold text-[#333333] mb-2">Feature Coverage</h4>
          <div className="space-y-2">
            {coverage.feature_matches.map((match, i) => (
              <div key={i} className="bg-[#F9F9F9] rounded-lg px-3 py-2">
                <p className="text-[13px] font-medium text-[#333333] mb-1">{match.goal}</p>
                <div className="flex flex-wrap gap-1">
                  {match.features.map((f) => (
                    <span
                      key={f.id}
                      className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-[#E8F5E9] text-[#25785A]"
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
