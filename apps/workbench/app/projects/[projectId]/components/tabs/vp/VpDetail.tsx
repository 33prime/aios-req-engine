/**
 * VpDetail Component
 *
 * Detailed view of selected VP step with refined styling:
 * - Teal section headers
 * - Blue User Experience box
 * - Gray System Behavior with bullet points
 * - Two-column Features/Value grid
 * - Green-bordered evidence
 * - Footer action bar
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
  Clock,
  MessageSquare,
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

// Get initials from name
function getInitials(name: string): string {
  return name
    .split(' ')
    .map((word) => word[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
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

  const label = stars >= 3 ? 'HIGH' : stars >= 2 ? 'MEDIUM' : 'LOW'
  return { stars, label }
}

// Extract actors from step
function getActors(step: VpStep) {
  const humanActors: { name: string; role: string; initials: string }[] = []
  const systemActors: { name: string; role: string }[] = []

  // Primary persona
  if (step.actor_persona_name || step.actor_persona_id) {
    const name = step.actor_persona_name || 'User'
    humanActors.push({
      name,
      role: 'initiates',
      initials: getInitials(name),
    })
  }

  // Detect system actors from narrative
  const narrative = step.narrative_system?.toLowerCase() || ''

  if (narrative.includes('ai') || narrative.includes('nlp') || narrative.includes('machine learning') || narrative.includes('engine')) {
    systemActors.push({ name: 'AI Engine', role: 'processes' })
  }

  if (narrative.includes('api') || narrative.includes('external service')) {
    systemActors.push({ name: 'External API', role: 'integrates' })
  }

  // Integrations as system actors
  if (step.integrations_triggered && step.integrations_triggered.length > 0) {
    step.integrations_triggered.forEach((integration) => {
      if (!systemActors.find((a) => a.name === integration)) {
        systemActors.push({ name: integration, role: 'triggered' })
      }
    })
  }

  return { humanActors, systemActors }
}

// Parse narrative into bullet points if it contains multiple sentences
function parseToBullets(text: string): string[] {
  if (!text) return []
  // Split by sentence-ending punctuation followed by space, or by newlines
  const sentences = text.split(/(?<=[.!?])\s+|\n+/).filter((s) => s.trim())
  return sentences
}

export function VpDetail({ step, onStatusUpdate, onViewEvidence, updating = false }: VpDetailProps) {
  const [showHistory, setShowHistory] = useState(false)

  if (!step) {
    return (
      <EmptyState
        icon={<Zap className="h-16 w-16" />}
        title="No Step Selected"
        description="Select a Value Path step from the journey flow to view details."
      />
    )
  }

  const confirmationStatus = step.confirmation_status || step.status
  const isConfirmed = confirmationStatus === 'confirmed_consultant' || confirmationStatus === 'confirmed_client'
  const needsClient = confirmationStatus === 'needs_client'

  const { humanActors, systemActors } = getActors(step)
  const { stars, label: valueLabel } = getValueRating(step)
  const evidenceItems = step.evidence || []
  const systemBullets = parseToBullets(step.narrative_system || '')

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-semibold text-gray-900">
              Step {step.step_index}: {step.label}
            </h2>
            {isConfirmed && (
              <span className="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800 flex items-center gap-1">
                <Check className="w-3 h-3" />
                Confirmed
              </span>
            )}
            {needsClient && (
              <span className="px-2 py-1 text-xs font-medium rounded-full bg-yellow-100 text-yellow-800 flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" />
                Needs Client
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-6 space-y-6">
        {/* Actors Section */}
        {(humanActors.length > 0 || systemActors.length > 0) && (
          <div>
            <h3 className="text-xs font-semibold text-[#009b87] uppercase tracking-wide mb-3">
              Actors
            </h3>
            <div className="flex items-center gap-3 flex-wrap">
              {humanActors.map((actor, idx) => (
                <div
                  key={`human-${idx}`}
                  className="flex items-center gap-2 px-3 py-2 bg-emerald-50 rounded-lg border border-emerald-200"
                >
                  <div className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center text-xs font-medium text-emerald-700">
                    {actor.initials}
                  </div>
                  <div>
                    <div className="text-sm font-medium text-gray-900">{actor.name}</div>
                    <div className="text-xs text-gray-500">({actor.role})</div>
                  </div>
                </div>
              ))}
              {systemActors.map((actor, idx) => (
                <div
                  key={`system-${idx}`}
                  className="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-lg border border-gray-200"
                >
                  <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center">
                    {actor.name.toLowerCase().includes('ai') || actor.name.toLowerCase().includes('engine') ? (
                      <Bot className="w-4 h-4 text-gray-500" />
                    ) : (
                      <Plug className="w-4 h-4 text-gray-500" />
                    )}
                  </div>
                  <div>
                    <div className="text-sm font-medium text-gray-700">{actor.name}</div>
                    <div className="text-xs text-gray-500">({actor.role})</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* User Experience Section */}
        {step.narrative_user && (
          <div>
            <h3 className="text-xs font-semibold text-[#009b87] uppercase tracking-wide mb-3">
              User Experience
            </h3>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-sm text-gray-700 leading-relaxed">
                {step.narrative_user}
              </p>
            </div>
          </div>
        )}

        {/* System Behavior Section */}
        {step.narrative_system && (
          <div>
            <h3 className="text-xs font-semibold text-[#009b87] uppercase tracking-wide mb-3">
              System Behavior
            </h3>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              {systemBullets.length > 1 ? (
                <div className="text-sm text-gray-700 space-y-2">
                  {systemBullets.map((bullet, idx) => (
                    <div key={idx} className="flex items-start">
                      <span className="text-[#009b87] mr-2 mt-0.5">•</span>
                      <span>{bullet}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-700">{step.narrative_system}</p>
              )}
            </div>
          </div>
        )}

        {/* Features & Value - Two Column Grid */}
        {((step.features_used?.length ?? 0) > 0 || step.value_created) && (
          <div className="grid grid-cols-2 gap-6">
            {/* Features */}
            {step.features_used && step.features_used.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold text-[#009b87] uppercase tracking-wide mb-3">
                  Features
                </h3>
                <div className="space-y-2">
                  {step.features_used.map((feature, idx) => (
                    <div
                      key={idx}
                      className="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-lg border border-gray-200"
                    >
                      <MessageSquare className="w-4 h-4 text-gray-500" />
                      <span className="text-sm font-medium text-gray-700">{feature.feature_name}</span>
                      {feature.role === 'core' && (
                        <span className="ml-auto text-xs px-2 py-0.5 bg-[#009b87] text-white rounded">
                          core
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Value Created */}
            {step.value_created && (
              <div>
                <h3 className="text-xs font-semibold text-[#009b87] uppercase tracking-wide mb-3">
                  Value Created
                </h3>
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                  <div className="flex items-start gap-2 mb-2">
                    <div className="text-yellow-500 text-sm">
                      {[1, 2, 3].map((i) => (
                        <span key={i} className={i <= stars ? '' : 'opacity-30'}>
                          ★
                        </span>
                      ))}
                    </div>
                    <span className="text-xs font-semibold text-yellow-800">{valueLabel} VALUE</span>
                  </div>
                  <p className="text-xs text-yellow-700 italic">"{step.value_created}"</p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Evidence Section */}
        {evidenceItems.length > 0 && (
          <div>
            <h3 className="text-xs font-semibold text-[#009b87] uppercase tracking-wide mb-3">
              Evidence
            </h3>
            <div className="space-y-3">
              {evidenceItems.map((evidence: VpEvidence, idx: number) => (
                <div
                  key={idx}
                  className={`border-l-4 p-4 rounded-r-lg ${
                    evidence.source_type === 'signal'
                      ? 'border-green-500 bg-green-50'
                      : evidence.source_type === 'research'
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-300 bg-gray-50'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0">
                      <span
                        className={`inline-flex items-center px-2 py-1 text-xs font-medium rounded ${
                          evidence.source_type === 'signal'
                            ? 'bg-green-100 text-green-800'
                            : evidence.source_type === 'research'
                              ? 'bg-blue-100 text-blue-800'
                              : 'bg-gray-100 text-gray-700'
                        }`}
                      >
                        {evidence.source_type === 'signal' ? 'Signal' : evidence.source_type === 'research' ? 'Research' : 'Inferred'}
                      </span>
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900 mb-1">"{evidence.excerpt}"</p>
                      <p className="text-xs text-gray-600">{evidence.rationale}</p>
                      {evidence.chunk_id && (
                        <button
                          onClick={() => onViewEvidence(evidence.chunk_id!)}
                          className="mt-2 text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"
                        >
                          View source <ExternalLink className="h-3 w-3" />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Legacy Description (fallback for non-V2 steps) */}
        {!step.narrative_user && !step.narrative_system && step.description && (
          <div>
            <h3 className="text-xs font-semibold text-[#009b87] uppercase tracking-wide mb-3">
              Description
            </h3>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              <p className="text-sm text-gray-700">{step.description}</p>
            </div>
          </div>
        )}
      </div>

      {/* Actions Footer */}
      <div className="p-6 border-t border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between">
          <button
            onClick={() => setShowHistory(!showHistory)}
            className="text-sm text-gray-600 hover:text-gray-900 transition-colors flex items-center gap-1"
          >
            <Clock className="w-4 h-4" />
            Change History
            {showHistory ? <ChevronUp className="w-4 h-4 ml-1" /> : <ChevronDown className="w-4 h-4 ml-1" />}
          </button>
          <div className="flex items-center gap-3">
            <button
              onClick={() => onStatusUpdate(step.id, 'needs_client')}
              disabled={updating || needsClient}
              className={`px-4 py-2 border rounded-lg transition-colors flex items-center gap-2 ${
                needsClient
                  ? 'border-yellow-400 bg-yellow-50 text-yellow-700'
                  : 'border-yellow-500 text-yellow-700 hover:bg-yellow-50'
              } ${updating ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <AlertTriangle className="w-4 h-4" />
              Needs Client Review
            </button>
            <button
              onClick={() => onStatusUpdate(step.id, 'confirmed_consultant')}
              disabled={updating || isConfirmed}
              className={`px-4 py-2 rounded-lg transition-colors flex items-center gap-2 ${
                isConfirmed
                  ? 'bg-green-100 text-green-800'
                  : 'bg-[#009b87] text-white hover:bg-[#007a6b]'
              } ${updating ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <Check className="w-4 h-4" />
              Confirm
            </button>
          </div>
        </div>

        {/* Change History Dropdown */}
        {showHistory && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            <ChangeLogTimeline entityType="vp_step" entityId={step.id} limit={10} />
          </div>
        )}
      </div>
    </div>
  )
}
