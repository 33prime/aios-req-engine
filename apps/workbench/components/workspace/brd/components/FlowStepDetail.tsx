'use client'

import { useState, useEffect } from 'react'
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
} from 'lucide-react'
import { ConfirmActions } from './ConfirmActions'
import type { SolutionFlowStepDetail as StepDetail, InformationField, FlowOpenQuestion } from '@/types/workspace'
import type { EntityLookup } from './SolutionFlowModal'
import { getDocumentStatus } from '@/lib/api'

const FIELD_TYPE_BADGE: Record<string, { label: string; color: string }> = {
  captured: { label: 'Captured', color: 'bg-[#3FAF7A]/10 text-[#25785A]' },
  displayed: { label: 'Displayed', color: 'bg-[#0A1E2F]/10 text-[#0A1E2F]' },
  computed: { label: 'Computed', color: 'bg-[#0D2A35]/10 text-[#0D2A35]' },
}

const CONFIDENCE_BADGE: Record<string, { label: string; color: string }> = {
  known: { label: 'Known', color: 'bg-[#3FAF7A]/10 text-[#25785A]' },
  inferred: { label: 'Inferred', color: 'bg-[#0A1E2F]/10 text-[#0A1E2F]' },
  guess: { label: 'Guess', color: 'bg-[#EDE8D5] text-[#8B7355]' },
  unknown: { label: 'Unknown', color: 'bg-[#F4F4F4] text-[#999999]' },
}

const ENTITY_CONFIG: Record<string, { icon: typeof GitBranch; label: string; color: string; bg: string }> = {
  workflow: { icon: GitBranch, label: 'Workflow', color: 'text-[#0A1E2F]', bg: 'bg-[#0A1E2F]/5 border-[#0A1E2F]/15' },
  feature: { icon: Box, label: 'Feature', color: 'text-[#25785A]', bg: 'bg-[#3FAF7A]/5 border-[#3FAF7A]/15' },
  data_entity: { icon: Database, label: 'Data Entity', color: 'text-[#0D2A35]', bg: 'bg-[#0D2A35]/5 border-[#0D2A35]/15' },
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
}

export function FlowStepDetail({ step, loading, onConfirm, onNeedsReview, entityLookup }: FlowStepDetailProps) {
  const [evidenceFiles, setEvidenceFiles] = useState<EvidenceFile[]>([])

  // Load evidence file metadata
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
      {/* Header with confirm actions */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-[#333333]">{step.title}</h2>
          <div className="flex items-center gap-2 mt-1">
            {step.actors.map(actor => (
              <span key={actor} className="text-xs px-2 py-0.5 rounded-full bg-[#0A1E2F]/8 text-[#0A1E2F]">
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

      {/* Goal box */}
      <div className="bg-[#0A1E2F] rounded-xl p-4">
        <div className="text-[10px] uppercase tracking-wider text-white/50 mb-1">Goal</div>
        <p className="text-sm text-white/90 leading-relaxed">{step.goal}</p>
      </div>

      {/* Linked Entities — pill-style chips with resolved names */}
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

      {/* Information Fields table */}
      {infoFields.length > 0 && (
        <div>
          <h3 className="text-[11px] font-semibold uppercase tracking-wider text-[#999999] mb-2">
            Information Fields ({infoFields.length})
          </h3>
          <div className="bg-white border border-[#E5E5E5] rounded-xl overflow-hidden">
            <table className="w-full text-[13px]">
              <thead>
                <tr className="bg-[#F4F4F4] text-[10px] uppercase tracking-wider text-[#999999]">
                  <th className="text-left px-3 py-2 font-medium">Field</th>
                  <th className="text-left px-3 py-2 font-medium">Type</th>
                  <th className="text-left px-3 py-2 font-medium">Mock Value</th>
                  <th className="text-left px-3 py-2 font-medium">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {infoFields.map((field, i) => {
                  const typeBadge = FIELD_TYPE_BADGE[field.type] || FIELD_TYPE_BADGE.captured
                  const confBadge = CONFIDENCE_BADGE[field.confidence] || CONFIDENCE_BADGE.unknown
                  return (
                    <tr key={i} className="border-t border-[#F4F4F4]">
                      <td className="px-3 py-2 font-medium text-[#333333]">{field.name}</td>
                      <td className="px-3 py-2">
                        <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${typeBadge.color}`}>
                          {typeBadge.label}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-[#666666] font-mono text-xs">{field.mock_value}</td>
                      <td className="px-3 py-2">
                        <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${confBadge.color}`}>
                          {confBadge.label}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Mock Data Narrative */}
      {step.mock_data_narrative && (
        <div className="bg-[#F4F4F4] border border-[#E5E5E5] rounded-xl p-4">
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
        <div>
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
    </div>
  )
}
