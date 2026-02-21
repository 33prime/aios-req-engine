'use client'

import { useState, useEffect, useRef } from 'react'
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Layout,
  FileText,
  Image as ImageIcon,
  Paperclip,
  GitBranch,
  Box,
  Database,
  ArrowUpRight,
  History,
  FileSearch,
  Sparkles,
  MessageCircle,
} from 'lucide-react'
import { ConfirmActions } from './ConfirmActions'
import type { SolutionFlowStepDetail as StepDetail, InformationField, FlowOpenQuestion, RevisionEntry } from '@/types/workspace'
import type { EntityLookup } from './SolutionFlowModal'
import { getDocumentStatus, getSolutionFlowStepRevisions } from '@/lib/api'

// ─── Confidence dot colors ───────────────────────────────────────────────────
const CONFIDENCE_DOT: Record<string, { color: string; label: string }> = {
  known: { color: 'bg-[#3FAF7A]', label: 'Known' },
  inferred: { color: 'bg-[#0A1E2F]', label: 'Inferred' },
  guess: { color: 'bg-[#C4A97D]', label: 'Guess' },
  unknown: { color: 'bg-[#CCCCCC]', label: 'Unknown' },
}

const ENTITY_CONFIG: Record<string, { icon: typeof GitBranch; label: string; color: string; bg: string }> = {
  workflow: { icon: GitBranch, label: 'Workflow', color: 'text-[#0A1E2F]', bg: 'bg-[#0A1E2F]/5 border-[#0A1E2F]/15' },
  feature: { icon: Box, label: 'Feature', color: 'text-[#25785A]', bg: 'bg-[#3FAF7A]/5 border-[#3FAF7A]/15' },
  data_entity: { icon: Database, label: 'Data Entity', color: 'text-[#0D2A35]', bg: 'bg-[#0D2A35]/5 border-[#0D2A35]/15' },
}

// ─── Revision badge config ───────────────────────────────────────────────────
const REVISION_BADGE: Record<string, { label: string; color: string; icon: typeof Sparkles }> = {
  chat_tool: { label: 'Updated', color: 'bg-[#3FAF7A]/10 text-[#25785A]', icon: CheckCircle2 },
  refine_chat_tool: { label: 'AI Refined', color: 'bg-[#0A1E2F]/10 text-[#0A1E2F]', icon: Sparkles },
  question_resolved: { label: 'Q&A', color: 'bg-[#3FAF7A]/10 text-[#25785A]', icon: MessageCircle },
  question_escalated: { label: 'Escalated', color: 'bg-[#EDE8D5] text-[#8B7355]', icon: ArrowUpRight },
}

interface EvidenceFile {
  id: string
  filename: string
  fileType: string
  status: string
}

interface FlowStepDetailProps {
  step: StepDetail | null
  loading: boolean
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
  entityLookup?: EntityLookup
  projectId: string
}

// ─── CSS animations (injected once) ─────────────────────────────────────────
const ANIMATION_STYLES = `
@keyframes slideInLeft {
  from { opacity: 0; transform: translateX(-8px); }
  to { opacity: 1; transform: translateX(0); }
}
@keyframes pulseGreen {
  0% { background-color: rgba(63, 175, 122, 0.15); }
  100% { background-color: transparent; }
}
.animate-slideInLeft { animation: slideInLeft 0.4s ease-out; }
.animate-pulseGreen { animation: pulseGreen 2.5s ease-out; }
`

