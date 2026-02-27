/**
 * CurrentFocusSection Component
 *
 * Phase-aware content display that shows the most relevant action
 * based on the current collaboration phase:
 * - pre_discovery: Discovery prep generation/confirmation
 * - discovery: Active discovery call
 * - validation: Pending validation tasks
 * - prototype: Prototype feedback collection
 * - iteration: Ongoing iteration feedback
 */

'use client'

import React from 'react'
import {
  Calendar,
  UserCheck,
  Sparkles,
  MessageSquare,
  CheckCircle,
  AlertCircle,
  ArrowRight,
  FileText,
  Loader2,
} from 'lucide-react'

interface DiscoveryPrepStatus {
  bundle_id?: string
  status: string
  questions_total: number
  questions_confirmed: number
  questions_answered: number
  documents_total: number
  documents_confirmed: number
  documents_received: number
  can_send: boolean
}

interface ValidationStatus {
  total_pending: number
  by_entity_type: Record<string, number>
  high_priority: number
  pushed_to_portal: number
  confirmed_by_client: number
}

interface PrototypeFeedbackStatus {
  prototype_shared: boolean
  prototype_url?: string
  screens_count: number
  feedback_requests_sent: number
  feedback_received: number
}

interface CurrentFocus {
  phase: string
  primary_action: string
  discovery_prep?: DiscoveryPrepStatus
  validation?: ValidationStatus
  prototype_feedback?: PrototypeFeedbackStatus
}

interface CurrentFocusSectionProps {
  currentFocus: CurrentFocus
  onGeneratePrep?: () => void
  onViewValidation?: () => void
  isGenerating?: boolean
}

const phaseConfig: Record<string, {
  icon: typeof Calendar
  label: string
  color: string
  bgColor: string
}> = {
  pre_discovery: {
    icon: Calendar,
    label: 'Pre-Discovery',
    color: 'text-purple-700',
    bgColor: 'bg-purple-100',
  },
  discovery: {
    icon: Sparkles,
    label: 'Discovery',
    color: 'text-brand-primary-hover',
    bgColor: 'bg-blue-100',
  },
  validation: {
    icon: UserCheck,
    label: 'Validation',
    color: 'text-amber-700',
    bgColor: 'bg-amber-100',
  },
  prototype: {
    icon: MessageSquare,
    label: 'Prototype Review',
    color: 'text-emerald-700',
    bgColor: 'bg-emerald-100',
  },
  iteration: {
    icon: ArrowRight,
    label: 'Iteration',
    color: 'text-gray-700',
    bgColor: 'bg-gray-100',
  },
}

export function CurrentFocusSection({
  currentFocus,
  onGeneratePrep,
  onViewValidation,
  isGenerating = false,
}: CurrentFocusSectionProps) {
  const config = phaseConfig[currentFocus.phase] || phaseConfig.pre_discovery
  const PhaseIcon = config.icon

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 ${config.bgColor} rounded-lg flex items-center justify-center`}>
            <PhaseIcon className={`w-5 h-5 ${config.color}`} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-semibold text-gray-900">Current Focus</h2>
              <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${config.bgColor} ${config.color}`}>
                {config.label}
              </span>
            </div>
            <p className="text-sm text-gray-600">{currentFocus.primary_action}</p>
          </div>
        </div>
      </div>

      {/* Phase-specific content */}
      {currentFocus.phase === 'pre_discovery' && currentFocus.discovery_prep && (
        <DiscoveryPrepContent
          status={currentFocus.discovery_prep}
          onGenerate={onGeneratePrep}
          isGenerating={isGenerating}
        />
      )}

      {currentFocus.phase === 'validation' && currentFocus.validation && (
        <ValidationContent
          status={currentFocus.validation}
          onView={onViewValidation}
        />
      )}

      {currentFocus.phase === 'prototype' && currentFocus.prototype_feedback && (
        <PrototypeContent status={currentFocus.prototype_feedback} />
      )}

      {currentFocus.phase === 'discovery' && (
        <DiscoveryActiveContent />
      )}

      {currentFocus.phase === 'iteration' && (
        <IterationContent />
      )}
    </div>
  )
}

