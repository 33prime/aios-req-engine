'use client'

import { useState, useCallback } from 'react'
import type { SolutionFlowStepSummary, SolutionFlowStepDetail, FeatureBRDSummary, VpStepBRDSummary, DataEntityBRDSummary } from '@/types/workspace'
import { getSolutionFlowStep } from '@/lib/api/admin'
import { PHASE_CARD_STYLE } from '@/lib/solution-flow-constants'
import { FlowStepChat } from '@/components/workspace/brd/components/FlowStepChat'
import { Markdown } from '@/components/ui/Markdown'
import { X, ChevronDown, ChevronRight, Layers, GitBranch, Database } from 'lucide-react'

interface FlowDetailPanelProps {
  projectId: string
  step: SolutionFlowStepSummary
  detail: SolutionFlowStepDetail | null
  isOpen: boolean
  onClose: () => void
  onPreview: () => void
  onDetailRefresh: (detail: SolutionFlowStepDetail) => void
  brdFeatures?: FeatureBRDSummary[]
  brdWorkflows?: VpStepBRDSummary[]
  brdDataEntities?: DataEntityBRDSummary[]
}

/** Extract first sentence from text */
function firstSentence(text: string): string {
  const match = text.match(/^[^.!?]+[.!?]/)
  return match ? match[0] : text.slice(0, 120)
}

