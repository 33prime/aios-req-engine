'use client'

import { useState, useEffect } from 'react'
import {
  Database,
  Layers,
  Settings2,
  Route,
  Sparkles,
  Clock,
  Shield,
  Lightbulb,
  AlertTriangle,
  ArrowRight,
} from 'lucide-react'
import { DrawerShell, type DrawerTab } from '@/components/ui/DrawerShell'
import { Spinner } from '@/components/ui/Spinner'
import { BRDStatusBadge } from './StatusBadge'
import { ConfirmActions } from './ConfirmActions'
import { EvidenceBlock } from './EvidenceBlock'
import { getDataEntityDetail, analyzeDataEntity } from '@/lib/api'
import { formatDate } from '@/lib/date-utils'
import type {
  DataEntityDetail,
  DataEntityEnrichment,
  DataEntityWorkflowLink,
  RevisionEntry,
} from '@/types/workspace'

type TabId = 'overview' | 'fields' | 'journey' | 'intelligence' | 'history'

interface DataEntityDetailDrawerProps {
  entityId: string
  projectId: string
  onClose: () => void
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
}

const TABS: { id: TabId; label: string; icon: typeof Database }[] = [
  { id: 'overview', label: 'Overview', icon: Layers },
  { id: 'fields', label: 'Fields', icon: Settings2 },
  { id: 'journey', label: 'Journey', icon: Route },
  { id: 'intelligence', label: 'Intelligence', icon: Sparkles },
  { id: 'history', label: 'History', icon: Clock },
]

const CATEGORY_LABELS: Record<string, string> = {
  domain: 'Domain',
  reference: 'Reference',
  transactional: 'Transactional',
  system: 'System',
}

const OPERATION_COLORS: Record<string, string> = {
  create: 'bg-[#E8F5E9] text-[#25785A]',
  read: 'bg-[#F0F0F0] text-[#666666]',
  update: 'bg-[#E8F5E9] text-brand-primary',
  delete: 'bg-[#0A1E2F] text-white',
  validate: 'bg-[#F0F0F0] text-text-placeholder',
  notify: 'bg-[#F0F0F0] text-text-placeholder',
  transfer: 'bg-[#F0F0F0] text-[#666666]',
}