export function FlowStepDetail({ step, loading, onConfirm, onNeedsReview, entityLookup, projectId }: FlowStepDetailProps) {
  const [evidenceFiles, setEvidenceFiles] = useState<EvidenceFile[]>([])
  const [activeTab, setActiveTab] = useState<'details' | 'history'>('details')
  const [revisions, setRevisions] = useState<RevisionEntry[]>([])
  const [revisionsLoading, setRevisionsLoading] = useState(false)

  // ─── Change highlighting state ──────────────────────────────────────────────
  const prevStepRef = useRef<StepDetail | null>(null)
  const [changedFields, setChangedFields] = useState<Set<string>>(new Set())

  useEffect(() => {
    if (!step || !prevStepRef.current || step.id !== prevStepRef.current.id) {
      prevStepRef.current = step
      return
    }
    const prev = prevStepRef.current
    const changed = new Set<string>()

    if (step.goal !== prev.goal) changed.add('goal')
    if (JSON.stringify(step.actors) !== JSON.stringify(prev.actors)) changed.add('actors')
    if (JSON.stringify(step.information_fields) !== JSON.stringify(prev.information_fields)) {
      changed.add('info_fields')
      const prevNames = new Set((prev.information_fields || []).map(f => f.name))
      for (const f of step.information_fields || []) {
        if (!prevNames.has(f.name)) changed.add(`field:${f.name}`)
        else {
          const oldField = prev.information_fields?.find(pf => pf.name === f.name)
          if (oldField && JSON.stringify(oldField) !== JSON.stringify(f)) changed.add(`field:${f.name}`)
        }
      }
    }
    if (JSON.stringify(step.open_questions) !== JSON.stringify(prev.open_questions)) changed.add('questions')
    if (step.mock_data_narrative !== prev.mock_data_narrative) changed.add('narrative')

    prevStepRef.current = step
    if (changed.size > 0) {
      setChangedFields(changed)
      setTimeout(() => setChangedFields(new Set()), 2500)
    }
  }, [step])

  // ─── Load evidence file metadata ───────────────────────────────────────────
  useEffect(() => {
    if (!step?.evidence_ids?.length) {
      setEvidenceFiles([])
      return
    }
    let cancelled = false
    Promise.allSettled(
      step.evidence_ids.map(id =>
        getDocumentStatus(id).then(doc => ({
          id: doc.id,
          filename: doc.original_filename || `Document`,
          fileType: doc.document_class || doc.original_filename?.split('.').pop() || 'file',
          status: doc.processing_status || 'completed',
        }))
      )
    ).then(results => {
      if (cancelled) return
      const files: EvidenceFile[] = []
      for (const r of results) {
        if (r.status === 'fulfilled') files.push(r.value)
      }
      setEvidenceFiles(files)
    })
    return () => { cancelled = true }
  }, [step?.evidence_ids])

  // ─── Load revisions when History tab selected ──────────────────────────────
  useEffect(() => {
    if (activeTab !== 'history' || !step?.id || !projectId) return
    let cancelled = false
    setRevisionsLoading(true)
    getSolutionFlowStepRevisions(projectId, step.id)
      .then(data => {
        if (!cancelled) setRevisions(data.revisions || [])
      })
      .catch(() => {
        if (!cancelled) setRevisions([])
      })
      .finally(() => {
        if (!cancelled) setRevisionsLoading(false)
      })
    return () => { cancelled = true }
  }, [activeTab, step?.id, projectId])

  // Reset tab when step changes
  useEffect(() => {
    setActiveTab('details')
  }, [step?.id])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-48 text-sm text-[#999999]">
        Loading step details...
      </div>
    )
  }

  if (!step) {
    return (
      <div className="flex items-center justify-center h-48 text-sm text-[#999999]">
        Step not found
      </div>
    )
  }

  const infoFields: InformationField[] = step.information_fields || []
  const openQuestions: FlowOpenQuestion[] = (step.open_questions || []).filter(q => q.status === 'open')
  const escalatedQuestions: FlowOpenQuestion[] = (step.open_questions || []).filter(q => q.status === 'escalated')
  const resolvedQuestions: FlowOpenQuestion[] = (step.open_questions || []).filter(q => q.status === 'resolved')

  // Group info fields by confidence
  const definedFields = infoFields.filter(f => f.confidence === 'known' || f.confidence === 'inferred')
  const needsConfirmationFields = infoFields.filter(f => f.confidence === 'guess' || f.confidence === 'unknown')

  // Collect linked entities with resolved names
  const linkedEntities: { type: string; id: string; name: string }[] = []
  if (step.linked_workflow_ids?.length) {
    for (const id of step.linked_workflow_ids) {
      linkedEntities.push({
        type: 'workflow',
        id,
        name: entityLookup?.workflows[id] || id.slice(0, 8) + '...',
      })
    }
  }
  if (step.linked_feature_ids?.length) {
    for (const id of step.linked_feature_ids) {
      linkedEntities.push({
        type: 'feature',
        id,
        name: entityLookup?.features[id] || id.slice(0, 8) + '...',
      })
    }
  }
  if (step.linked_data_entity_ids?.length) {
    for (const id of step.linked_data_entity_ids) {
      linkedEntities.push({
        type: 'data_entity',
        id,
        name: entityLookup?.data_entities[id] || id.slice(0, 8) + '...',
      })
    }
  }

  const fileIcon = (fileType: string) => {
    if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'image'].includes(fileType.toLowerCase())) {
      return <ImageIcon className="w-4 h-4" />
    }
    return <FileText className="w-4 h-4" />
  }

  return (
    <div className="h-full overflow-y-auto p-5 space-y-5">
      {/* Inject animation styles */}
      <style>{ANIMATION_STYLES}</style>

      {/* Header with confirm actions */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-[#333333]">{step.title}</h2>
          <div className="flex items-center gap-2 mt-1">
            {step.actors.map((actor, i) => (
              <span
                key={actor}
                className={`text-xs px-2 py-0.5 rounded-full bg-[#0A1E2F]/8 text-[#0A1E2F] ${
                  changedFields.has('actors') ? 'animate-slideInLeft' : ''
                }`}
                style={changedFields.has('actors') ? { animationDelay: `${i * 80}ms` } : undefined}
              >
                {actor}
              </span>
            ))}
          </div>
        </div>
        <ConfirmActions
          status={step.confirmation_status || 'ai_generated'}
          onConfirm={() => onConfirm('solution_flow_step', step.id)}
          onNeedsReview={() => onNeedsReview('solution_flow_step', step.id)}
        />
      </div>

      {/* Details / History tab toggle */}
      <div className="flex gap-1 bg-[#F4F4F4] rounded-lg p-0.5 w-fit">
        <button
          onClick={() => setActiveTab('details')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
            activeTab === 'details'
              ? 'bg-white text-[#333333] shadow-sm'
              : 'text-[#999999] hover:text-[#666666]'
          }`}
        >
          <FileSearch className="w-3.5 h-3.5" />
          Details
        </button>
        <button
          onClick={() => setActiveTab('history')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
            activeTab === 'history'
              ? 'bg-white text-[#333333] shadow-sm'
              : 'text-[#999999] hover:text-[#666666]'
          }`}
        >
          <History className="w-3.5 h-3.5" />
          History
        </button>
      </div>

      {activeTab === 'details' ? (
        <>
          {/* Goal box */}
          <div className={`bg-[#0A1E2F] rounded-xl p-4 transition-all duration-700 ${
            changedFields.has('goal') ? 'ring-2 ring-[#3FAF7A]/30' : ''
          }`}>
            <div className="text-[10px] uppercase tracking-wider text-white/50 mb-1">Goal</div>
            <p className="text-sm text-white/90 leading-relaxed">{step.goal}</p>
          </div>

          {/* Linked Entities */}
          {linkedEntities.length > 0 && (
            <div>
              <h3 className="text-[11px] font-semibold uppercase tracking-wider text-[#999999] mb-2">
                Linked Entities
              </h3>
              <div className="flex flex-wrap gap-2">
                {linkedEntities.map(({ type, id, name }) => {
                  const config = ENTITY_CONFIG[type] || ENTITY_CONFIG.workflow
                  const Icon = config.icon
                  return (
                    <div
                      key={id}
                      className={`flex items-center gap-2 px-3 py-2 rounded-lg border ${config.bg}`}
                    >
                      <Icon className={`w-3.5 h-3.5 ${config.color}`} />
                      <div className="min-w-0">
                        <span className={`text-[10px] font-medium ${config.color} mr-1.5`}>{config.label}</span>
                        <span className="text-[12px] font-medium text-[#333333]">{name}</span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Key Information — card-based grouped by confidence */}
          {infoFields.length > 0 && (
            <div>
              <h3 className="text-[11px] font-semibold uppercase tracking-wider text-[#999999] mb-2">
                Key Information ({infoFields.length})
              </h3>
              <div className="space-y-1">
                {/* Defined fields (known + inferred) */}
                {definedFields.map((field) => (
                  <FieldRow
                    key={field.name}
                    field={field}
                    highlighted={changedFields.has(`field:${field.name}`)}
                    isNew={changedFields.has(`field:${field.name}`) && changedFields.has('info_fields')}
                  />
                ))}

                {/* Divider between defined and needs-confirmation */}
                {definedFields.length > 0 && needsConfirmationFields.length > 0 && (
                  <div className="flex items-center gap-2 py-1.5">
                    <div className="flex-1 border-t border-dashed border-[#E5E5E5]" />
                    <span className="text-[10px] font-medium text-[#999999] uppercase tracking-wider">
                      Needs Confirmation
                    </span>
                    <div className="flex-1 border-t border-dashed border-[#E5E5E5]" />
                  </div>
                )}

                {/* Guess + unknown fields */}
                {needsConfirmationFields.map((field) => (
                  <FieldRow
                    key={field.name}
                    field={field}
                    highlighted={changedFields.has(`field:${field.name}`)}
                    isNew={changedFields.has(`field:${field.name}`) && changedFields.has('info_fields')}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Mock Data Narrative */}
          {step.mock_data_narrative && (
            <div className={`bg-[#F4F4F4] border border-[#E5E5E5] rounded-xl p-4 transition-all duration-700 ${
              changedFields.has('narrative') ? 'ring-2 ring-[#3FAF7A]/30' : ''
            }`}>
              <h3 className="text-[11px] font-semibold uppercase tracking-wider text-[#999999] mb-2">
                Preview
              </h3>
              <p className="text-[13px] text-[#666666] leading-relaxed italic">
                {step.mock_data_narrative}
              </p>
            </div>
          )}

          {/* Open Questions */}
          {openQuestions.length > 0 && (
            <div className={changedFields.has('questions') ? 'animate-pulseGreen rounded-xl' : ''}>
              <h3 className="text-[11px] font-semibold uppercase tracking-wider text-[#999999] mb-2">
                Open Questions ({openQuestions.length})
              </h3>
              <div className="space-y-2">
                {openQuestions.map((q, i) => (
                  <div key={i} className="border-l-[3px] border-[#C4A97D] bg-[#EDE8D5]/30 rounded-r-lg p-3">
                    <div className="flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 text-[#A08050] shrink-0 mt-0.5" />
                      <div>
                        <p className="text-[13px] text-[#333333]">{q.question}</p>
                        {q.context && (
                          <p className="text-xs text-[#999999] mt-1">{q.context}</p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Escalated Questions */}
          {escalatedQuestions.length > 0 && (
            <div>
              <h3 className="text-[11px] font-semibold uppercase tracking-wider text-[#999999] mb-2">
                Queued for Client ({escalatedQuestions.length})
              </h3>
              <div className="space-y-2">
                {escalatedQuestions.map((q, i) => (
                  <div key={i} className="border-l-[3px] border-[#E5E5E5] bg-[#F9F9F9] rounded-r-lg p-3">
                    <div className="flex items-start gap-2">
                      <ArrowUpRight className="w-4 h-4 text-[#999999] shrink-0 mt-0.5" />
                      <div>
                        <p className="text-[13px] text-[#666666]">{q.question}</p>
                        {q.escalated_to && (
                          <p className="text-xs text-[#A08050] mt-1 flex items-center gap-1">
                            <Clock className="w-3 h-3" /> Queued for {q.escalated_to}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Resolved Questions */}
          {resolvedQuestions.length > 0 && (
            <div>
              <h3 className="text-[11px] font-semibold uppercase tracking-wider text-[#999999] mb-2">
                Resolved ({resolvedQuestions.length})
              </h3>
              <div className="space-y-2">
                {resolvedQuestions.map((q, i) => (
                  <div key={i} className="border-l-[3px] border-[#3FAF7A]/40 bg-[#3FAF7A]/5 rounded-r-lg p-3">
                    <div className="flex items-start gap-2">
                      <CheckCircle2 className="w-4 h-4 text-[#3FAF7A] shrink-0 mt-0.5" />
                      <div>
                        <p className="text-[13px] text-[#666666] line-through opacity-60">{q.question}</p>
                        <p className="text-[13px] text-[#333333] mt-1">{q.resolved_answer}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Implied Pattern */}
          {step.implied_pattern && (
            <div className="flex items-center gap-2">
              <Layout className="w-4 h-4 text-[#999999]" />
              <span className="text-xs px-2.5 py-1 rounded-full bg-[#F4F4F4] text-[#666666] font-medium">
                {step.implied_pattern}
              </span>
            </div>
          )}

          {/* Evidence & Uploads */}
          <div>
            <h3 className="text-[11px] font-semibold uppercase tracking-wider text-[#999999] mb-2">
              Evidence & Uploads
              {evidenceFiles.length > 0 && ` (${evidenceFiles.length})`}
            </h3>
            {evidenceFiles.length > 0 ? (
              <div className="space-y-1.5">
                {evidenceFiles.map(file => (
                  <div
                    key={file.id}
                    className="flex items-center gap-3 px-3 py-2.5 bg-white border border-[#E5E5E5] rounded-lg"
                  >
                    <div className="w-8 h-8 rounded-md bg-[#F4F4F4] flex items-center justify-center text-[#666666]">
                      {fileIcon(file.fileType)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-[13px] font-medium text-[#333333] truncate">{file.filename}</div>
                      <div className="text-[10px] text-[#999999] uppercase">{file.fileType}</div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex items-center gap-3 px-4 py-5 border border-dashed border-[#E5E5E5] rounded-xl text-center">
                <Paperclip className="w-4 h-4 text-[#BBBBBB]" />
                <p className="text-xs text-[#BBBBBB]">
                  No files attached yet. Use the chat to upload documents or images for this step.
                </p>
              </div>
            )}
          </div>
        </>
      ) : (
        /* ─── History Tab ─────────────────────────────────────────────────── */
        <HistoryTimeline revisions={revisions} loading={revisionsLoading} />
      )}
    </div>
  )
}

// ─── Field Row Component ─────────────────────────────────────────────────────

function FieldRow({
  field,
  highlighted,
  isNew,
}: {
  field: InformationField
  highlighted: boolean
  isNew: boolean
}) {
  const dot = CONFIDENCE_DOT[field.confidence] || CONFIDENCE_DOT.unknown
  return (
    <div
      className={`flex items-start gap-2.5 py-2 px-3 rounded-lg transition-all duration-500 ${
        highlighted
          ? `animate-pulseGreen ring-1 ring-[#3FAF7A]/20${isNew ? ' animate-slideInLeft' : ''}`
          : 'hover:bg-[#F9F9F9]'
      }`}
    >
      <div className="flex items-center gap-2 shrink-0 mt-0.5" title={dot.label}>
        <span className={`w-2 h-2 rounded-full ${dot.color}`} />
      </div>
      <div className="flex-1 min-w-0">
        <span className="text-[13px] font-medium text-[#333333]">{field.name}</span>
        {field.mock_value && (
          <span className="text-[13px] text-[#999999] ml-1.5">&mdash; {field.mock_value}</span>
        )}
      </div>
    </div>
  )
}

// ─── History Timeline Component ──────────────────────────────────────────────

function HistoryTimeline({ revisions, loading }: { revisions: RevisionEntry[]; loading: boolean }) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-32 text-sm text-[#999999]">
        Loading history...
      </div>
    )
  }

  if (revisions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-32 text-center">
        <History className="w-5 h-5 text-[#CCCCCC] mb-2" />
        <p className="text-sm text-[#999999]">No changes recorded yet</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {revisions.map((rev, i) => {
        const badgeConfig = REVISION_BADGE[rev.diff_summary?.includes('Resolved') ? 'question_resolved' :
          rev.diff_summary?.includes('Escalated') ? 'question_escalated' :
          rev.diff_summary?.includes('AI refined') ? 'refine_chat_tool' : 'chat_tool'] || REVISION_BADGE.chat_tool
        const BadgeIcon = badgeConfig.icon
        const timeAgo = formatTimeAgo(rev.created_at)

        // Extract Q&A data if present
        const qResolved = rev.changes?.question_resolved as { question?: string; answer?: string } | undefined
        const qEscalated = rev.changes?.question_escalated as { question?: string; escalated_to?: string } | undefined

        return (
          <div key={i} className="flex gap-3">
            {/* Timeline line + dot */}
            <div className="flex flex-col items-center shrink-0">
              <div className={`w-2 h-2 rounded-full mt-1.5 ${i === 0 ? 'bg-[#3FAF7A]' : 'bg-[#E5E5E5]'}`} />
              {i < revisions.length - 1 && <div className="w-px flex-1 bg-[#E5E5E5] mt-1" />}
            </div>

            {/* Content */}
            <div className="flex-1 pb-3">
              <div className="flex items-center gap-2 mb-1">
                <span className={`inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded-full ${badgeConfig.color}`}>
                  <BadgeIcon className="w-3 h-3" />
                  {badgeConfig.label}
                </span>
                <span className="text-[10px] text-[#999999]">{timeAgo}</span>
                {rev.created_by && (
                  <span className="text-[10px] text-[#BBBBBB]">by {rev.created_by}</span>
                )}
              </div>

              {/* Diff summary */}
              {rev.diff_summary && !qResolved && !qEscalated && (
                <p className="text-[12px] text-[#666666]">{rev.diff_summary}</p>
              )}

              {/* Q&A inline */}
              {qResolved && (
                <div className="mt-1 bg-[#F0FFF4] rounded-lg px-3 py-2">
                  <p className="text-[12px] text-[#666666] mb-1">Q: {qResolved.question}</p>
                  <p className="text-[12px] text-[#333333] font-medium">A: {qResolved.answer}</p>
                </div>
              )}

              {/* Escalation inline */}
              {qEscalated && (
                <div className="mt-1 bg-[#FFFBF0] rounded-lg px-3 py-2">
                  <p className="text-[12px] text-[#666666]">{qEscalated.question}</p>
                  <p className="text-[11px] text-[#A08050] mt-0.5">Sent to {qEscalated.escalated_to}</p>
                </div>
              )}

              {/* Field-level changes (expandable) */}
              {rev.changes && !qResolved && !qEscalated && <FieldChanges changes={rev.changes} />}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ─── Field Changes (collapsible) ─────────────────────────────────────────────

function FieldChanges({ changes }: { changes: Record<string, unknown> }) {
  const [expanded, setExpanded] = useState(false)
  const fieldKeys = Object.keys(changes).filter(k => k !== 'question_resolved' && k !== 'question_escalated')
  if (fieldKeys.length === 0) return null

  return (
    <div className="mt-1">
      <button
        onClick={() => setExpanded(!expanded)}
        className="text-[11px] text-[#999999] hover:text-[#666666]"
      >
        {expanded ? 'Hide' : 'Show'} {fieldKeys.length} field change{fieldKeys.length !== 1 ? 's' : ''}
      </button>
      {expanded && (
        <div className="mt-1 space-y-1">
          {fieldKeys.map(key => {
            const change = changes[key] as { old?: unknown; new?: unknown } | undefined
            if (!change) return null
            const oldStr = typeof change.old === 'string' ? change.old : JSON.stringify(change.old)
            const newStr = typeof change.new === 'string' ? change.new : JSON.stringify(change.new)
            return (
              <div key={key} className="text-[11px] bg-[#F4F4F4] rounded px-2 py-1.5">
                <span className="font-medium text-[#666666]">{key}:</span>{' '}
                {oldStr && <span className="text-[#CC4444] line-through">{truncate(oldStr, 60)}</span>}
                {oldStr && newStr && <span className="text-[#999999]"> → </span>}
                {newStr && <span className="text-[#25785A]">{truncate(newStr, 60)}</span>}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatTimeAgo(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHr = Math.floor(diffMin / 60)
  if (diffHr < 24) return `${diffHr}h ago`
  const diffDays = Math.floor(diffHr / 24)
  if (diffDays === 1) return 'yesterday'
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function truncate(str: string, max: number): string {
  return str.length > max ? str.slice(0, max) + '...' : str
}
