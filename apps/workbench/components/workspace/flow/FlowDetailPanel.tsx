'use client'

import { useState, useEffect, useCallback } from 'react'
import type { SolutionFlowStepSummary, SolutionFlowStepDetail, PersonaSummary } from '@/types/workspace'
import { getSolutionFlowStep } from '@/lib/api/admin'
import { PHASE_CARD_STYLE } from '@/lib/solution-flow-constants'
import { FlowStepChat } from '@/components/workspace/brd/components/FlowStepChat'
import { Markdown } from '@/components/ui/Markdown'
import { X, ChevronDown, ChevronRight } from 'lucide-react'

interface FlowDetailPanelProps {
  projectId: string
  step: SolutionFlowStepSummary
  detail: SolutionFlowStepDetail | null
  isOpen: boolean
  onClose: () => void
  onPreview: () => void
  onDetailRefresh: (detail: SolutionFlowStepDetail) => void
}

function getPersonaColor(name: string): string {
  const palette = ['#3FAF7A', '#044159', '#2D6B4A', '#0A1E2F']
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash)
  return palette[Math.abs(hash) % palette.length]
}

export function FlowDetailPanel({
  projectId,
  step,
  detail,
  isOpen,
  onClose,
  onPreview,
  onDetailRefresh,
}: FlowDetailPanelProps) {
  const style = PHASE_CARD_STYLE[step.phase] || PHASE_CARD_STYLE.admin

  // Derive value badges
  const valueBadges: string[] = []
  if (detail?.pain_points_addressed?.length) valueBadges.push('Transform')
  if (detail?.ai_config?.role || detail?.ai_config?.ai_role) valueBadges.push('Amplify')
  if ((detail?.linked_workflow_ids?.length || 0) > 1) valueBadges.push('Connect')

  // Before/After
  const painBefore = detail?.pain_points_addressed?.[0]
  const beforeText = painBefore ? (typeof painBefore === 'string' ? painBefore : painBefore.text) : null
  const afterText = detail?.goals_addressed?.[0] || detail?.success_criteria?.[0] || null

  const handleToolResult = useCallback((toolName: string) => {
    getSolutionFlowStep(projectId, step.id)
      .then(onDetailRefresh)
      .catch(() => {})
  }, [projectId, step.id, onDetailRefresh])

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop — covers left of panel */}
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
            <span className="text-sm">◧</span> Preview this screen
          </button>

          {/* Narrative */}
          {detail?.mock_data_narrative && (
            <Section label="The Story">
              <div
                className="text-[11px] leading-[1.6] p-2.5 rounded-[6px]"
                style={{ background: '#EDF2F7', borderLeft: '3px solid #3FAF7A', color: '#2D3748' }}
              >
                <Markdown
                  content={detail.mock_data_narrative}
                  className="text-[11px] leading-[1.6] [&_p]:mb-1.5 [&_p:last-child]:mb-0 [&_strong]:text-[#0A1E2F]"
                />
              </div>
            </Section>
          )}

          {/* Transformation */}
          {(beforeText || afterText) && (
            <Section label="Transformation">
              <div className="grid grid-cols-2 gap-[5px]">
                <div className="p-[7px_9px] rounded-[5px]" style={{ background: 'rgba(4,65,89,0.03)', border: '1px solid rgba(4,65,89,0.08)' }}>
                  <div className="text-[7px] font-semibold uppercase tracking-wide mb-[3px]" style={{ color: '#044159' }}>Today</div>
                  <div className="text-[9px] leading-snug" style={{ color: '#4A5568' }}>{beforeText || '—'}</div>
                </div>
                <div className="p-[7px_9px] rounded-[5px]" style={{ background: 'rgba(63,175,122,0.03)', border: '1px solid rgba(63,175,122,0.08)' }}>
                  <div className="text-[7px] font-semibold uppercase tracking-wide mb-[3px]" style={{ color: '#2A8F5F' }}>Tomorrow</div>
                  <div className="text-[9px] leading-snug" style={{ color: '#4A5568' }}>{afterText || '—'}</div>
                </div>
              </div>
            </Section>
          )}

          {/* Information Fields */}
          {detail?.information_fields && detail.information_fields.length > 0 && (
            <CollapsibleSection label={`Fields (${detail.information_fields.length})`} defaultOpen>
              <div className="grid grid-cols-2 gap-[3px]">
                {detail.information_fields.map((f, i) => (
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
            <Section label={`Open Questions (${detail.open_questions.length})`}>
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
            </Section>
          )}

          {/* Background Narrative */}
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

        {/* Chat — fixed bottom, ~220px */}
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