export function DataEntityDetailDrawer({
  entityId,
  projectId,
  onClose,
  onConfirm,
  onNeedsReview,
}: DataEntityDetailDrawerProps) {
  const [activeTab, setActiveTab] = useState<TabId>('overview')
  const [detail, setDetail] = useState<DataEntityDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getDataEntityDetail(projectId, entityId)
      .then((data) => {
        if (!cancelled) setDetail(data)
      })
      .catch((err) => {
        console.error('Failed to load data entity detail:', err)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [projectId, entityId])

  const handleAnalyze = async () => {
    setAnalyzing(true)
    try {
      await analyzeDataEntity(projectId, entityId)
      // Reload
      const data = await getDataEntityDetail(projectId, entityId)
      setDetail(data)
    } catch (err) {
      console.error('Failed to analyze data entity:', err)
    } finally {
      setAnalyzing(false)
    }
  }

  const enrichment = detail?.enrichment_data || null

  const drawerTabs: DrawerTab[] = TABS.map((tab) => ({
    id: tab.id,
    label: tab.label,
    icon: tab.icon,
  }))

  const headerExtra = detail ? (
    <div className="flex items-center gap-2 mt-1.5">
      <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[#F0F0F0] text-[#666666]">
        {CATEGORY_LABELS[detail.entity_category] || detail.entity_category}
      </span>
      <span className="text-[10px] text-text-placeholder">
        {detail.fields?.length || 0} fields
      </span>
      {detail.enrichment_status === 'enriched' && (
        <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[#E8F5E9] text-[#25785A]">
          Enriched
        </span>
      )}
    </div>
  ) : undefined

  return (
    <DrawerShell
      onClose={onClose}
      icon={Database}
      entityLabel="Data Entity"
      title={detail?.name || 'Loading...'}
      headerExtra={headerExtra}
      tabs={drawerTabs}
      activeTab={activeTab}
      onTabChange={(id) => setActiveTab(id as TabId)}
    >
      {loading ? (
        <Spinner />
      ) : detail ? (
        <>
          {activeTab === 'overview' && (
            <OverviewTab detail={detail} onConfirm={onConfirm} onNeedsReview={onNeedsReview} />
          )}
          {activeTab === 'fields' && (
            <FieldsTab detail={detail} />
          )}
          {activeTab === 'journey' && (
            <JourneyTab workflowLinks={detail.workflow_links || []} />
          )}
          {activeTab === 'intelligence' && (
            <IntelligenceTab
              enrichment={enrichment}
              enrichmentStatus={detail.enrichment_status}
              onAnalyze={handleAnalyze}
              analyzing={analyzing}
            />
          )}
          {activeTab === 'history' && (
            <HistoryTab revisions={detail.revisions || []} />
          )}
        </>
      ) : (
        <p className="text-[13px] text-text-placeholder text-center py-8">Failed to load entity details.</p>
      )}
    </DrawerShell>
  )
}

// ============================================================================
// Overview Tab
// ============================================================================

function OverviewTab({
  detail,
  onConfirm,
  onNeedsReview,
}: {
  detail: DataEntityDetail
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
}) {
  return (
    <div className="space-y-5">
      {/* Description */}
      {detail.description && (
        <div>
          <h3 className="text-[13px] font-semibold text-text-body mb-2">Description</h3>
          <p className="text-[13px] text-[#666666] leading-relaxed">{detail.description}</p>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-surface-muted rounded-xl p-3 text-center">
          <p className="text-[18px] font-bold text-text-body">{detail.fields?.length || 0}</p>
          <p className="text-[11px] text-text-placeholder">Fields</p>
        </div>
        <div className="bg-surface-muted rounded-xl p-3 text-center">
          <p className="text-[18px] font-bold text-text-body">{detail.workflow_links?.length || 0}</p>
          <p className="text-[11px] text-text-placeholder">Workflow Links</p>
        </div>
        <div className="bg-surface-muted rounded-xl p-3 text-center">
          <p className="text-[18px] font-bold text-text-body">{detail.pii_flags?.length || 0}</p>
          <p className="text-[11px] text-text-placeholder">PII Fields</p>
        </div>
      </div>

      {/* PII Warning */}
      {detail.pii_flags && detail.pii_flags.length > 0 && (
        <div className="bg-surface-muted rounded-xl p-3 flex items-start gap-2">
          <Shield className="w-4 h-4 text-[#25785A] mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-[12px] font-medium text-text-body mb-1">PII Detected</p>
            <p className="text-[11px] text-[#666666]">
              Fields: {detail.pii_flags.join(', ')}
            </p>
          </div>
        </div>
      )}

      {/* Evidence */}
      <EvidenceBlock evidence={detail.evidence || []} />

      {/* Confirm Actions */}
      <div className="pt-3 border-t border-border">
        <ConfirmActions
          status={detail.confirmation_status}
          onConfirm={() => onConfirm('data_entity', detail.id)}
          onNeedsReview={() => onNeedsReview('data_entity', detail.id)}
        />
      </div>
    </div>
  )
}

// ============================================================================
// Fields Tab
// ============================================================================

function FieldsTab({ detail }: { detail: DataEntityDetail }) {
  const fields = detail.fields || []
  const piiSet = new Set(detail.pii_flags || [])

  if (fields.length === 0) {
    return (
      <div className="text-center py-8">
        <Settings2 className="w-6 h-6 text-text-placeholder mx-auto mb-2" />
        <p className="text-[13px] text-text-placeholder">No fields defined yet.</p>
      </div>
    )
  }

  return (
    <div className="space-y-1">
      <h3 className="text-[13px] font-semibold text-text-body mb-3">
        Fields ({fields.length})
      </h3>
      <div className="border border-border rounded-xl overflow-hidden">
        <table className="w-full text-[12px]">
          <thead>
            <tr className="bg-surface-muted">
              <th className="text-left px-3 py-2 text-text-placeholder font-medium">Name</th>
              <th className="text-left px-3 py-2 text-text-placeholder font-medium">Type</th>
              <th className="text-center px-3 py-2 text-text-placeholder font-medium">Req</th>
              <th className="text-left px-3 py-2 text-text-placeholder font-medium">Description</th>
            </tr>
          </thead>
          <tbody>
            {fields.map((f, i) => (
              <tr key={i} className="border-t border-border">
                <td className="px-3 py-2 text-text-body font-medium">
                  <span className="flex items-center gap-1.5">
                    {f.name}
                    {piiSet.has(f.name) && (
                      <Shield className="w-3 h-3 text-[#25785A]" />
                    )}
                  </span>
                </td>
                <td className="px-3 py-2 text-[#666666]">{f.type || 'text'}</td>
                <td className="px-3 py-2 text-center">
                  {f.required && <span className="text-brand-primary">*</span>}
                </td>
                <td className="px-3 py-2 text-text-placeholder truncate max-w-[150px]">{f.description || ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ============================================================================
// Journey Tab
// ============================================================================

function JourneyTab({ workflowLinks }: { workflowLinks: DataEntityWorkflowLink[] }) {
  if (workflowLinks.length === 0) {
    return (
      <div className="text-center py-8">
        <Route className="w-6 h-6 text-text-placeholder mx-auto mb-2" />
        <p className="text-[13px] text-text-placeholder">No workflow links yet.</p>
        <p className="text-[11px] text-text-placeholder mt-1">Link this entity to workflow steps to see its journey.</p>
      </div>
    )
  }

  // Group by operation type for timeline
  const operations = workflowLinks.sort((a, b) => {
    const order = ['create', 'read', 'update', 'validate', 'notify', 'transfer', 'delete']
    return order.indexOf(a.operation_type) - order.indexOf(b.operation_type)
  })

  return (
    <div className="space-y-4">
      <h3 className="text-[13px] font-semibold text-text-body">Data Journey</h3>

      {/* Timeline */}
      <div className="relative">
        <div className="absolute left-3 top-2 bottom-2 w-px bg-border" />

        <div className="space-y-3">
          {operations.map((link, i) => {
            const colorClass = OPERATION_COLORS[link.operation_type] || OPERATION_COLORS.read
            return (
              <div key={link.id || i} className="flex gap-3 relative">
                {/* Operation badge */}
                <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 z-10 ${colorClass}`}>
                  <span className="text-[8px] font-bold uppercase">{link.operation_type.charAt(0)}</span>
                </div>

                {/* Content */}
                <div className="flex-1 bg-white rounded-xl border border-border p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded ${colorClass}`}>
                      {link.operation_type}
                    </span>
                    <ArrowRight className="w-3 h-3 text-text-placeholder" />
                    <span className="text-[12px] font-medium text-text-body">
                      {link.vp_step_label || 'Workflow Step'}
                    </span>
                  </div>
                  {link.description && (
                    <p className="text-[11px] text-[#666666]">{link.description}</p>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// Intelligence Tab
// ============================================================================

function IntelligenceTab({
  enrichment,
  enrichmentStatus,
  onAnalyze,
  analyzing,
}: {
  enrichment: DataEntityEnrichment | null
  enrichmentStatus?: string | null
  onAnalyze: () => void
  analyzing: boolean
}) {
  if (!enrichment || enrichmentStatus !== 'enriched') {
    return (
      <div className="text-center py-8">
        <Sparkles className="w-6 h-6 text-text-placeholder mx-auto mb-2" />
        <p className="text-[13px] text-text-placeholder mb-3">
          {enrichmentStatus === 'failed'
            ? 'Analysis failed. Try again.'
            : 'Run AI analysis to get intelligence on this entity.'}
        </p>
        <button
          onClick={onAnalyze}
          disabled={analyzing}
          className="inline-flex items-center gap-1.5 px-4 py-2 text-[12px] font-medium text-white bg-brand-primary rounded-xl hover:bg-[#25785A] transition-colors disabled:opacity-50"
        >
          <Sparkles className={`w-3.5 h-3.5 ${analyzing ? 'animate-spin' : ''}`} />
          {analyzing ? 'Analyzing...' : 'Run Analysis'}
        </button>
      </div>
    )
  }

  const SENSITIVITY_CONFIG: Record<string, { bg: string; text: string }> = {
    critical: { bg: 'bg-[#0A1E2F]', text: 'text-white' },
    high: { bg: 'bg-[#25785A]', text: 'text-white' },
    medium: { bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]' },
    low: { bg: 'bg-[#F0F0F0]', text: 'text-[#666666]' },
  }

  const sensCfg = SENSITIVITY_CONFIG[enrichment.sensitivity_level || 'low'] || SENSITIVITY_CONFIG.low

  return (
    <div className="space-y-5">
      {/* Re-analyze button */}
      <div className="flex justify-end">
        <button
          onClick={onAnalyze}
          disabled={analyzing}
          className="inline-flex items-center gap-1 text-[11px] text-text-placeholder hover:text-brand-primary transition-colors disabled:opacity-50"
        >
          <Sparkles className={`w-3 h-3 ${analyzing ? 'animate-spin' : ''}`} />
          {analyzing ? 'Analyzing...' : 'Re-analyze'}
        </button>
      </div>

      {/* Sensitivity */}
      <div className="flex items-center gap-2">
        <span className="text-[12px] text-text-placeholder">Sensitivity:</span>
        <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${sensCfg.bg} ${sensCfg.text}`}>
          {(enrichment.sensitivity_level || 'low').charAt(0).toUpperCase() + (enrichment.sensitivity_level || 'low').slice(1)}
        </span>
      </div>

      {/* PII Fields */}
      {enrichment.pii_fields && enrichment.pii_fields.length > 0 && (
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <Shield className="w-3.5 h-3.5 text-[#25785A]" />
            <h4 className="text-[12px] font-medium text-text-body">PII Fields</h4>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {enrichment.pii_fields.map((field, i) => (
              <span key={i} className="px-2 py-0.5 text-[11px] bg-[#E8F5E9] text-[#25785A] rounded-full">
                {field}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* AI Opportunities */}
      {enrichment.ai_opportunities && enrichment.ai_opportunities.length > 0 && (
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <Lightbulb className="w-3.5 h-3.5 text-brand-primary" />
            <h4 className="text-[12px] font-medium text-text-body">AI Opportunities</h4>
          </div>
          <ul className="space-y-2">
            {enrichment.ai_opportunities.map((opp, i) => (
              <li key={i} className="flex items-start gap-2 text-[12px] text-[#666666] bg-surface-muted rounded-lg px-3 py-2">
                <Sparkles className="w-3 h-3 text-brand-primary mt-0.5 flex-shrink-0" />
                {opp}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* System Design Notes */}
      {enrichment.system_design_notes && (
        <div>
          <h4 className="text-[12px] font-medium text-text-body mb-1">System Design Notes</h4>
          <p className="text-[12px] text-[#666666] bg-surface-muted rounded-lg px-3 py-2">
            {enrichment.system_design_notes}
          </p>
        </div>
      )}

      {/* Relationship Suggestions */}
      {enrichment.relationship_suggestions && enrichment.relationship_suggestions.length > 0 && (
        <div>
          <h4 className="text-[12px] font-medium text-text-body mb-2">Relationship Suggestions</h4>
          <div className="space-y-2">
            {enrichment.relationship_suggestions.map((rel, i) => (
              <div key={i} className="bg-surface-muted rounded-lg px-3 py-2">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[11px] font-medium text-text-body">{rel.target_entity}</span>
                  <span className="text-[10px] text-text-placeholder bg-[#F0F0F0] px-1.5 py-0.5 rounded">
                    {rel.relationship_type}
                  </span>
                </div>
                <p className="text-[11px] text-[#666666]">{rel.rationale}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Validation Suggestions */}
      {enrichment.validation_suggestions && enrichment.validation_suggestions.length > 0 && (
        <div>
          <h4 className="text-[12px] font-medium text-text-body mb-2">Validation Rules</h4>
          <ul className="space-y-1">
            {enrichment.validation_suggestions.map((rule, i) => (
              <li key={i} className="flex items-start gap-2 text-[12px] text-[#666666]">
                <span className="text-brand-primary mt-0.5">*</span>
                {rule}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// History Tab
// ============================================================================

function HistoryTab({ revisions }: { revisions: RevisionEntry[] }) {
  if (revisions.length === 0) {
    return (
      <div className="text-center py-8">
        <Clock className="w-6 h-6 text-text-placeholder mx-auto mb-2" />
        <p className="text-[13px] text-text-placeholder">No revision history yet.</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <h3 className="text-[13px] font-semibold text-text-body">Revision History</h3>
      <div className="relative">
        <div className="absolute left-3 top-2 bottom-2 w-px bg-border" />
        <div className="space-y-3">
          {revisions.map((rev, i) => (
            <div key={i} className="flex gap-3 relative">
              <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 z-10 ${
                i === 0 ? 'bg-brand-primary' : 'bg-border'
              }`}>
                <span className={`text-[9px] font-bold ${i === 0 ? 'text-white' : 'text-text-placeholder'}`}>
                  {rev.revision_number}
                </span>
              </div>
              <div className="flex-1 bg-white rounded-xl border border-border p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[11px] font-medium text-text-body">
                    Revision {rev.revision_number}
                  </span>
                  <span className="text-[10px] text-text-placeholder">
                    {formatDate(rev.created_at)}
                  </span>
                </div>
                <p className="text-[12px] text-[#666666]">{rev.diff_summary}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
