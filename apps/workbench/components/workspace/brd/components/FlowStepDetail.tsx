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
  ChevronDown,
  ChevronRight,
  Target,
  Zap,
  Shield,
  Bot,
  ArrowRight,
  ArrowLeft,
  Heart,
  Trophy,
  Compass,
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

/** Shallow compare two arrays of primitives or objects by length + JSON per-item. */
function arraysChanged(a: unknown[] | undefined | null, b: unknown[] | undefined | null): boolean {
  if (a === b) return false
  if (!a || !b || a.length !== b.length) return true
  for (let i = 0; i < a.length; i++) {
    if (a[i] !== b[i] && JSON.stringify(a[i]) !== JSON.stringify(b[i])) return true
  }
  return false
}

const ENTITY_CONFIG: Record<string, { icon: typeof GitBranch; label: string; color: string; bg: string }> = {
  workflow: { icon: GitBranch, label: 'Workflow', color: 'text-[#0A1E2F]', bg: 'bg-[#0A1E2F]/5 border-[#0A1E2F]/15' },
  feature: { icon: Box, label: 'Feature', color: 'text-[#25785A]', bg: 'bg-[#3FAF7A]/5 border-[#3FAF7A]/15' },
  data_entity: { icon: Database, label: 'Data Entity', color: 'text-[#0D2A35]', bg: 'bg-[#0D2A35]/5 border-[#0D2A35]/15' },
}

// ─── Beat config — green monochrome palette with explicit icon colors ────────
const BEAT_CONFIG: Record<string, { verb: string; icon: typeof Target; iconColor: string; bg: string; border: string }> = {
  captured: { verb: 'User provides', icon: Target, iconColor: 'text-[#25785A]', bg: 'bg-[#3FAF7A]/5', border: 'border-[#3FAF7A]/15' },
  computed: { verb: 'System generates', icon: Zap, iconColor: 'text-[#3FAF7A]', bg: 'bg-[#3FAF7A]/8', border: 'border-[#3FAF7A]/20' },
  displayed: { verb: 'Shows', icon: FileSearch, iconColor: 'text-[#3FAF7A]/60', bg: 'bg-[#3FAF7A]/3', border: 'border-[#3FAF7A]/10' },
}

// ─── Revision badge config ───────────────────────────────────────────────────
const REVISION_BADGE: Record<string, { label: string; color: string; icon: typeof Sparkles }> = {
  chat_tool: { label: 'Updated', color: 'bg-[#3FAF7A]/10 text-[#25785A]', icon: CheckCircle2 },
  refine_chat_tool: { label: 'AI Refined', color: 'bg-[#0A1E2F]/10 text-[#0A1E2F]', icon: Sparkles },
  question_resolved: { label: 'Q&A', color: 'bg-[#3FAF7A]/10 text-[#25785A]', icon: MessageCircle },
  question_escalated: { label: 'Escalated', color: 'bg-[#0A1E2F]/10 text-[#0A1E2F]', icon: ArrowUpRight },
}

interface EvidenceFile {
  id: string
  filename: string
  fileType: string
  status: string
  quote?: string
  attribution?: string
}

// Map updated field names → which tab they belong to
const FIELD_TAB_MAP: Record<string, TabId> = {
  ai_config: 'ai',
  success_criteria: 'success',
  pain_points_addressed: 'success',
  goals_addressed: 'success',
  linked_feature_ids: 'success',
  linked_workflow_ids: 'success',
  linked_data_entity_ids: 'success',
}

