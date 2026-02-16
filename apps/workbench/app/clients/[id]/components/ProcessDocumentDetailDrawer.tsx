'use client'

import { useState, useEffect } from 'react'
import {
  X,
  FileText,
  Users,
  Database,
  GitBranch,
  AlertTriangle,
  Lightbulb,
  ClipboardList,
  Clock,
  Zap,
} from 'lucide-react'
import type { ProcessDocument } from '@/types/workspace'
import { getProcessDocument } from '@/lib/api'

interface ProcessDocumentDetailDrawerProps {
  docId: string
  onClose: () => void
}

type TabId = 'overview' | 'steps' | 'roles_data' | 'intelligence' | 'evidence'

const SCENARIO_LABELS: Record<string, string> = {
  reconstruct: 'Reconstructed from existing process',
  generate: 'Generated from discovered patterns',
  tribal_capture: 'Captured tribal knowledge',
}

const STATUS_STYLES: Record<string, { bg: string; text: string }> = {
  draft: { bg: 'bg-[#F0F0F0]', text: 'text-[#666]' },
  review: { bg: 'bg-[#F0F0F0]', text: 'text-[#666]' },
  confirmed: { bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]' },
  archived: { bg: 'bg-[#F0F0F0]', text: 'text-[#999]' },
}

const AUTHORITY_LABELS: Record<string, string> = {
  approver: 'Approver',
  executor: 'Executor',
  reviewer: 'Reviewer',
  informed: 'Informed',
}

