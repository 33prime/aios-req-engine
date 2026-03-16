'use client'

import { useState, useEffect, useCallback } from 'react'
import type { SolutionFlowStepSummary, SolutionFlowStepDetail, PersonaSummary } from '@/types/workspace'
import { getSolutionFlowStep } from '@/lib/api/admin'
import { SOLUTION_FLOW_PHASES, CONFIDENCE_DOT_COLOR } from '@/lib/solution-flow-constants'
import { FlowStepChat } from '@/components/workspace/brd/components/FlowStepChat'
import { Markdown } from '@/components/ui/Markdown'
import { X, ChevronDown, ChevronRight } from 'lucide-react'

interface FlowStepModalProps {
  projectId: string
  step: SolutionFlowStepSummary
  isOpen: boolean
  onClose: () => void
  personas: PersonaSummary[]
}

function getPersonaColor(name: string): string {
  const palette = ['#3FAF7A', '#044159', '#2D6B4A', '#0A1E2F']
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash)
  return palette[Math.abs(hash) % palette.length]
}

export function FlowStepModal({ projectId, step, isOpen, onClose, personas }: FlowStepModalProps) {
  const [detail, setDetail] = useState<SolutionFlowStepDetail | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!isOpen || !step?.id) return
    setLoading(true)
    getSolutionFlowStep(projectId, step.id)
      .then(setDetail)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [isOpen, step?.id, projectId])

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    if (isOpen) window.addEventListener('keydown', handleEsc)
    return () => window.removeEventListener('keydown', handleEsc)
  }, [isOpen, onClose])

  if (!isOpen) return null

  const phase = SOLUTION_FLOW_PHASES[step.phase]

  // Derive value badges
  const valueBadges: string[] = []
  if (detail?.pain_points_addressed?.length) valueBadges.push('Transform')
  if (detail?.ai_config?.role || detail?.ai_config?.ai_role) valueBadges.push('Amplify')
  if ((detail?.linked_workflow_ids?.length || 0) > 1) valueBadges.push('Connect')

  // Extract before/after
  const painBefore = detail?.pain_points_addressed?.[0]
  const beforeText = painBefore ? (typeof painBefore === 'string' ? painBefore : painBefore.text) : null
  const afterText = detail?.goals_addressed?.[0] || detail?.success_criteria?.[0] || null

  return (
    <div
      className="fixed inset-0 z-[200] flex items-center justify-center p-8"
      style={{ background: 'rgba(10,30,47,0.45)' }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div
        className="bg-white rounded-[14px] w-[940px] max-w-[95vw] max-h-[85vh] flex shadow-2xl overflow-hidden relative"
        style={{ animation: 'modalIn 0.3s ease' }}
      >
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 w-7 h-7 rounded-full flex items-center justify-center z-10 transition-colors"
          style={{ border: '1px solid #E5E5E5', background: '#F5F5F5', color: '#4B4B4B' }}
          onMouseEnter={e => { e.currentTarget.style.background = '#E5E5E5'; e.currentTarget.style.color = '#1D1D1F' }}
          onMouseLeave={e => { e.currentTarget.style.background = '#F5F5F5'; e.currentTarget.style.color = '#4B4B4B' }}
        >
          <X size={13} />
        </button>

        {/* Left: Detail */}
        <div className="flex-1 min-w-0 overflow-y-auto p-7">
          {loading ? (
            <div className="flex items-center justify-center h-40">
              <div className="animate-spin rounded-full h-6 w-6 border-2 border-[#3FAF7A] border-t-transparent" />
            </div>
          ) : (
            <>
              {/* Header */}
              <div className="flex items-center gap-2.5 mb-2">
                {phase && (
                  <span
                    className="text-[10px] font-semibold uppercase tracking-wide px-2 py-0.5 rounded"
                    style={{ background: 'rgba(63,175,122,0.08)', color: '#2A8F5F' }}
                  >
                    {phase.label}
                  </span>
                )}
                <span className="text-[10px] font-medium" style={{ color: '#999' }}>
                  Step {step.step_index + 1}
                </span>
                {valueBadges.map(badge => (
                  <span
                    key={badge}
                    className="text-[9px] font-semibold uppercase tracking-wide px-2 py-0.5 rounded"
                    style={{
                      background: badge === 'Transform' ? 'rgba(63,175,122,0.08)' : badge === 'Amplify' ? 'rgba(4,65,89,0.06)' : 'rgba(10,30,47,0.04)',
                      color: badge === 'Transform' ? '#2A8F5F' : badge === 'Amplify' ? '#044159' : '#0A1E2F',
                    }}
                  >
                    {badge}
                  </span>
                ))}
              </div>

              <h2 className="text-[22px] font-bold mb-1.5" style={{ color: '#1D1D1F', letterSpacing: '-0.01em' }}>
                {step.title}
              </h2>
              <Markdown
                content={step.goal}
                className="text-[13px] leading-relaxed mb-5 text-[#7B7B7B] [&_p]:mb-1.5 [&_p:last-child]:mb-0"
              />

              {/* Actors */}
              <div className="flex gap-2 mb-5 flex-wrap">
                {step.actors.map(name => {
                  const color = getPersonaColor(name)
                  return (
                    <div
                      key={name}
                      className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium"
                      style={{ background: `${color}10`, color, border: `1px solid ${color}20` }}
                    >
                      <div
                        className="w-4 h-4 rounded-full flex items-center justify-center text-[7px] font-bold text-white"
                        style={{ background: color }}
                      >
                        {name.split(' ').map(w => w[0]).join('').slice(0, 2)}
                      </div>
                      {name}
                    </div>
                  )
                })}
              </div>

              {/* Narrative */}
              {detail?.mock_data_narrative && (
                <Section label="The Story" icon="📖">
                  <div
                    className="rounded-[9px] p-3.5"
                    style={{ background: '#F5F5F5', borderLeft: '3px solid #3FAF7A' }}
                  >
                    <Markdown
                      content={detail.mock_data_narrative}
                      className="text-[12px] leading-[1.65] [&_p]:mb-2 [&_p:last-child]:mb-0 [&_strong]:text-[#1D1D1F] [&_li]:text-[12px]"
                    />
                  </div>
                </Section>
              )}

              {/* Before / After */}
              {(beforeText || afterText) && (
                <Section label="Transformation" icon="⚡">
                  <div
                    className="grid overflow-hidden rounded-[9px]"
                    style={{ gridTemplateColumns: '1fr auto 1fr', border: '1px solid #E5E5E5' }}
                  >
                    <div className="p-3" style={{ background: 'rgba(4,65,89,0.02)' }}>
                      <div className="text-[9px] font-semibold uppercase tracking-wide mb-1" style={{ color: '#044159' }}>Before</div>
                      <div className="text-[12px] font-medium leading-snug" style={{ color: '#333' }}>{beforeText || '—'}</div>
                    </div>
                    <div className="flex items-center justify-center px-2 text-base" style={{ background: '#F5F5F5', color: '#3FAF7A' }}>→</div>
                    <div className="p-3" style={{ background: 'rgba(63,175,122,0.025)' }}>
                      <div className="text-[9px] font-semibold uppercase tracking-wide mb-1" style={{ color: '#2A8F5F' }}>After</div>
                      <div className="text-[12px] font-medium leading-snug" style={{ color: '#333' }}>{afterText || '—'}</div>
                    </div>
                  </div>
                </Section>
              )}

              {/* AI Role */}
              {(detail?.ai_config?.role || detail?.ai_config?.ai_role) && (
                <Section label="AI Role" icon="🤖">
                  <div
                    className="text-[12px] leading-relaxed p-3 rounded-lg"
                    style={{ background: 'rgba(4,65,89,0.03)', color: '#333', borderLeft: '3px solid #044159' }}
                  >
                    {detail.ai_config?.role || detail.ai_config?.ai_role}
                  </div>
                </Section>
              )}

              {/* Information Fields — collapsible */}
              {detail?.information_fields && detail.information_fields.length > 0 && (
                <CollapsibleSection
                  label={`Information Fields (${detail.information_fields.length})`}
                  icon="📋"
                  defaultOpen={false}
                >
                  <div className="grid grid-cols-2 gap-2">
                    {detail.information_fields.map((f, i) => (
                      <div
                        key={i}
                        className="flex items-center gap-2 px-3 py-2 rounded-lg text-[12px]"
                        style={{ background: '#F5F5F5' }}
                      >
                        <div
                          className="w-2 h-2 rounded-full flex-shrink-0"
                          style={{
                            background: f.confidence === 'known' ? '#3FAF7A'
                              : f.confidence === 'inferred' ? 'rgba(10,30,47,0.4)'
                              : '#BBBBBB',
                          }}
                        />
                        <span className="font-medium" style={{ color: '#333' }}>{f.name}</span>
                        <span className="text-[10px] ml-auto" style={{ color: '#999' }}>{f.type}</span>
                      </div>
                    ))}
                  </div>
                </CollapsibleSection>
              )}

              {/* Open Questions */}
              {detail?.open_questions && detail.open_questions.length > 0 && (
                <Section label={`Open Questions (${detail.open_questions.length})`} icon="❓">
                  <div className="flex flex-col gap-1.5">
                    {detail.open_questions.map((q, i) => (
                      <div
                        key={i}
                        className="flex items-start gap-2 px-3 py-2.5 rounded-lg text-[12px]"
                        style={{ background: '#F5F5F5' }}
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
                        <span style={{ color: '#333' }}>{q.question}</span>
                      </div>
                    ))}
                  </div>
                </Section>
              )}

              {/* Background Narrative */}
              {detail?.background_narrative && (
                <Section label="Consultant&apos;s Insight" icon="💡">
                  <div
                    className="p-3.5 rounded-[9px]"
                    style={{
                      background: 'linear-gradient(135deg, rgba(4,65,89,0.03), rgba(63,175,122,0.03))',
                      border: '1px solid rgba(4,65,89,0.08)',
                    }}
                  >
                    <Markdown
                      content={detail.background_narrative}
                      className="text-[12px] leading-relaxed italic [&_p]:mb-2 [&_p:last-child]:mb-0 [&_strong]:not-italic [&_strong]:text-[#1D1D1F]"
                    />
                  </div>
                </Section>
              )}
            </>
          )}
        </div>

        {/* Right: Chat */}
        <div
          className="w-[320px] flex-shrink-0 flex flex-col"
          style={{ borderLeft: '1px solid #E5E5E5', background: '#F5F5F5' }}
        >
          <FlowStepChat
            projectId={projectId}
            stepId={step.id}
            stepTitle={step.title}
            stepGoal={step.goal}
            openQuestions={detail?.open_questions}
            onToolResult={(toolName) => {
              // Refresh detail on mutation
              getSolutionFlowStep(projectId, step.id)
                .then(setDetail)
                .catch(() => {})
            }}
          />
        </div>
      </div>

      <style jsx>{`
        @keyframes modalIn {
          from { opacity: 0; transform: translateY(16px) scale(0.98); }
          to { opacity: 1; transform: translateY(0) scale(1); }
        }
      `}</style>
    </div>
  )
}

// Reusable section label
function Section({ label, icon, children }: { label: string; icon: string; children: React.ReactNode }) {
  return (
    <div className="mb-5">
      <div className="flex items-center gap-1.5 mb-2 mt-5">
        <span className="text-xs">{icon}</span>
        <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: '#7B7B7B' }}>{label}</span>
      </div>
      {children}
    </div>
  )
}

// Collapsible section with toggle
function CollapsibleSection({ label, icon, defaultOpen = true, children }: { label: string; icon: string; defaultOpen?: boolean; children: React.ReactNode }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="mb-5">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 mb-2 mt-5 cursor-pointer group w-full text-left"
      >
        <span className="text-xs">{icon}</span>
        <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: '#7B7B7B' }}>{label}</span>
        {open
          ? <ChevronDown size={12} className="ml-1" style={{ color: '#999' }} />
          : <ChevronRight size={12} className="ml-1" style={{ color: '#999' }} />
        }
      </button>
      {open && children}
    </div>
  )
}
