'use client'

import { useState } from 'react'
import type { FeatureOverlay, OverlayContent, TourStep } from '@/types/prototype'

interface FeatureInfoCardProps {
  overlay: FeatureOverlay | null
  tourStep: TourStep | null
}

type InfoTab = 'overview' | 'impact' | 'gaps' | 'flow'

const TAB_CONFIG: { key: InfoTab; label: string }[] = [
  { key: 'overview', label: 'Overview' },
  { key: 'impact', label: 'Impact' },
  { key: 'gaps', label: 'Gaps' },
  { key: 'flow', label: 'Flow' },
]

const CONFIDENCE_COLORS: Record<string, string> = {
  high: 'bg-emerald-400',
  medium: 'bg-brand-accent',
  low: 'bg-red-400',
}

function confidenceLevel(score: number): string {
  if (score >= 0.7) return 'high'
  if (score >= 0.4) return 'medium'
  return 'low'
}

/**
 * Tabbed feature info card shown in the right panel during prototype review.
 * Displays rich context about the current feature from overlay data.
 *
 * Tabs:
 * - Overview: what it does, personas, triggers, confidence
 * - Impact: business rules, actions, data requirements
 * - Gaps: questions, upload suggestions, confidence bar
 * - Flow: dependencies, flow position, connected features
 */