export function ProcessDocumentDetailDrawer({ docId, onClose }: ProcessDocumentDetailDrawerProps) {
  const [doc, setDoc] = useState<ProcessDocument | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<TabId>('overview')

  useEffect(() => {
    setLoading(true)
    getProcessDocument(docId)
      .then(setDoc)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [docId])

  const tabs: { id: TabId; label: string; icon: React.ReactNode }[] = [
    { id: 'overview', label: 'Overview', icon: <FileText className="w-3.5 h-3.5" /> },
    { id: 'steps', label: 'Steps', icon: <ClipboardList className="w-3.5 h-3.5" /> },
    { id: 'roles_data', label: 'Roles & Data', icon: <Users className="w-3.5 h-3.5" /> },
    { id: 'intelligence', label: 'Intelligence', icon: <Lightbulb className="w-3.5 h-3.5" /> },
    { id: 'evidence', label: 'Evidence', icon: <GitBranch className="w-3.5 h-3.5" /> },
  ]

  return (
    <>
      <div className="fixed inset-0 bg-black/20 z-40" onClick={onClose} />
      <div className="fixed right-0 top-0 h-full w-[640px] max-w-[95vw] bg-white shadow-xl z-50 flex flex-col">
        {/* Header */}
        <div className="flex items-start justify-between px-6 py-5 border-b border-[#E5E5E5]">
          <div className="flex-1 min-w-0 mr-4">
            {loading ? (
              <div className="h-5 w-48 bg-[#F0F0F0] rounded animate-pulse" />
            ) : (
              <>
                <p className="text-[15px] font-semibold text-[#333] line-clamp-2 leading-snug">
                  {doc?.title || 'Process Document'}
                </p>
                {doc && (
                  <div className="flex items-center gap-2 mt-2">
                    <span className={`px-2 py-0.5 text-[10px] font-medium rounded-md ${
                      (STATUS_STYLES[doc.status] || STATUS_STYLES.draft).bg
                    } ${(STATUS_STYLES[doc.status] || STATUS_STYLES.draft).text}`}>
                      {doc.status}
                    </span>
                    {doc.generation_scenario && (
                      <span className="px-2 py-0.5 text-[10px] font-medium text-[#666] bg-[#F0F0F0] rounded-md">
                        {SCENARIO_LABELS[doc.generation_scenario] || doc.generation_scenario}
                      </span>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
          <button onClick={onClose} className="p-1 text-[#999] hover:text-[#666] transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="border-b border-[#E5E5E5] px-6">
          <div className="flex gap-4 overflow-x-auto">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 py-2.5 text-[12px] font-medium border-b-2 transition-colors whitespace-nowrap ${
                  activeTab === tab.id
                    ? 'text-[#3FAF7A] border-[#3FAF7A]'
                    : 'text-[#999] border-transparent hover:text-[#666]'
                }`}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {loading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-20 bg-[#F4F4F4] rounded-xl animate-pulse" />
              ))}
            </div>
          ) : doc ? (
            <>
              {activeTab === 'overview' && <OverviewTab doc={doc} />}
              {activeTab === 'steps' && <StepsTab doc={doc} />}
              {activeTab === 'roles_data' && <RolesDataTab doc={doc} />}
              {activeTab === 'intelligence' && <IntelligenceTab doc={doc} />}
              {activeTab === 'evidence' && <EvidenceTab doc={doc} />}
            </>
          ) : (
            <div className="text-center py-12">
              <FileText className="w-8 h-8 text-[#CCC] mx-auto mb-2" />
              <p className="text-[13px] text-[#666]">Document not found</p>
            </div>
          )}
        </div>
      </div>
    </>
  )
}

function OverviewTab({ doc }: { doc: ProcessDocument }) {
  return (
    <div className="space-y-5">
      {doc.purpose && (
        <div>
          <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide mb-1.5">Purpose</p>
          <p className="text-[13px] text-[#333] leading-relaxed">{doc.purpose}</p>
        </div>
      )}
      {doc.trigger_event && (
        <div>
          <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide mb-1">Trigger</p>
          <p className="text-[13px] text-[#666]">{doc.trigger_event}</p>
        </div>
      )}
      {doc.frequency && (
        <div>
          <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide mb-1">Frequency</p>
          <p className="text-[13px] text-[#666]">{doc.frequency}</p>
        </div>
      )}
      <div className="grid grid-cols-3 gap-3 pt-2">
        <div className="bg-[#F4F4F4] rounded-xl p-3 text-center">
          <p className="text-[18px] font-semibold text-[#333]">{doc.steps?.length || 0}</p>
          <p className="text-[11px] text-[#999]">Steps</p>
        </div>
        <div className="bg-[#F4F4F4] rounded-xl p-3 text-center">
          <p className="text-[18px] font-semibold text-[#333]">{doc.roles?.length || 0}</p>
          <p className="text-[11px] text-[#999]">Roles</p>
        </div>
        <div className="bg-[#F4F4F4] rounded-xl p-3 text-center">
          <p className="text-[18px] font-semibold text-[#333]">{doc.data_flow?.length || 0}</p>
          <p className="text-[11px] text-[#999]">Data Flows</p>
        </div>
      </div>
      {doc.generation_duration_ms && (
        <div className="pt-2 border-t border-[#E5E5E5]">
          <p className="text-[11px] text-[#999]">
            Generated in {(doc.generation_duration_ms / 1000).toFixed(1)}s
            {doc.generation_model && ` using ${doc.generation_model}`}
          </p>
        </div>
      )}
    </div>
  )
}

function StepsTab({ doc }: { doc: ProcessDocument }) {
  return (
    <div className="space-y-3">
      {(doc.steps || []).length === 0 ? (
        <EmptyState icon={<ClipboardList className="w-6 h-6" />} message="No steps documented" />
      ) : (
        doc.steps.map((step, i) => (
          <div key={i} className="bg-[#F4F4F4] rounded-xl p-4">
            <div className="flex items-start gap-3">
              <div className="w-7 h-7 bg-white rounded-lg flex items-center justify-center border border-[#E5E5E5] flex-shrink-0">
                <span className="text-[12px] font-semibold text-[#333]">{step.step_index}</span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[13px] font-medium text-[#333]">{step.label}</p>
                {step.description && (
                  <p className="text-[12px] text-[#666] mt-0.5 leading-relaxed">{step.description}</p>
                )}
                <div className="flex flex-wrap items-center gap-2 mt-2">
                  {step.actor_persona_name && (
                    <span className="flex items-center gap-1 px-2 py-0.5 text-[10px] font-medium text-[#666] bg-white rounded-md border border-[#E5E5E5]">
                      <Users className="w-3 h-3" />
                      {step.actor_persona_name}
                    </span>
                  )}
                  {step.time_minutes != null && (
                    <span className="flex items-center gap-1 px-2 py-0.5 text-[10px] text-[#999]">
                      <Clock className="w-3 h-3" />
                      {step.time_minutes}m
                    </span>
                  )}
                  {step.vp_step_id && (
                    <span className="flex items-center gap-1 px-2 py-0.5 text-[10px] text-[#25785A] bg-[#E8F5E9] rounded-md">
                      <Zap className="w-3 h-3" />
                      VP linked
                    </span>
                  )}
                </div>
                {step.decision_points && step.decision_points.length > 0 && (
                  <div className="mt-2 pl-3 border-l-2 border-[#E5E5E5]">
                    {step.decision_points.map((dp, j) => (
                      <p key={j} className="text-[11px] text-[#666]">&bull; {dp}</p>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))
      )}
    </div>
  )
}

function RolesDataTab({ doc }: { doc: ProcessDocument }) {
  return (
    <div className="space-y-6">
      {/* Roles */}
      <div>
        <p className="text-[12px] font-semibold text-[#999] uppercase tracking-wide mb-3">Roles</p>
        {(doc.roles || []).length === 0 ? (
          <EmptyState icon={<Users className="w-5 h-5" />} message="No roles defined" />
        ) : (
          <div className="space-y-2">
            {doc.roles.map((role, i) => (
              <div key={i} className="bg-[#F4F4F4] rounded-xl p-3">
                <div className="flex items-center gap-2 mb-1">
                  <p className="text-[13px] font-medium text-[#333]">{role.persona_name}</p>
                  {role.authority_level && (
                    <span className="px-1.5 py-0.5 text-[9px] font-medium text-[#666] bg-[#E5E5E5] rounded">
                      {AUTHORITY_LABELS[role.authority_level] || role.authority_level}
                    </span>
                  )}
                </div>
                {role.responsibilities && role.responsibilities.length > 0 && (
                  <div className="space-y-0.5">
                    {role.responsibilities.map((r, j) => (
                      <p key={j} className="text-[12px] text-[#666]">&bull; {r}</p>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Data Flow */}
      <div>
        <p className="text-[12px] font-semibold text-[#999] uppercase tracking-wide mb-3">Data Flow</p>
        {(doc.data_flow || []).length === 0 ? (
          <EmptyState icon={<Database className="w-5 h-5" />} message="No data flow documented" />
        ) : (
          <div className="space-y-2">
            {doc.data_flow.map((df, i) => (
              <div key={i} className="bg-[#F4F4F4] rounded-xl p-3">
                <div className="flex items-center gap-2 mb-1">
                  <Database className="w-3.5 h-3.5 text-[#666]" />
                  <p className="text-[13px] font-medium text-[#333]">{df.data_entity_name}</p>
                  <span className="px-1.5 py-0.5 text-[9px] font-medium text-[#25785A] bg-[#E8F5E9] rounded uppercase">
                    {df.operation}
                  </span>
                </div>
                {df.description && <p className="text-[12px] text-[#666] mt-0.5">{df.description}</p>}
                {df.step_indices && df.step_indices.length > 0 && (
                  <p className="text-[10px] text-[#999] mt-1">
                    Steps: {df.step_indices.join(', ')}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function IntelligenceTab({ doc }: { doc: ProcessDocument }) {
  return (
    <div className="space-y-6">
      {/* Decision Points */}
      <div>
        <p className="text-[12px] font-semibold text-[#999] uppercase tracking-wide mb-3">Decision Points</p>
        {(doc.decision_points || []).length === 0 ? (
          <EmptyState icon={<GitBranch className="w-5 h-5" />} message="No decision points" />
        ) : (
          <div className="space-y-2">
            {doc.decision_points.map((dp, i) => (
              <div key={i} className="bg-[#F4F4F4] rounded-xl p-3">
                <p className="text-[13px] font-medium text-[#333]">{dp.label}</p>
                {dp.description && <p className="text-[12px] text-[#666] mt-0.5">{dp.description}</p>}
                {dp.criteria && dp.criteria.length > 0 && (
                  <div className="mt-1.5">
                    <p className="text-[10px] text-[#999] font-medium uppercase">Criteria</p>
                    {dp.criteria.map((c, j) => (
                      <p key={j} className="text-[11px] text-[#666]">&bull; {c}</p>
                    ))}
                  </div>
                )}
                {dp.outcomes && dp.outcomes.length > 0 && (
                  <div className="mt-1.5">
                    <p className="text-[10px] text-[#999] font-medium uppercase">Outcomes</p>
                    {dp.outcomes.map((o, j) => (
                      <p key={j} className="text-[11px] text-[#666]">&bull; {o}</p>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Exceptions */}
      <div>
        <p className="text-[12px] font-semibold text-[#999] uppercase tracking-wide mb-3">Exceptions</p>
        {(doc.exceptions || []).length === 0 ? (
          <EmptyState icon={<AlertTriangle className="w-5 h-5" />} message="No exceptions documented" />
        ) : (
          <div className="space-y-2">
            {doc.exceptions.map((ex, i) => (
              <div key={i} className="bg-[#F4F4F4] rounded-xl p-3">
                <p className="text-[13px] font-medium text-[#333]">{ex.label}</p>
                {ex.description && <p className="text-[12px] text-[#666] mt-0.5">{ex.description}</p>}
                {ex.handling_procedure && (
                  <p className="text-[12px] text-[#666] mt-1">
                    <span className="font-medium">Handling:</span> {ex.handling_procedure}
                  </p>
                )}
                {ex.escalation_path && (
                  <p className="text-[11px] text-[#999] mt-0.5">Escalate to: {ex.escalation_path}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Tribal Knowledge */}
      <div>
        <p className="text-[12px] font-semibold text-[#999] uppercase tracking-wide mb-3">Tribal Knowledge</p>
        {(doc.tribal_knowledge_callouts || []).length === 0 ? (
          <EmptyState icon={<Lightbulb className="w-5 h-5" />} message="No tribal knowledge captured" />
        ) : (
          <div className="space-y-2">
            {doc.tribal_knowledge_callouts.map((tk, i) => (
              <div key={i} className="bg-white rounded-xl p-3 border-l-3 border-[#3FAF7A]" style={{ borderLeftWidth: 3 }}>
                <p className="text-[13px] text-[#333] leading-relaxed">{tk.text}</p>
                {tk.stakeholder_name && (
                  <p className="text-[11px] text-[#25785A] font-medium mt-1.5">
                    — {tk.stakeholder_name}
                  </p>
                )}
                {tk.context && <p className="text-[11px] text-[#999] mt-0.5">{tk.context}</p>}
                {tk.importance && (
                  <span className={`inline-block mt-1 px-1.5 py-0.5 text-[9px] font-medium rounded ${
                    tk.importance === 'critical' ? 'bg-[#E8F5E9] text-[#25785A]' : 'bg-[#F0F0F0] text-[#666]'
                  }`}>
                    {tk.importance}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function EvidenceTab({ doc }: { doc: ProcessDocument }) {
  const allEvidence = doc.evidence || []
  return (
    <div className="space-y-3">
      {allEvidence.length === 0 ? (
        <EmptyState icon={<GitBranch className="w-6 h-6" />} message="No evidence references" />
      ) : (
        allEvidence.map((ev, i) => (
          <div key={i} className="bg-[#F4F4F4] rounded-xl p-3">
            {ev.excerpt && (
              <p className="text-[12px] text-[#333] leading-relaxed italic">&ldquo;{ev.excerpt}&rdquo;</p>
            )}
            <div className="flex items-center gap-2 mt-1.5">
              {ev.signal_id && (
                <span className="text-[10px] text-[#999] font-mono">
                  Signal: {ev.signal_id.slice(0, 8)}...
                </span>
              )}
              {ev.section && (
                <span className="px-1.5 py-0.5 text-[9px] text-[#666] bg-[#E5E5E5] rounded">
                  {ev.section}
                </span>
              )}
            </div>
          </div>
        ))
      )}
    </div>
  )
}

function EmptyState({ icon, message }: { icon: React.ReactNode; message: string }) {
  return (
    <div className="text-center py-6">
      <div className="text-[#CCC] mx-auto mb-1.5 flex justify-center">{icon}</div>
      <p className="text-[12px] text-[#999]">{message}</p>
    </div>
  )
}