export function FlowDetailPanel({
  projectId,
  step,
  detail,
  isOpen,
  onClose,
  onPreview,
  onDetailRefresh,
  brdFeatures,
  brdWorkflows,
  brdDataEntities,
}: FlowDetailPanelProps) {
  const style = PHASE_CARD_STYLE[step.phase] || PHASE_CARD_STYLE.admin

  // Before/After
  const painBefore = detail?.pain_points_addressed?.[0]
  const beforeText = painBefore ? (typeof painBefore === 'string' ? painBefore : painBefore.text) : null
  const afterText = detail?.goals_addressed?.[0] || detail?.success_criteria?.[0] || null

  // Story headline or fallback
  const storyHeadline = detail?.story_headline || (detail?.mock_data_narrative ? firstSentence(detail.mock_data_narrative) : null)

  // User actions
  const userActions = detail?.user_actions || []

  // Linked entity resolution
  const linkedFeatures = (detail?.linked_feature_ids || [])
    .map(id => brdFeatures?.find(f => f.id === id))
    .filter(Boolean)
  const linkedWorkflows = (detail?.linked_workflow_ids || [])
    .map(id => brdWorkflows?.find(w => w.id === id))
    .filter(Boolean)
  const linkedDataEntities = (detail?.linked_data_entity_ids || [])
    .map(id => brdDataEntities?.find(d => d.id === id))
    .filter(Boolean)
  const hasLinkedEntities = linkedFeatures.length > 0 || linkedWorkflows.length > 0 || linkedDataEntities.length > 0

  // Data profile summary
  const fields = detail?.information_fields || []
  const fieldCount = fields.length
  const knownCount = fields.filter(f => f.confidence === 'known').length
  const inferredCount = fields.filter(f => f.confidence === 'inferred').length
  const guessCount = fields.filter(f => f.confidence === 'guess').length
  const unknownCount = fields.filter(f => f.confidence === 'unknown').length
  const knownPct = fieldCount > 0 ? Math.round((knownCount / fieldCount) * 100) : 0

  const handleToolResult = useCallback((toolName: string) => {
    getSolutionFlowStep(projectId, step.id)
      .then(onDetailRefresh)
      .catch(() => {})
  }, [projectId, step.id, onDetailRefresh])

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed top-0 left-0 bottom-0 z-[180]"
        style={{ right: 480, background: 'rgba(10,30,47,0.10)' }}
        onClick={onClose}
      />

      {/* Slide-in panel */}
      <div
        className="fixed top-0 bottom-0 right-0 z-[210] flex flex-col"
        style={{
          width: 480,
          maxWidth: '90vw',
          background: '#fff',
          boxShadow: '-6px 0 32px rgba(10,30,47,0.10)',
          animation: 'panelSlideIn 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        }}
      >
        {/* Header */}
        <div className="flex items-start gap-2.5 px-4 py-3 border-b flex-shrink-0" style={{ borderColor: '#E2E8F0' }}>
          <div
            className="w-[30px] h-[30px] rounded-lg flex items-center justify-center text-xs font-bold text-white flex-shrink-0"
            style={{ background: style.idxColor }}
          >
            {step.step_index + 1}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-[13px] font-bold leading-tight" style={{ color: '#0A1E2F' }}>
              {step.title}
            </div>
            <div className="text-[10px] mt-0.5" style={{ color: '#718096', lineHeight: 1.4 }}>
              {step.goal}
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 transition-colors"
            style={{ border: '1px solid #E2E8F0', background: '#EDF2F7', color: '#718096' }}
            onMouseEnter={e => { e.currentTarget.style.background = '#E2E8F0'; e.currentTarget.style.color = '#0A1E2F' }}
            onMouseLeave={e => { e.currentTarget.style.background = '#EDF2F7'; e.currentTarget.style.color = '#718096' }}
          >
            <X size={12} />
          </button>
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto px-4 py-3 min-h-0">
          {/* Preview button */}
          <button
            onClick={onPreview}
            className="flex items-center justify-center gap-1.5 w-full py-2.5 rounded-[7px] text-[11px] font-semibold transition-all mb-3"
            style={{
              border: '1.5px solid rgba(63,175,122,0.3)',
              background: 'rgba(63,175,122,0.04)',
              color: '#2A8F5F',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(63,175,122,0.10)'; e.currentTarget.style.borderColor = '#3FAF7A' }}
            onMouseLeave={e => { e.currentTarget.style.background = 'rgba(63,175,122,0.04)'; e.currentTarget.style.borderColor = 'rgba(63,175,122,0.3)' }}
          >
            <span className="text-sm">&#x25E7;</span> Preview this screen
          </button>

          {/* Key Moment */}
          {storyHeadline && (
            <ExpandableStory
              headline={storyHeadline}
              fullNarrative={detail?.mock_data_narrative || null}
            />
          )}

          {/* Transformation */}
          {(beforeText || afterText) && (
            <Section label="Transformation">
              <div className="grid grid-cols-2 gap-[5px]">
                <div className="p-[7px_9px] rounded-[5px]" style={{ background: 'rgba(4,65,89,0.03)', border: '1px solid rgba(4,65,89,0.08)' }}>
                  <div className="text-[7px] font-semibold uppercase tracking-wide mb-[3px]" style={{ color: '#044159' }}>Today</div>
                  <div className="text-[9px] leading-snug" style={{ color: '#4A5568' }}>{beforeText || '\u2014'}</div>
                </div>
                <div className="p-[7px_9px] rounded-[5px]" style={{ background: 'rgba(63,175,122,0.03)', border: '1px solid rgba(63,175,122,0.08)' }}>
                  <div className="text-[7px] font-semibold uppercase tracking-wide mb-[3px]" style={{ color: '#2A8F5F' }}>Tomorrow</div>
                  <div className="text-[9px] leading-snug" style={{ color: '#4A5568' }}>{afterText || '\u2014'}</div>
                </div>
              </div>
            </Section>
          )}

          {/* What Users Do Here */}
          {userActions.length > 0 && (
            <Section label="What Users Do Here">
              <div className="flex flex-col gap-1">
                {userActions.map((action, i) => (
                  <div key={i} className="flex items-start gap-1.5 text-[10px]" style={{ color: '#2D3748' }}>
                    <span className="text-[10px] leading-[1.5] flex-shrink-0" style={{ color: '#3FAF7A' }}>&#x25B8;</span>
                    <span className="leading-[1.5]">{action}</span>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* Built From */}
          {hasLinkedEntities && (
            <Section label="Built From">
              <div className="flex flex-wrap gap-1">
                {linkedFeatures.map((f, i) => (
                  <LinkedEntityPill key={`f-${i}`} icon="feature" name={f!.name} status={f!.confirmation_status} />
                ))}
                {linkedWorkflows.map((w, i) => (
                  <LinkedEntityPill key={`w-${i}`} icon="workflow" name={w!.title} status={w!.confirmation_status} />
                ))}
                {linkedDataEntities.map((d, i) => (
                  <LinkedEntityPill key={`d-${i}`} icon="data" name={d!.name} status={d!.confirmation_status} />
                ))}
              </div>
            </Section>
          )}

          {/* Data Profile */}
          {fieldCount > 0 && (
            <CollapsibleSection label={`Data Profile (${fieldCount})`} defaultOpen={false}>
              <DataProfileSummary
                total={fieldCount}
                known={knownCount}
                inferred={inferredCount}
                guess={guessCount}
                unknown={unknownCount}
                knownPct={knownPct}
              />
              <div className="grid grid-cols-2 gap-[3px] mt-2">
                {fields.map((f, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-1 text-[9px] py-[3px] px-[5px] rounded-[3px]"
                    style={{ background: 'rgba(0,0,0,0.02)' }}
                  >
                    <span
                      className="w-1 h-1 rounded-full flex-shrink-0"
                      style={{
                        background: f.confidence === 'known' ? '#3FAF7A'
                          : f.confidence === 'inferred' ? '#044159'
                          : f.confidence === 'guess' ? '#D4A017'
                          : '#E5E5E5',
                      }}
                    />
                    <span className="flex-1 min-w-0 overflow-hidden text-ellipsis whitespace-nowrap" style={{ color: '#2D3748' }}>
                      {f.name}
                    </span>
                    <span className="text-[8px] flex-shrink-0" style={{ color: '#718096' }}>
                      {f.mock_value}
                    </span>
                  </div>
                ))}
              </div>
            </CollapsibleSection>
          )}

          {/* AI Config */}
          {(detail?.ai_config?.role || detail?.ai_config?.ai_role) && (
            <Section label="AI">
              <div
                className="p-[7px_9px] rounded-[5px]"
                style={{ background: 'rgba(4,65,89,0.03)', border: '1px solid rgba(4,65,89,0.08)' }}
              >
                <div className="text-[10px] font-medium mb-[2px]" style={{ color: '#2D3748' }}>
                  {detail.ai_config?.role || detail.ai_config?.ai_role}
                </div>
                {detail.ai_config?.behaviors?.map((b, i) => (
                  <div key={i} className="text-[9px] leading-snug py-[1px]" style={{ color: '#4A5568' }}>
                    <span className="inline-block w-[3px] h-[3px] rounded-full mr-[5px] align-middle" style={{ background: '#044159' }} />
                    {b}
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* Open Questions */}
          {detail?.open_questions && detail.open_questions.length > 0 && (
            <CollapsibleSection label={`Open Questions (${detail.open_questions.length})`} defaultOpen={false}>
              <div className="flex flex-col gap-1.5">
                {detail.open_questions.map((q, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-2 px-2.5 py-2 rounded-lg text-[11px]"
                    style={{ background: '#F7FAFC' }}
                  >
                    <span
                      className="text-[8px] font-bold uppercase px-1.5 py-0.5 rounded flex-shrink-0 mt-0.5"
                      style={{
                        background: q.status === 'resolved' ? 'rgba(63,175,122,0.1)' : 'rgba(4,65,89,0.06)',
                        color: q.status === 'resolved' ? '#2A8F5F' : '#044159',
                      }}
                    >
                      {q.status}
                    </span>
                    <span style={{ color: '#2D3748' }}>{q.question}</span>
                  </div>
                ))}
              </div>
            </CollapsibleSection>
          )}

          {/* Background Narrative / Consultant's Insight */}
          {detail?.background_narrative && (
            <Section label="Consultant&apos;s Insight">
              <div
                className="p-3 rounded-[6px]"
                style={{
                  background: 'linear-gradient(135deg, rgba(4,65,89,0.03), rgba(63,175,122,0.03))',
                  border: '1px solid rgba(4,65,89,0.08)',
                }}
              >
                <Markdown
                  content={detail.background_narrative}
                  className="text-[11px] leading-relaxed italic [&_p]:mb-1.5 [&_p:last-child]:mb-0 [&_strong]:not-italic [&_strong]:text-[#0A1E2F]"
                />
              </div>
            </Section>
          )}
        </div>

        {/* Chat */}
        <div className="flex-shrink-0 border-t flex flex-col" style={{ borderColor: '#E2E8F0', height: 220, background: '#EDF2F7' }}>
          <FlowStepChat
            projectId={projectId}
            stepId={step.id}
            stepTitle={step.title}
            stepGoal={step.goal}
            openQuestions={detail?.open_questions}
            onToolResult={handleToolResult}
          />
        </div>
      </div>

      <style jsx>{`
        @keyframes panelSlideIn {
          from { transform: translateX(100%); }
          to { transform: translateX(0); }
        }
      `}</style>
    </>
  )
}

// ── Local Components ────────────────────────────────────────────────

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mb-2.5">
      <div className="text-[8px] font-semibold uppercase tracking-wide mb-1" style={{ color: '#A0AEC0' }}>
        {label}
      </div>
      {children}
    </div>
  )
}

function CollapsibleSection({ label, defaultOpen = true, children }: { label: string; defaultOpen?: boolean; children: React.ReactNode }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="mb-2.5">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 mb-1 cursor-pointer w-full text-left"
      >
        <span className="text-[8px] font-semibold uppercase tracking-wide" style={{ color: '#A0AEC0' }}>{label}</span>
        {open
          ? <ChevronDown size={10} style={{ color: '#A0AEC0' }} />
          : <ChevronRight size={10} style={{ color: '#A0AEC0' }} />
        }
      </button>
      {open && children}
    </div>
  )
}

function ExpandableStory({ headline, fullNarrative }: { headline: string; fullNarrative: string | null }) {
  const [expanded, setExpanded] = useState(false)
  const hasMore = fullNarrative && fullNarrative.length > headline.length + 10

  return (
    <Section label="Key Moment">
      <div
        className="text-[11px] leading-[1.6] p-2.5 rounded-[6px]"
        style={{ background: '#EDF2F7', borderLeft: '3px solid #3FAF7A', color: '#2D3748' }}
      >
        {expanded && fullNarrative ? (
          <Markdown
            content={fullNarrative}
            className="text-[11px] leading-[1.6] [&_p]:mb-1.5 [&_p:last-child]:mb-0 [&_strong]:text-[#0A1E2F]"
          />
        ) : (
          <span>{headline}</span>
        )}
        {hasMore && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="block mt-1 text-[10px] font-medium"
            style={{ color: '#3FAF7A' }}
          >
            {expanded ? 'Show less' : 'Show full story \u2192'}
          </button>
        )}
      </div>
    </Section>
  )
}

function DataProfileSummary({ total, known, inferred, guess, unknown, knownPct }: {
  total: number; known: number; inferred: number; guess: number; unknown: number; knownPct: number
}) {
  const segments = [
    { count: known, color: '#3FAF7A' },
    { count: inferred, color: '#044159' },
    { count: guess, color: '#D4A017' },
    { count: unknown, color: '#E5E5E5' },
  ]
  return (
    <div>
      <div className="flex items-center gap-2 mb-1.5">
        <span className="text-[10px]" style={{ color: '#4A5568' }}>
          {total} data points &middot; {knownPct}% known
        </span>
      </div>
      <div className="flex h-1.5 rounded-full overflow-hidden gap-px">
        {segments.map((seg, i) => (
          seg.count > 0 ? (
            <div
              key={i}
              className="h-full rounded-full"
              style={{ flex: seg.count, background: seg.color }}
            />
          ) : null
        ))}
      </div>
    </div>
  )
}

function LinkedEntityPill({ icon, name, status }: { icon: 'feature' | 'workflow' | 'data'; name: string; status?: string | null }) {
  const Icon = icon === 'feature' ? Layers : icon === 'workflow' ? GitBranch : Database
  const dotColor = status === 'confirmed_client' ? '#3FAF7A'
    : status === 'confirmed_consultant' ? '#044159'
    : '#E5E5E5'

  return (
    <div
      className="inline-flex items-center gap-1 px-2 py-[3px] rounded-full text-[9px]"
      style={{ background: 'rgba(0,0,0,0.03)', border: '1px solid rgba(0,0,0,0.06)' }}
    >
      <Icon size={10} style={{ color: '#718096' }} />
      <span className="font-medium truncate max-w-[120px]" style={{ color: '#2D3748' }}>{name}</span>
      <span className="w-[5px] h-[5px] rounded-full flex-shrink-0" style={{ background: dotColor }} />
    </div>
  )
}