// ============================================================================
// Phase-specific content components
// ============================================================================

function DiscoveryPrepContent({
  status,
  onGenerate,
  isGenerating,
}: {
  status: DiscoveryPrepStatus
  onGenerate?: () => void
  isGenerating?: boolean
}) {
  const hasBundle = status.status !== 'not_generated'
  const isSent = status.status === 'sent'

  if (!hasBundle) {
    return (
      <div className="mt-4 p-4 bg-purple-50 rounded-lg border border-purple-100">
        <div className="flex items-start gap-3">
          <Sparkles className="w-5 h-5 text-purple-600 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm text-purple-900 font-medium">
              Generate discovery call preparation
            </p>
            <p className="text-xs text-purple-700 mt-1">
              AI will analyze your project context and generate targeted questions
              and document requests for your client.
            </p>
            {onGenerate && (
              <button
                onClick={onGenerate}
                disabled={isGenerating}
                className="mt-3 inline-flex items-center gap-2 px-4 py-2 bg-purple-600 text-white text-sm font-medium rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-colors"
              >
                {isGenerating ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    Generate Prep
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="mt-4 space-y-4">
      {/* Progress stats */}
      <div className="grid grid-cols-2 gap-4">
        <div className="p-3 bg-gray-50 rounded-lg">
          <div className="flex items-center gap-2 mb-2">
            <MessageSquare className="w-4 h-4 text-gray-500" />
            <span className="text-sm font-medium text-gray-700">Questions</span>
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-bold text-gray-900">
              {status.questions_answered}
            </span>
            <span className="text-sm text-gray-500">
              / {status.questions_total} answered
            </span>
          </div>
          {!isSent && (
            <p className="text-xs text-gray-500 mt-1">
              {status.questions_confirmed} confirmed for portal
            </p>
          )}
        </div>

        <div className="p-3 bg-gray-50 rounded-lg">
          <div className="flex items-center gap-2 mb-2">
            <FileText className="w-4 h-4 text-gray-500" />
            <span className="text-sm font-medium text-gray-700">Documents</span>
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-bold text-gray-900">
              {status.documents_received}
            </span>
            <span className="text-sm text-gray-500">
              / {status.documents_total} received
            </span>
          </div>
          {!isSent && (
            <p className="text-xs text-gray-500 mt-1">
              {status.documents_confirmed} confirmed for portal
            </p>
          )}
        </div>
      </div>

      {/* Status indicator */}
      {isSent ? (
        <div className="flex items-center gap-2 p-3 bg-green-50 border border-green-200 rounded-lg">
          <CheckCircle className="w-5 h-5 text-green-600" />
          <span className="text-sm text-green-800 font-medium">
            Sent to client portal - awaiting responses
          </span>
        </div>
      ) : status.can_send ? (
        <div className="flex items-center gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg">
          <AlertCircle className="w-5 h-5 text-amber-600" />
          <span className="text-sm text-amber-800">
            Ready to send to client portal
          </span>
        </div>
      ) : (
        <div className="flex items-center gap-2 p-3 bg-gray-50 border border-gray-200 rounded-lg">
          <AlertCircle className="w-5 h-5 text-gray-400" />
          <span className="text-sm text-gray-600">
            Confirm at least one question or document to send
          </span>
        </div>
      )}
    </div>
  )
}

function ValidationContent({
  status,
  onView,
}: {
  status: ValidationStatus
  onView?: () => void
}) {
  const entityTypes = Object.entries(status.by_entity_type)

  return (
    <div className="mt-4 space-y-4">
      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        <div className="p-3 bg-gray-50 rounded-lg text-center">
          <span className="text-2xl font-bold text-gray-900">{status.total_pending}</span>
          <p className="text-xs text-gray-500 mt-1">Pending</p>
        </div>
        <div className="p-3 bg-red-50 rounded-lg text-center">
          <span className="text-2xl font-bold text-red-700">{status.high_priority}</span>
          <p className="text-xs text-red-600 mt-1">High Priority</p>
        </div>
        <div className="p-3 bg-green-50 rounded-lg text-center">
          <span className="text-2xl font-bold text-green-700">{status.confirmed_by_client}</span>
          <p className="text-xs text-green-600 mt-1">Confirmed</p>
        </div>
      </div>

      {/* By entity type */}
      {entityTypes.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {entityTypes.map(([type, count]) => (
            <span
              key={type}
              className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 text-gray-700 text-xs font-medium rounded-full"
            >
              {count} {type.replace('_', ' ')}s
            </span>
          ))}
        </div>
      )}

      {status.total_pending === 0 ? (
        <div className="flex items-center gap-2 p-3 bg-green-50 border border-green-200 rounded-lg">
          <CheckCircle className="w-5 h-5 text-green-600" />
          <span className="text-sm text-green-800 font-medium">
            All items validated!
          </span>
        </div>
      ) : (
        onView && (
          <button
            onClick={onView}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-[#009b87] text-white text-sm font-medium rounded-lg hover:bg-[#008775] transition-colors"
          >
            <UserCheck className="w-4 h-4" />
            Review Validation Tasks
          </button>
        )
      )}
    </div>
  )
}

function PrototypeContent({ status }: { status: PrototypeFeedbackStatus }) {
  if (!status.prototype_shared) {
    return (
      <div className="mt-4 p-4 bg-emerald-50 rounded-lg border border-emerald-100">
        <div className="flex items-start gap-3">
          <MessageSquare className="w-5 h-5 text-emerald-600 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm text-emerald-900 font-medium">
              Share prototype with client
            </p>
            <p className="text-xs text-emerald-700 mt-1">
              Once your prototype is ready, share it with the client to collect
              screen-by-screen feedback.
            </p>
            <button
              disabled
              className="mt-3 inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white text-sm font-medium rounded-lg opacity-50 cursor-not-allowed"
            >
              <MessageSquare className="w-4 h-4" />
              Coming Soon
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="mt-4 space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="p-3 bg-gray-50 rounded-lg text-center">
          <span className="text-2xl font-bold text-gray-900">{status.screens_count}</span>
          <p className="text-xs text-gray-500 mt-1">Screens</p>
        </div>
        <div className="p-3 bg-emerald-50 rounded-lg text-center">
          <span className="text-2xl font-bold text-emerald-700">{status.feedback_received}</span>
          <p className="text-xs text-emerald-600 mt-1">Feedback Items</p>
        </div>
      </div>

      {status.prototype_url && (
        <a
          href={status.prototype_url}
          target="_blank"
          rel="noopener noreferrer"
          className="block w-full text-center px-4 py-2 text-sm font-medium text-emerald-700 bg-emerald-50 rounded-lg hover:bg-emerald-100 transition-colors"
        >
          View Prototype
        </a>
      )}
    </div>
  )
}

function DiscoveryActiveContent() {
  return (
    <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-100">
      <div className="flex items-start gap-3">
        <Sparkles className="w-5 h-5 text-brand-primary mt-0.5" />
        <div className="flex-1">
          <p className="text-sm text-blue-900 font-medium">
            Discovery call in progress
          </p>
          <p className="text-xs text-brand-primary-hover mt-1">
            The client is actively engaged with your discovery preparation.
            Monitor responses in the client portal section.
          </p>
        </div>
      </div>
    </div>
  )
}

function IterationContent() {
  return (
    <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
      <div className="flex items-start gap-3">
        <ArrowRight className="w-5 h-5 text-gray-600 mt-0.5" />
        <div className="flex-1">
          <p className="text-sm text-gray-900 font-medium">
            Iteration phase
          </p>
          <p className="text-xs text-gray-600 mt-1">
            Continue refining based on client feedback. Create new validation
            rounds or collect additional prototype feedback as needed.
          </p>
        </div>
      </div>
    </div>
  )
}

export default CurrentFocusSection
