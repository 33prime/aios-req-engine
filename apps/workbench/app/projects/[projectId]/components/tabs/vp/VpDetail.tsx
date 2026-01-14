/**
 * VpDetail Component
 *
 * Detailed view of selected VP step matching the mockup design:
 * - Single bordered container with sections
 * - Emoji section headers
 * - Action buttons at bottom
 */

'use client'

import React, { useState } from 'react'
import { EmptyState } from '@/components/ui'
import { Markdown } from '@/components/ui/Markdown'
import {
  Zap,
  User,
  Bot,
  Plug,
  Check,
  AlertTriangle,
  ExternalLink,
  History,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import type { VpStep, VpEvidence } from '@/types/api'
import ChangeLogTimeline from '@/components/revisions/ChangeLogTimeline'

interface VpDetailProps {
  step: VpStep | null
  onStatusUpdate: (stepId: string, newStatus: string) => Promise<void>
  onViewEvidence: (chunkId: string) => void
  updating?: boolean
}

// Calculate value rating (stars)
function getValueRating(step: VpStep): { stars: number; label: string } {
  const hasHighValue = step.value_created && step.value_created.length > 100
  const hasEvidence = step.evidence && step.evidence.length > 0
  const hasFeatures = step.features_used && step.features_used.length >= 2

  let stars = 1
  if (hasHighValue) stars++
  if (hasEvidence) stars++
  if (hasFeatures && stars < 3) stars++

  const label = stars >= 3 ? 'High' : stars >= 2 ? 'Medium' : 'Low'
  return { stars, label }
}

// Extract actors from step
function getActors(step: VpStep) {
  const humanActors: { name: string; role: string }[] = []
  const systemActors: { name: string; role: string }[] = []

  // Primary persona
  if (step.actor_persona_name || step.actor_persona_id) {
    humanActors.push({
      name: step.actor_persona_name || 'User',
      role: 'initiates'
    })
  }

  // Detect system actors from narrative
  const narrative = step.narrative_system?.toLowerCase() || ''

  if (narrative.includes('ai') || narrative.includes('nlp') || narrative.includes('machine learning')) {
    systemActors.push({ name: 'AI Engine', role: 'processes' })
  }

  if (narrative.includes('api') || narrative.includes('external service')) {
    systemActors.push({ name: 'External API', role: 'integrates' })
  }

  // Integrations as system actors
  if (step.integrations_triggered && step.integrations_triggered.length > 0) {
    step.integrations_triggered.forEach(integration => {
      if (!systemActors.find(a => a.name === integration)) {
        systemActors.push({ name: integration, role: 'triggered' })
      }
    })
  }

  return { humanActors, systemActors }
}

export function VpDetail({ step, onStatusUpdate, onViewEvidence, updating = false }: VpDetailProps) {
  const [showEvidence, setShowEvidence] = useState(true)
  const [showHistory, setShowHistory] = useState(false)

  if (!step) {
    return (
      <EmptyState
        icon={<Zap className="h-16 w-16" />}
        title="No Step Selected"
        description="Select a Value Path step from the list to view details."
      />
    )
  }

  const confirmationStatus = step.confirmation_status || step.status
  const isConfirmed = confirmationStatus === 'confirmed_consultant' || confirmationStatus === 'confirmed_client'
  const statusText = isConfirmed ? 'Confirmed' : confirmationStatus === 'needs_client' ? 'Needs Client' : 'Draft'
  const statusIcon = isConfirmed ? '✓' : '○'

  const { humanActors, systemActors } = getActors(step)
  const allActors = [...humanActors, ...systemActors]
  const { stars, label: valueLabel } = getValueRating(step)
  const evidenceItems = step.evidence || []

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden bg-white">
      {/* Header */}
      <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
          Step Detail
        </h3>
        <div className="mt-1 flex items-center gap-2 flex-wrap">
          <span className="text-lg font-medium text-gray-900">
            Step {step.step_index}: {step.label}
          </span>
          <span className={`text-sm ${isConfirmed ? 'text-green-600' : 'text-gray-400'}`}>
            {statusIcon} {statusText}
          </span>
        </div>
      </div>

      {/* Content sections */}
      <div className="p-4 space-y-5">

        {/* ACTORS */}
        {allActors.length > 0 && (
          <section>
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
              👤 Actors
            </h4>
            <div className="flex flex-wrap items-center gap-4">
              {humanActors.map((actor, idx) => (
                <div key={`human-${idx}`} className="flex items-center gap-2">
                  <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                    <User className="w-4 h-4 text-blue-600" />
                  </div>
                  <span className="text-sm text-gray-700">
                    {actor.name} <span className="text-gray-400">({actor.role})</span>
                  </span>
                </div>
              ))}
              {systemActors.map((actor, idx) => (
                <div key={`system-${idx}`} className="flex items-center gap-2">
                  <div className="w-8 h-8 bg-slate-100 rounded-full flex items-center justify-center">
                    {actor.name.toLowerCase().includes('ai') || actor.name.toLowerCase().includes('engine') ? (
                      <Bot className="w-4 h-4 text-slate-500" />
                    ) : (
                      <Plug className="w-4 h-4 text-slate-500" />
                    )}
                  </div>
                  <span className="text-sm text-gray-500">
                    {actor.name} <span className="text-gray-400">({actor.role})</span>
                  </span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* USER EXPERIENCE */}
        {step.narrative_user && (
          <section>
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
              📖 User Experience
            </h4>
            <div className="border border-gray-200 rounded-lg p-3 bg-gray-50">
              <div className="prose prose-sm max-w-none text-gray-700">
                <Markdown content={step.narrative_user} />
              </div>
            </div>
          </section>
        )}

        {/* BEHIND THE SCENES */}
        {step.narrative_system && (
          <section>
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
              ⚙️ Behind the Scenes
            </h4>
            <div className="border border-gray-200 rounded-lg p-3 bg-gray-50">
              <div className="prose prose-sm max-w-none text-gray-700">
                <Markdown content={step.narrative_system} />
              </div>
            </div>
          </section>
        )}

        {/* FEATURES */}
        {step.features_used && step.features_used.length > 0 && (
          <section>
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
              Features
            </h4>
            <div className="flex flex-wrap gap-3">
              {step.features_used.map((feature, idx) => (
                <div key={idx} className="text-center">
                  <span className="inline-block px-3 py-1.5 bg-gray-100 border border-gray-200 rounded-lg text-sm text-gray-700">
                    {feature.feature_name}
                  </span>
                  {feature.role === 'core' && (
                    <div className="text-xs text-gray-400 mt-1">core</div>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {/* VALUE CREATED */}
        {step.value_created && (
          <section>
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-2">
              Value Created
              <span className="text-amber-400">
                {[1, 2, 3].map(i => (
                  <span key={i} className={i <= stars ? '' : 'opacity-30'}>★</span>
                ))}
              </span>
              <span className="text-amber-600 text-xs font-normal">{valueLabel}</span>
            </h4>
            <p className="text-sm text-gray-700">"{step.value_created}"</p>
          </section>
        )}

        {/* EVIDENCE */}
        {evidenceItems.length > 0 && (
          <section>
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                Evidence ({evidenceItems.length})
              </h4>
              <button
                onClick={() => setShowEvidence(!showEvidence)}
                className="text-xs text-blue-600 hover:text-blue-800"
              >
                {showEvidence ? 'Hide' : 'Show'}
              </button>
            </div>

            {showEvidence && (
              <div className="space-y-2">
                {evidenceItems.map((evidence: VpEvidence, idx: number) => (
                  <div
                    key={idx}
                    className={`border rounded-lg p-3 ${
                      evidence.source_type === 'signal'
                        ? 'bg-green-50 border-green-200'
                        : evidence.source_type === 'research'
                          ? 'bg-blue-50 border-blue-200'
                          : 'bg-gray-50 border-gray-200'
                    }`}
                  >
                    <div className="flex items-start gap-2 mb-1">
                      <span className={`text-xs px-2 py-0.5 rounded font-medium ${
                        evidence.source_type === 'signal'
                          ? 'bg-green-100 text-green-700'
                          : evidence.source_type === 'research'
                            ? 'bg-blue-100 text-blue-700'
                            : 'bg-gray-100 text-gray-600'
                      }`}>
                        {evidence.source_type}
                      </span>
                    </div>
                    <p className="text-sm text-gray-700 italic mb-1">
                      "{evidence.excerpt}"
                    </p>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-500">{evidence.rationale}</span>
                      {evidence.chunk_id && (
                        <button
                          onClick={() => onViewEvidence(evidence.chunk_id!)}
                          className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"
                        >
                          View source <ExternalLink className="h-3 w-3" />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {/* Legacy Description (fallback for non-V2) */}
        {!step.narrative_user && !step.narrative_system && step.description && (
          <section>
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
              Description
            </h4>
            <p className="text-sm text-gray-700">{step.description}</p>
          </section>
        )}

        {/* ACTION BUTTONS */}
        <div className="pt-4 border-t border-gray-200 flex gap-3">
          <button
            onClick={() => onStatusUpdate(step.id, 'confirmed_consultant')}
            disabled={updating || confirmationStatus === 'confirmed_consultant'}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors
              ${confirmationStatus === 'confirmed_consultant'
                ? 'bg-green-100 text-green-800 border border-green-300'
                : 'bg-green-50 text-green-700 border border-green-200 hover:bg-green-100'
              }
              ${updating ? 'opacity-50 cursor-not-allowed' : ''}
            `}
          >
            <Check className="w-4 h-4" /> Confirm
          </button>
          <button
            onClick={() => onStatusUpdate(step.id, 'needs_client')}
            disabled={updating || confirmationStatus === 'needs_client'}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors
              ${confirmationStatus === 'needs_client'
                ? 'bg-amber-100 text-amber-800 border border-amber-300'
                : 'bg-amber-50 text-amber-700 border border-amber-200 hover:bg-amber-100'
              }
              ${updating ? 'opacity-50 cursor-not-allowed' : ''}
            `}
          >
            <AlertTriangle className="w-4 h-4" /> Needs Client Review
          </button>
        </div>

        {/* CHANGE HISTORY */}
        <section className="pt-4 border-t border-gray-200">
          <button
            onClick={() => setShowHistory(!showHistory)}
            className="flex items-center text-xs font-semibold text-gray-500 uppercase tracking-wide hover:text-blue-600"
          >
            <History className="h-4 w-4 mr-1" />
            Change History
            {showHistory ? <ChevronUp className="h-4 w-4 ml-1" /> : <ChevronDown className="h-4 w-4 ml-1" />}
          </button>

          {showHistory && (
            <div className="mt-4">
              <ChangeLogTimeline entityType="vp_step" entityId={step.id} limit={10} />
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