export default function FeatureInfoCard({ overlay, tourStep }: FeatureInfoCardProps) {
  const [activeTab, setActiveTab] = useState<InfoTab>('overview')

  if (!overlay?.overlay_content) {
    return (
      <div className="p-4 text-center">
        <div className="w-10 h-10 mx-auto mb-2 rounded-full bg-ui-background flex items-center justify-center">
          <span className="text-ui-supportText text-lg">i</span>
        </div>
        <p className="text-xs text-ui-supportText">
          {tourStep ? 'Loading feature data...' : 'Click a feature or start the tour to see details'}
        </p>
      </div>
    )
  }

  const content = overlay.overlay_content
  const gapsCount = content.questions.filter((q) => !q.answer).length

  return (
    <div className="flex flex-col h-full">
      {/* Feature header */}
      <div className="px-4 pt-3 pb-2 border-b border-ui-cardBorder">
        <div className="flex items-start justify-between gap-2 mb-2">
          <h3 className="text-sm font-semibold text-ui-headingDark leading-tight">
            {content.feature_name}
          </h3>
          <StatusBadge status={content.status} />
        </div>
        {tourStep?.vpStepLabel && (
          <div className="flex items-center gap-1.5 mb-2">
            <span className="w-1.5 h-1.5 rounded-full bg-brand-primary" />
            <span className="text-[11px] text-brand-primary font-medium">{tourStep.vpStepLabel}</span>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-0.5">
          {TAB_CONFIG.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors relative ${
                activeTab === key
                  ? 'bg-brand-primary/10 text-brand-primary'
                  : 'text-ui-supportText hover:text-ui-bodyText hover:bg-ui-background'
              }`}
            >
              {label}
              {key === 'gaps' && gapsCount > 0 && (
                <span className="ml-1 px-1 py-px bg-brand-primary text-white text-[9px] rounded-full">
                  {gapsCount}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
        {activeTab === 'overview' && <OverviewTab content={content} tourStep={tourStep} />}
        {activeTab === 'impact' && <ImpactTab content={content} />}
        {activeTab === 'gaps' && <GapsTab content={content} />}
        {activeTab === 'flow' && <FlowTab content={content} />}
      </div>
    </div>
  )
}

// =============================================================================
// Status Badge
// =============================================================================

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    understood: 'bg-emerald-100 text-emerald-800',
    partial: 'bg-amber-100 text-amber-800',
    unknown: 'bg-gray-100 text-gray-600',
  }
  return (
    <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full whitespace-nowrap ${styles[status] || styles.unknown}`}>
      {status}
    </span>
  )
}

// =============================================================================
// Overview Tab
// =============================================================================

function OverviewTab({ content, tourStep }: { content: OverlayContent; tourStep: TourStep | null }) {
  return (
    <div className="space-y-4">
      {/* Confidence + role */}
      <div className="flex items-center gap-3">
        <div className="flex-1">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[11px] text-ui-supportText">Confidence</span>
            <span className="text-[11px] font-medium text-ui-bodyText">{Math.round(content.confidence * 100)}%</span>
          </div>
          <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${CONFIDENCE_COLORS[confidenceLevel(content.confidence)]}`}
              style={{ width: `${content.confidence * 100}%` }}
            />
          </div>
        </div>
        {tourStep && (
          <span className={`text-[10px] font-medium px-2 py-0.5 rounded ${
            tourStep.featureRole === 'core'
              ? 'bg-brand-primary/10 text-brand-primary'
              : tourStep.featureRole === 'supporting'
                ? 'bg-brand-accent/10 text-brand-accent'
                : 'bg-gray-100 text-gray-500'
          }`}>
            {tourStep.featureRole}
          </span>
        )}
      </div>

      {/* Implementation notes */}
      {content.implementation_notes && (
        <Section title="What it does">
          <p className="text-xs text-ui-bodyText leading-relaxed">{content.implementation_notes}</p>
        </Section>
      )}

      {/* Personas */}
      {content.personas.length > 0 && (
        <Section title="Used by">
          <div className="flex flex-wrap gap-1.5">
            {content.personas.map((p) => (
              <span key={p.persona_id} className="text-[11px] bg-ui-background px-2 py-0.5 rounded-full text-ui-bodyText">
                {p.persona_name}
                {p.role && <span className="text-ui-supportText ml-1">({p.role})</span>}
              </span>
            ))}
          </div>
        </Section>
      )}

      {/* Triggers */}
      {content.triggers.length > 0 && (
        <Section title="Triggers">
          <ul className="space-y-1">
            {content.triggers.map((t, i) => (
              <li key={i} className="text-xs text-ui-bodyText flex items-start gap-1.5">
                <span className="text-brand-primary mt-0.5">&#x2022;</span>{t}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* Actions */}
      {content.actions.length > 0 && (
        <Section title="Actions">
          <ul className="space-y-1">
            {content.actions.map((a, i) => (
              <li key={i} className="text-xs text-ui-bodyText flex items-start gap-1.5">
                <span className="text-brand-accent mt-0.5">&#x25B8;</span>{a}
              </li>
            ))}
          </ul>
        </Section>
      )}
    </div>
  )
}

// =============================================================================
// Impact Tab
// =============================================================================

function ImpactTab({ content }: { content: OverlayContent }) {
  return (
    <div className="space-y-4">
      {/* Business rules */}
      {content.business_rules.length > 0 && (
        <Section title="Business Rules">
          <div className="space-y-2">
            {content.business_rules.map((br, i) => (
              <div key={i} className="bg-ui-background rounded-lg p-2.5">
                <p className="text-xs text-ui-bodyText">{br.rule}</p>
                <div className="flex items-center gap-2 mt-1.5">
                  <span className={`text-[10px] font-medium ${
                    br.source === 'confirmed' ? 'text-emerald-700' : br.source === 'aios' ? 'text-brand-primary' : 'text-ui-supportText'
                  }`}>
                    {br.source}
                  </span>
                  <span className="text-[10px] text-ui-supportText">
                    {Math.round(br.confidence * 100)}% confidence
                  </span>
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Data requirements */}
      {content.data_requirements.length > 0 && (
        <Section title="Data Requirements">
          <ul className="space-y-1">
            {content.data_requirements.map((d, i) => (
              <li key={i} className="text-xs text-ui-bodyText flex items-start gap-1.5">
                <span className="text-ui-supportText mt-0.5">&#x25CB;</span>{d}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* Placeholder for future pipeline enrichment */}
      {content.business_rules.length === 0 && content.data_requirements.length === 0 && (
        <div className="text-center py-6">
          <p className="text-xs text-ui-supportText">Impact analysis not yet available for this feature.</p>
          <p className="text-[11px] text-ui-supportText mt-1">Business rules and requirements will appear here once analyzed.</p>
        </div>
      )}
    </div>
  )
}

// =============================================================================
// Gaps Tab
// =============================================================================

function GapsTab({ content }: { content: OverlayContent }) {
  const unanswered = content.questions.filter((q) => !q.answer)
  const answered = content.questions.filter((q) => !!q.answer)

  return (
    <div className="space-y-4">
      {/* Confidence bar */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <span className="text-[11px] text-ui-supportText">Feature Confidence</span>
          <span className="text-[11px] font-medium text-ui-bodyText">{Math.round(content.confidence * 100)}%</span>
        </div>
        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${CONFIDENCE_COLORS[confidenceLevel(content.confidence)]}`}
            style={{ width: `${content.confidence * 100}%` }}
          />
        </div>
        <p className="text-[10px] text-ui-supportText mt-1">
          {content.gaps_count} gaps remaining
        </p>
      </div>

      {/* Unanswered questions */}
      {unanswered.length > 0 && (
        <Section title={`Open Questions (${unanswered.length})`}>
          <div className="space-y-2.5">
            {unanswered.map((q, i) => (
              <QuestionCard key={q.id} question={q} index={i + 1} />
            ))}
          </div>
        </Section>
      )}

      {/* Answered questions */}
      {answered.length > 0 && (
        <Section title={`Answered (${answered.length})`}>
          <div className="space-y-2">
            {answered.map((q, i) => (
              <div key={q.id} className="bg-emerald-50/50 rounded-lg p-2.5 border border-emerald-100">
                <p className="text-xs text-ui-supportText">{q.question}</p>
                <p className="text-xs text-emerald-700 mt-1 flex items-start gap-1">
                  <svg className="w-3 h-3 mt-0.5 flex-shrink-0" viewBox="0 0 16 16" fill="none">
                    <path d="M3 8L6.5 11.5L13 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                  {q.answer}
                </p>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Upload suggestions */}
      {content.upload_suggestions.length > 0 && (
        <Section title="Helpful Uploads">
          <div className="space-y-1.5">
            {content.upload_suggestions.map((us, i) => (
              <div key={i} className="flex items-start gap-2 text-xs">
                <span className="text-brand-primary mt-0.5">&#x2191;</span>
                <div>
                  <span className="font-medium text-ui-bodyText">{us.title}</span>
                  <p className="text-ui-supportText">{us.description}</p>
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}

      {content.questions.length === 0 && (
        <div className="text-center py-6">
          <p className="text-xs text-ui-supportText">No questions for this feature.</p>
        </div>
      )}
    </div>
  )
}

function QuestionCard({ question, index }: { question: { id: string; question: string; category: string; priority: string }; index: number }) {
  const priorityColors: Record<string, string> = {
    high: 'bg-brand-primary text-white',
    medium: 'bg-brand-accent text-white',
    low: 'bg-gray-200 text-gray-600',
  }

  return (
    <div className="bg-ui-background rounded-lg p-3">
      <div className="flex items-start gap-2">
        <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold flex-shrink-0 ${priorityColors[question.priority] || priorityColors.low}`}>
          {index}
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-xs text-ui-bodyText leading-relaxed">{question.question}</p>
          <span className="text-[10px] text-ui-supportText mt-1 inline-block">{question.category}</span>
        </div>
      </div>
    </div>
  )
}

// =============================================================================
// Flow Tab
// =============================================================================

function FlowTab({ content }: { content: OverlayContent }) {
  const upstream = content.dependencies.filter((d) => d.direction === 'upstream')
  const downstream = content.dependencies.filter((d) => d.direction === 'downstream')

  return (
    <div className="space-y-4">
      {/* Flow position */}
      {content.flow_position && (
        <div className="bg-brand-primary/5 rounded-lg p-3 border border-brand-primary/10">
          <div className="flex items-center gap-2 mb-1">
            <span className="w-6 h-6 rounded-full bg-brand-primary text-white text-[10px] font-bold flex items-center justify-center">
              {content.flow_position.vp_step_index}
            </span>
            <span className="text-xs font-medium text-brand-primary">{content.flow_position.vp_step_label}</span>
          </div>
          <p className="text-[11px] text-ui-supportText">Value path step position</p>
        </div>
      )}

      {/* Upstream dependencies */}
      {upstream.length > 0 && (
        <Section title="Depends On">
          <div className="space-y-1.5">
            {upstream.map((d, i) => (
              <DependencyRow key={i} dep={d} />
            ))}
          </div>
        </Section>
      )}

      {/* Current feature indicator */}
      <div className="flex items-center gap-2 py-2">
        <div className="flex-1 h-px bg-ui-cardBorder" />
        <span className="text-[10px] font-medium text-brand-primary px-2 py-0.5 bg-brand-primary/5 rounded">
          {content.feature_name}
        </span>
        <div className="flex-1 h-px bg-ui-cardBorder" />
      </div>

      {/* Downstream dependencies */}
      {downstream.length > 0 && (
        <Section title="Enables">
          <div className="space-y-1.5">
            {downstream.map((d, i) => (
              <DependencyRow key={i} dep={d} />
            ))}
          </div>
        </Section>
      )}

      {content.dependencies.length === 0 && !content.flow_position && (
        <div className="text-center py-6">
          <p className="text-xs text-ui-supportText">No flow data available for this feature.</p>
          <p className="text-[11px] text-ui-supportText mt-1">Dependencies and flow position will appear once mapped.</p>
        </div>
      )}
    </div>
  )
}

function DependencyRow({ dep }: { dep: { feature_name: string; relationship: string; direction: string } }) {
  return (
    <div className="flex items-center gap-2 text-xs bg-ui-background rounded px-2.5 py-1.5">
      <span className="text-ui-supportText">{dep.direction === 'upstream' ? '\u2190' : '\u2192'}</span>
      <span className="text-ui-bodyText font-medium">{dep.feature_name}</span>
      {dep.relationship && <span className="text-ui-supportText ml-auto text-[10px]">{dep.relationship}</span>}
    </div>
  )
}

// =============================================================================
// Standalone Tabs — for embedding in ReviewPanel without the full card header
// =============================================================================

export function FeatureInfoTabs({ content, tourStep }: { content: OverlayContent; tourStep: TourStep | null }) {
  const [activeTab, setActiveTab] = useState<InfoTab>('overview')
  const gapsCount = content.questions.filter((q) => !q.answer).length

  return (
    <div>
      <div className="flex gap-0.5 px-3 pt-2 pb-1.5">
        {TAB_CONFIG.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`px-2 py-1 text-[11px] font-medium rounded-md transition-colors ${
              activeTab === key
                ? 'bg-brand-primary/10 text-brand-primary'
                : 'text-ui-supportText hover:text-ui-bodyText hover:bg-ui-background'
            }`}
          >
            {label}
            {key === 'gaps' && gapsCount > 0 && (
              <span className="ml-1 px-1 py-px bg-brand-primary text-white text-[9px] rounded-full">
                {gapsCount}
              </span>
            )}
          </button>
        ))}
      </div>
      <div className="px-3 pb-3">
        {activeTab === 'overview' && <OverviewTab content={content} tourStep={tourStep} />}
        {activeTab === 'impact' && <ImpactTab content={content} />}
        {activeTab === 'gaps' && <GapsTab content={content} />}
        {activeTab === 'flow' && <FlowTab content={content} />}
      </div>
    </div>
  )
}

// =============================================================================
// Shared Section Component
// =============================================================================

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h4 className="text-[11px] font-semibold text-ui-headingDark uppercase tracking-wide mb-2">{title}</h4>
      {children}
    </div>
  )
}