interface FlowStepDetailProps {
  step: StepDetail | null
  loading: boolean
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
  entityLookup?: EntityLookup
  projectId: string
  prevStepTitle?: string
  nextStepTitle?: string
  highlightFields?: string[] | null
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
@keyframes highlightFlash {
  0% { box-shadow: 0 0 0 2px rgba(63, 175, 122, 0.5); }
  100% { box-shadow: 0 0 0 2px transparent; }
}
@keyframes dimOut {
  from { opacity: 1; filter: saturate(1); }
  to { opacity: 0.4; filter: saturate(0.3); }
}
@keyframes dimInPulse {
  0% { opacity: 0.4; filter: saturate(0.3); background-color: rgba(63, 175, 122, 0.08); }
  30% { opacity: 1; filter: saturate(1); background-color: rgba(63, 175, 122, 0.08); }
  100% { opacity: 1; filter: saturate(1); background-color: transparent; }
}
@keyframes previewPulse {
  0% { opacity: 1; }
  40% { opacity: 0.5; }
  60% { opacity: 0.9; }
  80% { opacity: 0.5; }
  100% { opacity: 0.4; filter: saturate(0.3); }
}
.animate-slideInLeft { animation: slideInLeft 0.4s ease-out; }
.animate-pulseGreen { animation: pulseGreen 2.5s ease-out; }
.animate-highlightFlash { animation: previewPulse 0.7s ease-in-out forwards; border-radius: 12px; }
.animate-dimOut { animation: dimOut 0.5s ease-out forwards; }
.animate-dimInPulse { animation: dimInPulse 2.5s ease-out forwards; }
.animate-previewPulse { animation: previewPulse 0.7s ease-in-out forwards; }
`

type TabId = 'experience' | 'success' | 'ai' | 'history'

export function FlowStepDetail({ step, loading, onConfirm, onNeedsReview, entityLookup, projectId, prevStepTitle, nextStepTitle, highlightFields }: FlowStepDetailProps) {
  const [evidenceFiles, setEvidenceFiles] = useState<EvidenceFile[]>([])
  const [activeTab, setActiveTab] = useState<TabId>('experience')
  const [revisions, setRevisions] = useState<RevisionEntry[]>([])
  const [revisionsLoading, setRevisionsLoading] = useState(false)
  const [dataFieldsExpanded, setDataFieldsExpanded] = useState(false)

  // ─── Change highlighting state ──────────────────────────────────────────────
  const prevStepRef = useRef<StepDetail | null>(null)
  const [changedFields, setChangedFields] = useState<Set<string>>(new Set())
  const [animPhase, setAnimPhase] = useState<'idle' | 'dimming' | 'updating'>('idle')

  useEffect(() => {
    if (!step || !prevStepRef.current || step.id !== prevStepRef.current.id) {
      prevStepRef.current = step
      return
    }
    const prev = prevStepRef.current
    const changed = new Set<string>()

    if (step.goal !== prev.goal) changed.add('goal')
    if (arraysChanged(step.actors, prev.actors)) changed.add('actors')
    if (arraysChanged(step.information_fields, prev.information_fields)) {
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
    if (arraysChanged(step.open_questions, prev.open_questions)) changed.add('questions')
    if (step.mock_data_narrative !== prev.mock_data_narrative) changed.add('narrative')
    if (arraysChanged(step.success_criteria, prev.success_criteria)) changed.add('success_criteria')
    if (arraysChanged(step.pain_points_addressed, prev.pain_points_addressed)) changed.add('pain_points')
    if (arraysChanged(step.goals_addressed, prev.goals_addressed)) changed.add('goals_addressed')
    if (step.ai_config !== prev.ai_config && JSON.stringify(step.ai_config) !== JSON.stringify(prev.ai_config)) changed.add('ai_config')

    prevStepRef.current = step
    if (changed.size > 0) {
      // Phase 1: dim out
      setChangedFields(changed)
      setAnimPhase('dimming')
      setTimeout(() => {
        // Phase 2: update highlight
        setAnimPhase('updating')
        setTimeout(() => {
          setAnimPhase('idle')
          setChangedFields(new Set())
        }, 3000)
      }, 500)
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
    setActiveTab('experience')
    setDataFieldsExpanded(false)
  }, [step?.id])

  // Auto-switch tab when highlightFields arrives from chat tool completion
  useEffect(() => {
    if (!highlightFields?.length) return
    // Find which tab the first updated field belongs to (default: experience)
    for (const field of highlightFields) {
      const tab = FIELD_TAB_MAP[field]
      if (tab) {
        setActiveTab(tab)
        return
      }
    }
    setActiveTab('experience')
  }, [highlightFields])

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

  // Group info fields by type for narrative beats
  const capturedFields = infoFields.filter(f => f.type === 'captured')
  const computedFields = infoFields.filter(f => f.type === 'computed')
  const displayedFields = infoFields.filter(f => f.type === 'displayed')

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

  const tabs: { id: TabId; label: string; icon: typeof FileSearch }[] = [
    { id: 'experience', label: 'Experience', icon: FileSearch },
    { id: 'success', label: 'Success', icon: Trophy },
    { id: 'ai', label: 'AI', icon: Bot },
    { id: 'history', label: 'History', icon: History },
  ]

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

      {/* 4-tab toggle */}
      <div className="flex gap-1 bg-[#F4F4F4] rounded-lg p-0.5 w-fit">
        {tabs.map(tab => {
          const Icon = tab.icon
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                activeTab === tab.id
                  ? 'bg-white text-[#333333] shadow-sm'
                  : 'text-[#999999] hover:text-[#666666]'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          )
        })}
      </div>

      {activeTab === 'experience' ? (
        <ExperienceTab
          step={step}
          infoFields={infoFields}
          capturedFields={capturedFields}
          computedFields={computedFields}
          displayedFields={displayedFields}
          openQuestions={openQuestions}
          escalatedQuestions={escalatedQuestions}
          resolvedQuestions={resolvedQuestions}
          changedFields={changedFields}
          animPhase={animPhase}
          evidenceFiles={evidenceFiles}
          fileIcon={fileIcon}
          prevStepTitle={prevStepTitle}
          nextStepTitle={nextStepTitle}
          dataFieldsExpanded={dataFieldsExpanded}
          setDataFieldsExpanded={setDataFieldsExpanded}
          highlightFields={highlightFields}
        />
      ) : activeTab === 'success' ? (
        <SuccessTab
          step={step}
          linkedEntities={linkedEntities}
          changedFields={changedFields}
          animPhase={animPhase}
          highlightFields={highlightFields}
        />
      ) : activeTab === 'ai' ? (
        <AITab step={step} changedFields={changedFields} animPhase={animPhase} highlightFields={highlightFields} />
      ) : (
        <HistoryTimeline revisions={revisions} loading={revisionsLoading} />
      )}
    </div>
  )
}

// ─── Experience Tab ─────────────────────────────────────────────────────────

function ExperienceTab({
  step,
  infoFields,
  capturedFields,
  computedFields,
  displayedFields,
  openQuestions,
  escalatedQuestions,
  resolvedQuestions,
  changedFields,
  animPhase,
  evidenceFiles,
  fileIcon,
  prevStepTitle,
  nextStepTitle,
  dataFieldsExpanded,
  setDataFieldsExpanded,
  highlightFields,
}: {
  step: StepDetail
  infoFields: InformationField[]
  capturedFields: InformationField[]
  computedFields: InformationField[]
  displayedFields: InformationField[]
  openQuestions: FlowOpenQuestion[]
  escalatedQuestions: FlowOpenQuestion[]
  resolvedQuestions: FlowOpenQuestion[]
  changedFields: Set<string>
  animPhase: 'idle' | 'dimming' | 'updating'
  evidenceFiles: EvidenceFile[]
  fileIcon: (fileType: string) => React.ReactNode
  prevStepTitle?: string
  nextStepTitle?: string
  dataFieldsExpanded: boolean
  setDataFieldsExpanded: (v: boolean) => void
  highlightFields?: string[] | null
}) {
  const hlSet = new Set(highlightFields || [])
  const phaseClass = (field: string) => {
    if (!changedFields.has(field) && !hlSet.has(field)) return ''
    if (animPhase === 'dimming') return 'animate-dimOut'
    if (animPhase === 'updating') return 'animate-dimInPulse'
    return ''
  }
  return (
    <>
      {/* Goal box */}
      <div className={`bg-[#0A1E2F] rounded-xl p-4 transition-all duration-700 ${phaseClass('goal') || (hlSet.has('goal') ? 'animate-highlightFlash' : '')}${step.confidence_impact && step.confidence_impact > 0 ? ' ring-2 ring-[#0A1E2F]/30' : ''}`}>
        <div className="flex items-center justify-between mb-1">
          <div className="text-[10px] uppercase tracking-wider text-white/50">Goal</div>
          {step.confidence_impact != null && step.confidence_impact > 0 && (
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#0A1E2F]/10 text-white/60 font-medium">
              {Math.round(step.confidence_impact * 100)}% links stale
            </span>
          )}
        </div>
        <p className="text-sm text-white/90 leading-relaxed">{step.goal}</p>
      </div>

      {/* Background narrative (provenance) */}
      {step.background_narrative && (
        <div className="text-xs text-[#999999] leading-relaxed px-1 -mt-2">
          {step.background_narrative}
        </div>
      )}

      {/* Needs review indicator */}
      {step.confirmation_status === 'needs_review' && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[#0A1E2F]/5 border border-[#0A1E2F]/15 text-xs text-[#0A1E2F]/70">
          <AlertCircle className="w-3.5 h-3.5 shrink-0" />
          <span>This step was demoted to needs review — linked entities have changed.</span>
        </div>
      )}

      {/* Narrative Beats — info fields as story beats */}
      {infoFields.length > 0 && (
        <div>
          {/* Mock data narrative as featured block */}
          {step.mock_data_narrative && (
            <div className={`bg-[#F8F6F0] border border-[#E8E4D8] rounded-xl p-4 mb-4 transition-all duration-700 ${
              phaseClass('narrative') || (hlSet.has('mock_data_narrative') ? 'animate-highlightFlash' : '')
            }`}>
              <p className="text-[13px] text-[#555555] leading-relaxed italic">
                {step.mock_data_narrative}
              </p>
            </div>
          )}

          <h3 className="text-[11px] font-semibold uppercase tracking-wider text-[#999999] mb-3">
            Narrative Beats
          </h3>

          {(() => {
            const allBeats: { field?: InformationField; beatType: 'captured' | 'computed' | 'displayed' | 'pattern'; actors?: string[] }[] = [
              ...capturedFields.map(f => ({ field: f, beatType: 'captured' as const, actors: step.actors })),
              ...computedFields.map(f => ({ field: f, beatType: 'computed' as const })),
              ...(step.implied_pattern ? [{ beatType: 'pattern' as const }] : []),
              ...displayedFields.map(f => ({ field: f, beatType: 'displayed' as const })),
            ]
            return (
              <div className="space-y-0">
                {allBeats.map((beat, i) => {
                  const isLast = i === allBeats.length - 1
                  if (beat.beatType === 'pattern') {
                    return (
                      <div key="pattern" className="flex gap-3">
                        <div className="flex flex-col items-center shrink-0" style={{ width: 36 }}>
                          <div className="w-[34px] h-[34px] rounded-lg bg-[#0A1E2F]/8 flex items-center justify-center">
                            <Layout className="w-4 h-4 text-[#0A1E2F]/50" />
                          </div>
                          {!isLast && <div className="w-0.5 flex-1 bg-[#3FAF7A]/15 mt-0.5" />}
                        </div>
                        <div className="flex-1 py-2 group">
                          <div className="text-[10px] font-bold uppercase tracking-wider text-[#999999] mb-0.5">Layout</div>
                          <span className="text-[12px] text-[#666666]">
                            Renders as a <span className="font-medium text-[#0A1E2F]">{step.implied_pattern}</span>
                          </span>
                        </div>
                      </div>
                    )
                  }
                  return (
                    <NarrativeBeat
                      key={`${beat.beatType}-${beat.field!.name}`}
                      field={beat.field!}
                      beatType={beat.beatType as 'captured' | 'computed' | 'displayed'}
                      actors={beat.actors}
                      highlighted={changedFields.has(`field:${beat.field!.name}`)}
                      isNew={changedFields.has(`field:${beat.field!.name}`) && changedFields.has('info_fields')}
                      isLast={isLast}
                    />
                  )
                })}
              </div>
            )
          })()}
        </div>
      )}

      {/* Step connections */}
      {(prevStepTitle || nextStepTitle) && (
        <div className="flex items-center gap-3 px-3 py-2 rounded-lg bg-[#F4F4F4]/60 text-[12px] text-[#999999]">
          {prevStepTitle && (
            <span className="flex items-center gap-1">
              <ArrowLeft className="w-3 h-3" /> from {prevStepTitle}
            </span>
          )}
          {prevStepTitle && nextStepTitle && <span className="text-[#E5E5E5]">|</span>}
          {nextStepTitle && (
            <span className="flex items-center gap-1">
              feeds {nextStepTitle} <ArrowRight className="w-3 h-3" />
            </span>
          )}
        </div>
      )}

      {/* Evidence & Uploads */}
      {evidenceFiles.length > 0 && (
        <div>
          <h3 className="text-[11px] font-semibold uppercase tracking-wider text-[#999999] mb-2">
            Client References ({evidenceFiles.length})
          </h3>
          <div className="flex flex-wrap gap-2">
            {evidenceFiles.map(file => (
              <div
                key={file.id}
                className={`flex items-start gap-2 px-3 py-2 bg-white border border-[#E5E5E5] rounded-lg ${file.quote ? 'w-full' : ''}`}
              >
                <div className="w-7 h-7 rounded-md bg-[#F4F4F4] flex items-center justify-center text-[#666666] shrink-0">
                  {fileIcon(file.fileType)}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-[12px] font-medium text-[#333333] truncate max-w-[200px]">{file.filename}</div>
                  {file.quote && (
                    <>
                      <p className="text-[12px] text-[#666666] italic leading-snug mt-1 line-clamp-3">{file.quote}</p>
                      {file.attribution && (
                        <p className="text-[10px] text-[#999999] mt-0.5">&mdash; {file.attribution}</p>
                      )}
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Things to Explore — reframed open questions */}
      {openQuestions.length > 0 && (
        <div className={phaseClass('questions') || (hlSet.has('open_questions') ? 'animate-highlightFlash' : '')}>
          <h3 className="text-[11px] font-semibold uppercase tracking-wider text-[#999999] mb-2">
            Things to Explore ({openQuestions.length})
          </h3>
          <div className="space-y-2">
            {openQuestions.map((q, i) => (
              <div key={i} className="border border-[#E5E5E5] bg-[#FAFAFA] rounded-xl p-3">
                <div className="flex items-start gap-2">
                  <Compass className="w-4 h-4 text-[#0A1E2F]/40 shrink-0 mt-0.5" />
                  <div className="flex-1">
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
              <div key={i} className="border-l-[3px] border-[#0A1E2F]/30 bg-[#0A1E2F]/3 rounded-r-lg p-3">
                <div className="flex items-start gap-2">
                  <ArrowUpRight className="w-4 h-4 text-[#0A1E2F]/40 shrink-0 mt-0.5" />
                  <div>
                    <p className="text-[13px] text-[#666666]">{q.question}</p>
                    {q.escalated_to && (
                      <p className="text-xs text-[#0A1E2F]/60 mt-1 flex items-center gap-1">
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

      {/* Collapsed data fields */}
      {infoFields.length > 0 && (
        <div>
          <button
            onClick={() => setDataFieldsExpanded(!dataFieldsExpanded)}
            className="flex items-center gap-1.5 text-[11px] font-medium text-[#999999] hover:text-[#666666]"
          >
            {dataFieldsExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            {dataFieldsExpanded ? 'Hide' : 'Show'} {infoFields.length} data field{infoFields.length !== 1 ? 's' : ''}
          </button>
          {dataFieldsExpanded && (
            <div className="mt-2 space-y-1">
              {infoFields.map((field) => (
                <FieldRow
                  key={field.name}
                  field={field}
                  highlighted={changedFields.has(`field:${field.name}`)}
                  isNew={changedFields.has(`field:${field.name}`) && changedFields.has('info_fields')}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </>
  )
}

// ─── Narrative Beat Component ────────────────────────────────────────────────

function NarrativeBeat({
  field,
  beatType,
  actors,
  highlighted,
  isNew,
  isLast,
}: {
  field: InformationField
  beatType: 'captured' | 'computed' | 'displayed'
  actors?: string[]
  highlighted: boolean
  isNew: boolean
  isLast?: boolean
}) {
  const config = BEAT_CONFIG[beatType]
  const Icon = config.icon

  return (
    <div
      className={`flex gap-3 transition-all duration-500 ${
        highlighted
          ? `animate-pulseGreen${isNew ? ' animate-slideInLeft' : ''}`
          : ''
      }`}
    >
      {/* Icon column with connector */}
      <div className="flex flex-col items-center shrink-0" style={{ width: 36 }}>
        <div className={`w-[34px] h-[34px] rounded-lg ${config.bg} ${config.border} border flex items-center justify-center`}>
          <Icon className={`w-4 h-4 ${config.iconColor}`} />
        </div>
        {!isLast && <div className="w-0.5 flex-1 bg-[#3FAF7A]/15 mt-0.5" />}
      </div>

      {/* Content */}
      <div className="flex-1 py-1.5 group-hover:bg-[#F9F9F9] rounded-lg">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-[10px] font-bold text-[#999999] uppercase tracking-wider">
            {config.verb}
          </span>
          {beatType === 'captured' && actors?.length ? (
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-[#0A1E2F]/8 text-[#0A1E2F]">
              {actors[0]}
            </span>
          ) : null}
        </div>
        <div className="flex items-baseline gap-1.5">
          <span className="text-[13px] font-medium text-[#333333]">{field.name}</span>
          {field.mock_value && (
            <span className="text-[12px] text-[#999999]">&mdash; {field.mock_value}</span>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Success Tab ─────────────────────────────────────────────────────────────

function SuccessTab({
  step,
  linkedEntities,
  changedFields,
  animPhase,
  highlightFields,
}: {
  step: StepDetail
  linkedEntities: { type: string; id: string; name: string }[]
  changedFields: Set<string>
  animPhase: 'idle' | 'dimming' | 'updating'
  highlightFields?: string[] | null
}) {
  const hlSet = new Set(highlightFields || [])
  const phaseClass = (field: string) => {
    if (!changedFields.has(field) && !hlSet.has(field)) return ''
    if (animPhase === 'dimming') return 'animate-dimOut'
    if (animPhase === 'updating') return 'animate-dimInPulse'
    return ''
  }
  const painPoints = (step.pain_points_addressed || []).map(pp =>
    typeof pp === 'string' ? { text: pp } : pp
  )
  const goals = step.goals_addressed || []
  const criteria = step.success_criteria || []

  const isEmpty = painPoints.length === 0 && goals.length === 0 && criteria.length === 0 && linkedEntities.length === 0

  if (isEmpty) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-center">
        <Trophy className="w-6 h-6 text-[#CCCCCC] mb-3" />
        <p className="text-sm text-[#999999] mb-1">No success criteria yet</p>
        <p className="text-xs text-[#BBBBBB]">Use the chat to discuss what makes this step successful</p>
      </div>
    )
  }

  return (
    <>
      {/* Solves For — pain points */}
      {painPoints.length > 0 && (
        <div className={phaseClass('pain_points') || (hlSet.has('pain_points_addressed') ? 'animate-highlightFlash' : '')}>
          <h3 className="text-[11px] font-semibold uppercase tracking-wider text-[#999999] mb-2">
            Solves For
          </h3>
          <div className="space-y-2">
            {painPoints.map((pp, i) => (
              <div
                key={i}
                className="border border-[#E5E5E5] bg-white rounded-xl p-3 animate-slideInLeft"
                style={{ animationDelay: `${i * 60}ms` }}
              >
                <div className="flex items-start gap-2">
                  <Heart className="w-4 h-4 text-[#25785A] shrink-0 mt-0.5" />
                  <div>
                    <p className="text-[13px] text-[#333333]">{pp.text}</p>
                    {pp.persona && (
                      <span className="inline-block text-[10px] px-2 py-0.5 rounded-full bg-[#0A1E2F]/5 text-[#0A1E2F] mt-1.5">
                        {pp.persona}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Achieves — goals */}
      {goals.length > 0 && (
        <div className={phaseClass('goals_addressed') || (hlSet.has('goals_addressed') ? 'animate-highlightFlash' : '')}>
          <h3 className="text-[11px] font-semibold uppercase tracking-wider text-[#999999] mb-2">
            Achieves
          </h3>
          <div className="flex flex-wrap gap-2">
            {goals.map((goal, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1.5 text-[12px] px-3 py-1.5 rounded-full bg-[#3FAF7A]/10 text-[#25785A] font-medium"
              >
                <CheckCircle2 className="w-3 h-3" />
                {goal}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* What Makes This Step Successful — criteria */}
      {criteria.length > 0 && (
        <div className={phaseClass('success_criteria') || (hlSet.has('success_criteria') ? 'animate-highlightFlash' : '')}>
          <h3 className="text-[11px] font-semibold uppercase tracking-wider text-[#999999] mb-2">
            What Makes This Step Successful
          </h3>
          <div className="space-y-1.5">
            {criteria.map((c, i) => (
              <div key={i} className="flex items-start gap-2 py-1.5 px-3 rounded-lg hover:bg-[#F9F9F9]">
                <Target className="w-4 h-4 text-[#3FAF7A] shrink-0 mt-0.5" />
                <span className="text-[13px] text-[#333333]">{c}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Connected Entities */}
      {linkedEntities.length > 0 && (
        <div>
          <h3 className="text-[11px] font-semibold uppercase tracking-wider text-[#999999] mb-2">
            Connected Entities
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
    </>
  )
}

// ─── AI Tab ──────────────────────────────────────────────────────────────────

function AITab({
  step,
  changedFields,
  animPhase,
  highlightFields,
}: {
  step: StepDetail
  changedFields: Set<string>
  animPhase: 'idle' | 'dimming' | 'updating'
  highlightFields?: string[] | null
}) {
  const hlSet = new Set(highlightFields || [])
  const aiConfig = step.ai_config

  const phaseClass = (() => {
    if (!changedFields.has('ai_config') && !hlSet.has('ai_config')) return ''
    if (animPhase === 'dimming') return 'animate-dimOut'
    if (animPhase === 'updating') return 'animate-dimInPulse'
    return ''
  })()

  if (!aiConfig) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-center">
        <Bot className="w-6 h-6 text-[#CCCCCC] mb-3" />
        <p className="text-sm font-medium text-[#666666] mb-1">Does this step use AI?</p>
        <p className="text-xs text-[#999999] max-w-xs mb-4">
          If this step involves AI-driven behavior — recommendations, scoring, generation — define the role, behaviors, and guardrails.
        </p>
        <p className="text-xs text-[#BBBBBB]">
          Use the chat to say &quot;Enable AI for this step&quot;
        </p>
      </div>
    )
  }

  const role = aiConfig.role || aiConfig.ai_role

  return (
    <div className={`space-y-0 ${phaseClass}`}>
      {/* Stage 1 — Data In */}
      <div className="flex gap-3">
        <div className="flex flex-col items-center shrink-0" style={{ width: 36 }}>
          <div className="w-[34px] h-[34px] rounded-lg bg-[#0A1E2F]/8 flex items-center justify-center">
            <Database className="w-4 h-4 text-[#0A1E2F]/50" />
          </div>
          <div className="w-0.5 flex-1 bg-[#3FAF7A]/20 mt-0.5" />
        </div>
        <div className="flex-1 pb-4">
          <div className="text-[10px] font-bold uppercase tracking-wider text-[#999999] mb-1.5">Data In</div>
          <div className="bg-[#0A1E2F] rounded-xl p-4">
            <p className="text-sm text-white/90 leading-relaxed">
              {role || 'No role defined'}
            </p>
          </div>
        </div>
      </div>

      {/* Stage 2 — What the AI Does */}
      <div className="flex gap-3">
        <div className="flex flex-col items-center shrink-0" style={{ width: 36 }}>
          <div className="w-[34px] h-[34px] rounded-lg bg-[#3FAF7A]/10 flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-[#3FAF7A]" />
          </div>
          {(aiConfig.confidence_display || aiConfig.fallback) && (
            <div className="w-0.5 flex-1 bg-[#3FAF7A]/20 mt-0.5" />
          )}
        </div>
        <div className="flex-1 pb-4">
          <div className="text-[10px] font-bold uppercase tracking-wider text-[#999999] mb-1.5">What the AI Does</div>

          {/* Behaviors */}
          {aiConfig.behaviors && aiConfig.behaviors.length > 0 && (
            <div className="space-y-1.5 mb-3">
              {aiConfig.behaviors.map((b, i) => (
                <div key={i} className="flex items-start gap-2 py-1.5 px-3 rounded-lg bg-[#3FAF7A]/5">
                  <Zap className="w-3.5 h-3.5 text-[#3FAF7A] shrink-0 mt-0.5" />
                  <span className="text-[13px] text-[#333333]">{b}</span>
                </div>
              ))}
            </div>
          )}

          {/* Guardrails sub-section */}
          {aiConfig.guardrails && aiConfig.guardrails.length > 0 && (
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-wider text-[#999999] mb-1.5 mt-1">Guardrails</div>
              <div className="space-y-1.5">
                {aiConfig.guardrails.map((g, i) => (
                  <div key={i} className="flex items-start gap-2 py-1.5 px-3 rounded-lg bg-[#0A1E2F]/3">
                    <Shield className="w-3.5 h-3.5 text-[#0A1E2F]/50 shrink-0 mt-0.5" />
                    <span className="text-[13px] text-[#333333]">{g}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Stage 3 — What Comes Out */}
      {(aiConfig.confidence_display || aiConfig.fallback) && (
        <div className="flex gap-3">
          <div className="flex flex-col items-center shrink-0" style={{ width: 36 }}>
            <div className="w-[34px] h-[34px] rounded-lg bg-[#3FAF7A]/15 flex items-center justify-center">
              <ArrowRight className="w-4 h-4 text-[#25785A]" />
            </div>
            {(step.success_criteria?.length || step.pain_points_addressed?.length) ? (
              <div className="w-0.5 flex-1 bg-[#3FAF7A]/20 mt-0.5" />
            ) : null}
          </div>
          <div className="flex-1 pb-2">
            <div className="text-[10px] font-bold uppercase tracking-wider text-[#999999] mb-1.5">What Comes Out</div>
            {aiConfig.confidence_display && (
              <span className="inline-flex text-[12px] px-2 py-0.5 rounded-full bg-[#3FAF7A]/10 text-[#25785A] font-medium mb-2">
                {aiConfig.confidence_display}
              </span>
            )}
            {aiConfig.fallback && (
              <div className="flex items-start gap-2 py-1.5 px-3 rounded-lg bg-[#F4F4F4] border border-[#E5E5E5] mt-1">
                <Shield className="w-3.5 h-3.5 text-[#999999] shrink-0 mt-0.5" />
                <span className="text-[13px] text-[#666666]">{aiConfig.fallback}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Stage 4 — What Success Looks Like */}
      {(step.success_criteria?.length || step.pain_points_addressed?.length) ? (
        <div className="flex gap-3">
          <div className="flex flex-col items-center shrink-0" style={{ width: 36 }}>
            <div className="w-[34px] h-[34px] rounded-lg bg-[#3FAF7A]/20 flex items-center justify-center">
              <Trophy className="w-4 h-4 text-[#25785A]" />
            </div>
          </div>
          <div className="flex-1 pb-2">
            <div className="text-[10px] font-bold uppercase tracking-wider text-[#999999] mb-1.5">What Success Looks Like</div>
            <div className="space-y-1.5">
              {(step.success_criteria || []).map((c, i) => (
                <div key={`c-${i}`} className="flex items-start gap-2 py-1 px-3 rounded-lg bg-[#3FAF7A]/5">
                  <Target className="w-3.5 h-3.5 text-[#3FAF7A] shrink-0 mt-0.5" />
                  <span className="text-[12px] text-[#333333]">{c}</span>
                </div>
              ))}
              {(step.pain_points_addressed || []).map((pp, i) => {
                const text = typeof pp === 'string' ? pp : pp.text
                const persona = typeof pp === 'string' ? undefined : pp.persona
                return (
                  <div key={`pp-${i}`} className="flex items-start gap-2 py-1 px-3 rounded-lg bg-[#0A1E2F]/3">
                    <Heart className="w-3.5 h-3.5 text-[#25785A] shrink-0 mt-0.5" />
                    <span className="text-[12px] text-[#333333]">
                      {text}{persona && <span className="text-[#999999] ml-1">({persona})</span>}
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      ) : null}
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
                <p className="text-[12px] text-[#666666]">{friendlyDiffSummary(rev.diff_summary)}</p>
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
                <div className="mt-1 bg-[#0A1E2F]/3 rounded-lg px-3 py-2">
                  <p className="text-[12px] text-[#666666]">{qEscalated.question}</p>
                  <p className="text-[11px] text-[#0A1E2F]/60 mt-0.5">Sent to {qEscalated.escalated_to}</p>
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

const HISTORY_FIELD_LABELS: Record<string, string> = {
  ai_config: 'AI Configuration',
  goal: 'Goal',
  title: 'Title',
  actors: 'Actors',
  phase: 'Phase',
  information_fields: 'Information Fields',
  open_questions: 'Open Questions',
  implied_pattern: 'Implied Pattern',
  success_criteria: 'Success Criteria',
  pain_points_addressed: 'Pain Points',
  goals_addressed: 'Goals',
  mock_data_narrative: 'Preview Narrative',
  linked_feature_ids: 'Linked Features',
  linked_workflow_ids: 'Linked Workflows',
  linked_data_entity_ids: 'Linked Data Entities',
  mock_value: 'Mock Value',
  confidence: 'Confidence',
  background_narrative: 'Background Narrative',
  generation_version: 'Generation Version',
}

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
                <span className="font-medium text-[#666666]">{HISTORY_FIELD_LABELS[key] || key.replace(/_/g, ' ')}:</span>{' '}
                {oldStr && <span className="text-[#CC4444] line-through">{truncate(oldStr, 60)}</span>}
                {oldStr && newStr && <span className="text-[#999999]"> &rarr; </span>}
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

/** Transform raw diff_summary like "Updated ai_config, information_fields" into friendly labels. */
const DIFF_FIELD_MAP: Record<string, string> = {
  ai_config: 'AI flow',
  information_fields: 'information fields',
  implied_pattern: 'implied pattern',
  mock_data_narrative: 'experience narrative',
  open_questions: 'open questions',
  success_criteria: 'success criteria',
  pain_points_addressed: 'pain points',
  goals_addressed: 'goals',
  linked_feature_ids: 'linked features',
  linked_workflow_ids: 'linked workflows',
  linked_data_entity_ids: 'linked data entities',
  background_narrative: 'background narrative',
}

function friendlyDiffSummary(summary: string): string {
  // Match "Updated field1, field2, field3" pattern
  const match = summary.match(/^Updated\s+(.+)$/)
  if (!match) return summary
  const fields = match[1].split(/,\s*/).map(f => DIFF_FIELD_MAP[f.trim()] || f.trim().replace(/_/g, ' '))
  if (fields.length === 1) return `Updated ${fields[0]}`
  if (fields.length === 2) return `Updated ${fields[0]} and ${fields[1]}`
  return `Updated ${fields.slice(0, -1).join(', ')}, and ${fields[fields.length - 1]}`
}
