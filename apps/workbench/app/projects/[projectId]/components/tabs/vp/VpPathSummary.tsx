/**
 * VpPathSummary Component
 *
 * Right sidebar showing path-level insights:
 * - Actors across entire path (humans above, systems below)
 * - Confirmation progress
 * - Evidence strength
 * - Value moments by rating
 * - Gaps and warnings
 */

'use client'

import React from 'react'
import {
  User,
  Bot,
  Plug,
  CheckCircle,
  AlertTriangle,
  FileText,
  Sparkles
} from 'lucide-react'
import type { VpStep } from '@/types/api'

interface VpPathSummaryProps {
  steps: VpStep[]
  onSelectStep?: (stepId: string) => void
}

interface ActorSummary {
  name: string
  type: 'human' | 'system'
  stepCount: number
  stepIndices: number[]
}

export function VpPathSummary({ steps, onSelectStep }: VpPathSummaryProps) {
  // Calculate actors across all steps
  const getActorsSummary = (): ActorSummary[] => {
    const actorMap = new Map<string, ActorSummary>()

    steps.forEach(step => {
      // Human actors (personas)
      const personaName = step.actor_persona_name || 'User'
      if (!actorMap.has(personaName)) {
        actorMap.set(personaName, {
          name: personaName,
          type: 'human',
          stepCount: 0,
          stepIndices: []
        })
      }
      const persona = actorMap.get(personaName)!
      persona.stepCount++
      persona.stepIndices.push(step.step_index)

      // System actors (detect from narrative/integrations)
      const narrative = step.narrative_system?.toLowerCase() || ''

      if (narrative.includes('ai') || narrative.includes('nlp') || narrative.includes('engine')) {
        if (!actorMap.has('AI Engine')) {
          actorMap.set('AI Engine', { name: 'AI Engine', type: 'system', stepCount: 0, stepIndices: [] })
        }
        const ai = actorMap.get('AI Engine')!
        ai.stepCount++
        ai.stepIndices.push(step.step_index)
      }

      if (step.integrations_triggered && step.integrations_triggered.length > 0) {
        step.integrations_triggered.forEach(integration => {
          const key = integration.length > 15 ? integration.slice(0, 15) + '...' : integration
          if (!actorMap.has(key)) {
            actorMap.set(key, { name: key, type: 'system', stepCount: 0, stepIndices: [] })
          }
          const actor = actorMap.get(key)!
          actor.stepCount++
          if (!actor.stepIndices.includes(step.step_index)) {
            actor.stepIndices.push(step.step_index)
          }
        })
      }
    })

    // Sort: humans first, then by step count
    return Array.from(actorMap.values()).sort((a, b) => {
      if (a.type !== b.type) return a.type === 'human' ? -1 : 1
      return b.stepCount - a.stepCount
    })
  }

  // Calculate confirmation progress
  const getProgress = () => {
    const confirmed = steps.filter(s => {
      const status = s.confirmation_status || s.status
      return status === 'confirmed_consultant' || status === 'confirmed_client'
    }).length
    return { confirmed, total: steps.length }
  }

  // Calculate evidence strength
  const getEvidenceStrength = () => {
    let signalBacked = 0
    let inferred = 0

    steps.forEach(step => {
      if (step.evidence) {
        step.evidence.forEach(e => {
          if (e.source_type === 'signal') signalBacked++
          else inferred++
        })
      }
    })

    return { signalBacked, inferred, total: signalBacked + inferred }
  }

  // Get value moments grouped by rating
  const getValueMoments = () => {
    const high: number[] = []
    const medium: number[] = []
    const low: number[] = []

    steps.forEach(step => {
      const hasHighValue = step.value_created && step.value_created.length > 100
      const hasEvidence = step.evidence && step.evidence.length > 0
      const hasFeatures = step.features_used && step.features_used.length >= 2

      let stars = 1
      if (hasHighValue) stars++
      if (hasEvidence) stars++
      if (hasFeatures && stars < 3) stars++

      if (stars >= 3) high.push(step.step_index)
      else if (stars >= 2) medium.push(step.step_index)
      else low.push(step.step_index)
    })

    return { high, medium, low }
  }

  // Get gaps and warnings
  const getGaps = () => {
    const gaps: { stepIndex: number; stepId: string; issue: string }[] = []

    steps.forEach(step => {
      const status = step.confirmation_status || step.status

      if (!step.evidence || step.evidence.length === 0) {
        gaps.push({ stepIndex: step.step_index, stepId: step.id, issue: 'no evidence' })
      }

      if (status === 'needs_client') {
        gaps.push({ stepIndex: step.step_index, stepId: step.id, issue: 'needs client' })
      }

      if (step.is_stale) {
        gaps.push({ stepIndex: step.step_index, stepId: step.id, issue: 'stale' })
      }
    })

    return gaps.slice(0, 5) // Limit to 5
  }

  const actors = getActorsSummary()
  const humanActors = actors.filter(a => a.type === 'human')
  const systemActors = actors.filter(a => a.type === 'system')
  const progress = getProgress()
  const evidence = getEvidenceStrength()
  const valueMoments = getValueMoments()
  const gaps = getGaps()

  if (steps.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <h3 className="text-sm font-semibold text-[#009b87] uppercase tracking-wide mb-4">
          Path Summary
        </h3>
        <p className="text-sm text-gray-500">Generate the value path to see insights.</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-5">
      <h3 className="text-sm font-semibold text-[#009b87] uppercase tracking-wide">
        Path Summary
      </h3>

      {/* Actors Section */}
      <div>
        <h4 className="text-xs font-semibold text-[#009b87] uppercase tracking-wide mb-2 flex items-center gap-1">
          <User className="w-3 h-3" /> Actors
        </h4>
        <div className="space-y-1.5">
          {/* Human actors */}
          {humanActors.map(actor => (
            <div key={actor.name} className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <div className="w-5 h-5 rounded-full bg-emerald-100 flex items-center justify-center">
                  <User className="w-3 h-3 text-emerald-700" />
                </div>
                <span className="text-gray-700">{actor.name}</span>
              </div>
              <span className="text-xs text-gray-400">{actor.stepCount} steps</span>
            </div>
          ))}

          {/* Divider if we have both */}
          {humanActors.length > 0 && systemActors.length > 0 && (
            <div className="border-t border-dashed border-gray-200 my-2" />
          )}

          {/* System actors */}
          {systemActors.map(actor => (
            <div key={actor.name} className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <div className="w-5 h-5 rounded-full bg-slate-100 flex items-center justify-center">
                  {actor.name.includes('AI') || actor.name.includes('Engine') ? (
                    <Bot className="w-3 h-3 text-slate-500" />
                  ) : (
                    <Plug className="w-3 h-3 text-slate-500" />
                  )}
                </div>
                <span className="text-gray-500">{actor.name}</span>
              </div>
              <span className="text-xs text-gray-400">{actor.stepCount} steps</span>
            </div>
          ))}
        </div>
      </div>

      {/* Progress Section */}
      <div>
        <h4 className="text-xs font-semibold text-[#009b87] uppercase tracking-wide mb-2 flex items-center gap-1">
          <CheckCircle className="w-3 h-3" /> Progress
        </h4>
        <div className="space-y-1">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">Confirmed</span>
            <span className="text-gray-900 font-medium">{progress.confirmed}/{progress.total}</span>
          </div>
          <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-green-500 rounded-full transition-all duration-300"
              style={{ width: `${(progress.confirmed / progress.total) * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* Evidence Section */}
      <div>
        <h4 className="text-xs font-semibold text-[#009b87] uppercase tracking-wide mb-2 flex items-center gap-1">
          <FileText className="w-3 h-3" /> Evidence
        </h4>
        <div className="space-y-1">
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-green-500" />
              <span className="text-gray-600">Signal-backed</span>
            </div>
            <span className="text-gray-900 font-medium">{evidence.signalBacked}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-gray-300" />
              <span className="text-gray-600">AI-inferred</span>
            </div>
            <span className="text-gray-900 font-medium">{evidence.inferred}</span>
          </div>
          {evidence.total > 0 && (
            <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden flex">
              <div
                className="h-full bg-green-500"
                style={{ width: `${(evidence.signalBacked / evidence.total) * 100}%` }}
              />
              <div
                className="h-full bg-gray-300"
                style={{ width: `${(evidence.inferred / evidence.total) * 100}%` }}
              />
            </div>
          )}
        </div>
      </div>

      {/* Value Moments Section */}
      <div>
        <h4 className="text-xs font-semibold text-[#009b87] uppercase tracking-wide mb-2 flex items-center gap-1">
          <Sparkles className="w-3 h-3" /> Value Moments
        </h4>
        <div className="space-y-1 text-sm">
          {valueMoments.high.length > 0 && (
            <div className="flex items-center justify-between">
              <span className="text-amber-500">★★★ High</span>
              <span className="text-gray-500">
                Step {valueMoments.high.join(', ')}
              </span>
            </div>
          )}
          {valueMoments.medium.length > 0 && (
            <div className="flex items-center justify-between">
              <span className="text-amber-400">★★ Medium</span>
              <span className="text-gray-500">
                Step {valueMoments.medium.join(', ')}
              </span>
            </div>
          )}
          {valueMoments.low.length > 0 && (
            <div className="flex items-center justify-between">
              <span className="text-gray-400">★ Low</span>
              <span className="text-gray-500">
                Step {valueMoments.low.join(', ')}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Gaps Section */}
      {gaps.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-[#009b87] uppercase tracking-wide mb-2 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" /> Gaps
          </h4>
          <div className="space-y-1.5">
            {gaps.map((gap, idx) => (
              <button
                key={idx}
                onClick={() => onSelectStep?.(gap.stepId)}
                className="w-full flex items-center gap-2 text-sm text-left hover:bg-amber-50 rounded p-1 -ml-1 transition-colors"
              >
                <AlertTriangle className="w-3 h-3 text-amber-500 flex-shrink-0" />
                <span className="text-gray-600">
                  Step {gap.stepIndex}: <span className="text-amber-600">{gap.issue}</span>
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default VpPathSummary
