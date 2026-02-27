'use client'

import { useState, useEffect, useMemo, useCallback } from 'react'
import {
  AlertTriangle,
  Target,
  BarChart3,
  FileText,
  Users,
  Puzzle,
  ChevronDown,
  ChevronRight,
  Workflow,
  FileSearch,
  Info,
  DollarSign,
  Pencil,
  Clock,
  Compass,
  TrendingUp,
  TrendingDown,
  Minus,
} from 'lucide-react'
import { DrawerShell, type DrawerTab } from '@/components/ui/DrawerShell'
import { EmptyState } from '@/components/ui/EmptyState'
import { Spinner } from '@/components/ui/Spinner'
import { ConnectionGroup } from '@/components/ui/ConnectionGroup'
import { formatRelativeTime, formatRevisionAuthor, REVISION_TYPE_COLORS } from '@/lib/date-utils'
import { BRDStatusBadge } from './StatusBadge'
import { ConfirmActions } from './ConfirmActions'
import { EvidenceBlock } from './EvidenceBlock'
import { WhoHasTheData } from './WhoHasTheData'
import { FinancialImpactCard } from './FinancialImpactCard'
import { FieldEditor } from './FieldEditor'
import { LinkedPillGroup } from './FeatureDrawer'
import { getBRDDriverDetail, updateDriverFinancials, updateBusinessDriver, getDriverHorizons } from '@/lib/api'
import { getTopicsForDriverType, inferTopicsFromText } from '@/lib/topic-role-map'
import type {
  BusinessDriver,
  BusinessDriverDetail,
  RevisionEntry,
  AssociatedPersona,
  VisionAlignment,
  StakeholderBRDSummary,
  LinkedEntityPill,
} from '@/types/workspace'

type DriverType = 'pain' | 'goal' | 'kpi'
type TabId = 'overview' | 'history' | 'horizons'

interface BusinessDriverDetailDrawerProps {
  driverId: string
  driverType: DriverType
  projectId: string
  initialData: BusinessDriver
  stakeholders?: StakeholderBRDSummary[]
  onClose: () => void
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
}

const TYPE_CONFIG: Record<DriverType, { icon: typeof AlertTriangle; color: string; label: string }> = {
  pain: { icon: AlertTriangle, color: 'text-red-400', label: 'Pain Point' },
  goal: { icon: Target, color: '#3FAF7A', label: 'Business Goal' },
  kpi: { icon: BarChart3, color: 'text-gray-500', label: 'Success Metric' },
}

export function BusinessDriverDetailDrawer({
  driverId,
  driverType,
  projectId,
  initialData,
  stakeholders = [],
  onClose,
  onConfirm,
  onNeedsReview,
}: BusinessDriverDetailDrawerProps) {
  const [activeTab, setActiveTab] = useState<TabId>('overview')
  const [detail, setDetail] = useState<BusinessDriverDetail | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchDetail = useCallback(() => {
    setLoading(true)
    getBRDDriverDetail(projectId, driverId)
      .then((data) => setDetail(data))
      .catch((err) => console.error('Failed to load driver detail:', err))
      .finally(() => setLoading(false))
  }, [projectId, driverId])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getBRDDriverDetail(projectId, driverId)
      .then((data) => { if (!cancelled) setDetail(data) })
      .catch((err) => console.error('Failed to load driver detail:', err))
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [projectId, driverId])

  const config = TYPE_CONFIG[driverType]
  const Icon = config.icon

  const tabs: DrawerTab[] = useMemo(() => [
    { id: 'overview', label: 'Overview', icon: FileText },
    { id: 'history', label: 'History', icon: Clock },
    { id: 'horizons', label: 'Horizons', icon: Compass },
  ], [])

  const displayTitle = initialData.title || initialData.description

  return (
    <DrawerShell
      onClose={onClose}
      icon={Icon}
      entityLabel={config.label}
      title={displayTitle}
      headerRight={<BRDStatusBadge status={initialData.confirmation_status} />}
      headerActions={
        <ConfirmActions
          status={initialData.confirmation_status}
          onConfirm={() => onConfirm('business_driver', driverId)}
          onNeedsReview={() => onNeedsReview('business_driver', driverId)}
          size="md"
        />
      }
      tabs={tabs}
      activeTab={activeTab}
      onTabChange={(id) => setActiveTab(id as TabId)}
    >
      {activeTab === 'overview' && (
        <OverviewTab
          driverType={driverType}
          projectId={projectId}
          driverId={driverId}
          initialData={initialData}
          detail={detail}
          loading={loading}
          onDetailUpdate={setDetail}
          onRefresh={fetchDetail}
        />
      )}
      {activeTab === 'history' && (
        <HistoryTab
          revisions={detail?.revisions || []}
          loading={loading}
        />
      )}
      {activeTab === 'horizons' && (
        <HorizonsTab
          projectId={projectId}
          driverId={driverId}
        />
      )}
    </DrawerShell>
  )
}

// ============================================================================
// Overview Tab (editable fields + narrative + relevance + connections + evidence)
// ============================================================================

function OverviewTab({
  driverType,
  projectId,
  driverId,
  initialData,
  detail,
  loading,
  onDetailUpdate,
  onRefresh,
}: {
  driverType: DriverType
  projectId: string
  driverId: string
  initialData: BusinessDriver
  detail: BusinessDriverDetail | null
  loading: boolean
  onDetailUpdate: (d: BusinessDriverDetail) => void
  onRefresh: () => void
}) {
  const d = detail || initialData
  const [editingFinancial, setEditingFinancial] = useState(false)
  const [savingFinancial, setSavingFinancial] = useState(false)
  const [evidenceExpanded, setEvidenceExpanded] = useState(false)

  const narrative = useMemo(() => buildNarrative(driverType, d), [driverType, d])
  const score = d.relatability_score ?? 0
  const va = d.vision_alignment

  const missingData = useMemo(() => {
    const items: string[] = []
    if (!d.linked_persona_count && !(detail?.associated_personas?.length))
      items.push('Not linked to any persona')
    if (!d.linked_workflow_count)
      items.push('Not linked to any workflow')
    if (!d.linked_feature_count && !(detail?.associated_features?.length))
      items.push('Not linked to any feature')
    if (driverType === 'kpi') {
      if (!d.baseline_value) items.push('Missing baseline value')
      if (!d.target_value) items.push('Missing target value')
      if (!d.measurement_method) items.push('Missing measurement method')
    }
    if (driverType === 'pain' && !d.severity) items.push('Missing severity assessment')
    if (driverType === 'goal' && !d.success_criteria) items.push('Missing success criteria')
    return items
  }, [d, detail, driverType])

  // Build LinkedEntityPills from detail associations
  const linkedPersonaPills: LinkedEntityPill[] = useMemo(() => {
    if (!detail?.associated_personas?.length) return []
    return detail.associated_personas.map((p) => ({
      id: p.id,
      entity_type: 'persona',
      name: p.name,
      subtitle: p.role || null,
      dependency_type: 'associated',
      strength: 0,
    }))
  }, [detail])

  const linkedFeaturePills: LinkedEntityPill[] = useMemo(() => {
    if (!detail?.associated_features?.length) return []
    return detail.associated_features.map((f) => ({
      id: f.id,
      entity_type: 'feature',
      name: f.name,
      subtitle: f.category || null,
      dependency_type: 'associated',
      strength: 0,
    }))
  }, [detail])

  const handleFieldSave = async (fieldName: string, value: string) => {
    try {
      await updateBusinessDriver(projectId, driverId, { [fieldName]: value })
      onRefresh()
    } catch (err) {
      console.error(`Failed to save ${fieldName}:`, err)
    }
  }

  const evidence = detail?.evidence || initialData.evidence || []

  return (
    <div className="space-y-6">
      {/* Editable Title */}
      <FieldEditor
        fieldName="title"
        fieldLabel="Title"
        currentValue={d.title}
        driverId={driverId}
        projectId={projectId}
        onSave={(v) => handleFieldSave('title', v)}
      />

      {/* Editable Description */}
      <FieldEditor
        fieldName="description"
        fieldLabel="Description"
        currentValue={d.description}
        driverId={driverId}
        projectId={projectId}
        onSave={(v) => handleFieldSave('description', v)}
        multiline
      />

      {/* AI Narrative */}
      {narrative && (
        <div className="bg-[#F4F4F4] border border-border rounded-xl px-4 py-3">
          <p className="text-[11px] font-medium text-text-placeholder uppercase tracking-wide mb-1">AI Narrative</p>
          <p className="text-[13px] text-text-body leading-relaxed">{narrative}</p>
        </div>
      )}

      {/* Relatability Score + Vision Alignment */}
      <div className="flex items-center gap-4">
        <div className="flex-1">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-medium text-text-placeholder uppercase tracking-wide">
              Relevance Score
            </span>
            <span className="text-[12px] font-semibold text-text-body">{score.toFixed(1)}</span>
          </div>
          <div className="h-2 bg-[#F0F0F0] rounded-full overflow-hidden">
            <div
              className="h-full bg-brand-primary rounded-full transition-all duration-500"
              style={{ width: `${Math.min((score / 30) * 100, 100)}%` }}
            />
          </div>
        </div>
        {va && <VisionAlignmentBadge alignment={va} />}
      </div>

      {/* Financial Impact Overview (KPI only) */}
      {driverType === 'kpi' && (
        <FinancialOverview
          d={d}
          editing={editingFinancial}
          saving={savingFinancial}
          onEdit={() => setEditingFinancial(true)}
          onCancel={() => setEditingFinancial(false)}
          onSave={async (values) => {
            setSavingFinancial(true)
            try {
              await updateDriverFinancials(projectId, driverId, values)
              onRefresh()
              setEditingFinancial(false)
            } catch (err) {
              console.error('Failed to save financial impact:', err)
            } finally {
              setSavingFinancial(false)
            }
          }}
        />
      )}

      {/* Type-specific editable fields */}
      <div>
        <h4 className="text-[11px] font-medium text-text-placeholder uppercase tracking-wide mb-3">
          {driverType === 'pain' ? 'Pain Details' : driverType === 'goal' ? 'Goal Details' : 'Metric Details'}
        </h4>

        <div className="space-y-4">
          {driverType === 'pain' && (
            <>
              <FieldEditor fieldName="severity" fieldLabel="Severity" currentValue={d.severity} driverId={driverId} projectId={projectId} onSave={(v) => handleFieldSave('severity', v)} />
              <FieldEditor fieldName="business_impact" fieldLabel="Business Impact" currentValue={d.business_impact} driverId={driverId} projectId={projectId} onSave={(v) => handleFieldSave('business_impact', v)} multiline />
              <FieldEditor fieldName="affected_users" fieldLabel="Affected Users" currentValue={d.affected_users} driverId={driverId} projectId={projectId} onSave={(v) => handleFieldSave('affected_users', v)} />
              <FieldEditor fieldName="current_workaround" fieldLabel="Current Workaround" currentValue={d.current_workaround} driverId={driverId} projectId={projectId} onSave={(v) => handleFieldSave('current_workaround', v)} multiline />
              <FieldEditor fieldName="frequency" fieldLabel="Frequency" currentValue={d.frequency} driverId={driverId} projectId={projectId} onSave={(v) => handleFieldSave('frequency', v)} />
            </>
          )}

          {driverType === 'goal' && (
            <>
              <FieldEditor fieldName="success_criteria" fieldLabel="Success Criteria" currentValue={d.success_criteria} driverId={driverId} projectId={projectId} onSave={(v) => handleFieldSave('success_criteria', v)} multiline />
              <FieldEditor fieldName="owner" fieldLabel="Owner" currentValue={d.owner} driverId={driverId} projectId={projectId} onSave={(v) => handleFieldSave('owner', v)} />
              <FieldEditor fieldName="goal_timeframe" fieldLabel="Timeframe" currentValue={d.goal_timeframe} driverId={driverId} projectId={projectId} onSave={(v) => handleFieldSave('goal_timeframe', v)} />
              <FieldEditor fieldName="dependencies" fieldLabel="Dependencies" currentValue={d.dependencies} driverId={driverId} projectId={projectId} onSave={(v) => handleFieldSave('dependencies', v)} multiline />
            </>
          )}

          {driverType === 'kpi' && (
            <>
              <FieldEditor fieldName="baseline_value" fieldLabel="Baseline" currentValue={d.baseline_value} driverId={driverId} projectId={projectId} onSave={(v) => handleFieldSave('baseline_value', v)} />
              <FieldEditor fieldName="target_value" fieldLabel="Target" currentValue={d.target_value} driverId={driverId} projectId={projectId} onSave={(v) => handleFieldSave('target_value', v)} />
              <FieldEditor fieldName="measurement_method" fieldLabel="Measurement Method" currentValue={d.measurement_method} driverId={driverId} projectId={projectId} onSave={(v) => handleFieldSave('measurement_method', v)} />
              <FieldEditor fieldName="tracking_frequency" fieldLabel="Tracking Frequency" currentValue={d.tracking_frequency} driverId={driverId} projectId={projectId} onSave={(v) => handleFieldSave('tracking_frequency', v)} />
              <FieldEditor fieldName="data_source" fieldLabel="Data Source" currentValue={d.data_source} driverId={driverId} projectId={projectId} onSave={(v) => handleFieldSave('data_source', v)} />
              <FieldEditor fieldName="responsible_team" fieldLabel="Responsible Team" currentValue={d.responsible_team} driverId={driverId} projectId={projectId} onSave={(v) => handleFieldSave('responsible_team', v)} />
            </>
          )}
        </div>
      </div>

      {/* Missing Data Callouts */}
      {missingData.length > 0 && (
        <div className="space-y-1.5">
          <h4 className="text-[11px] font-medium text-text-placeholder uppercase tracking-wide">Missing Data</h4>
          {missingData.map((msg, i) => (
            <div
              key={i}
              className="flex items-start gap-2 text-[12px] text-[#666666] bg-[#F4F4F4] border border-border rounded-lg px-3 py-2"
            >
              <Info className="w-3.5 h-3.5 mt-0.5 flex-shrink-0 text-text-placeholder" />
              {msg}
            </div>
          ))}
        </div>
      )}

      {/* Linked Entities (from connections, merged into overview) */}
      {loading && !detail ? (
        <Spinner size="sm" label="Loading connections..." />
      ) : (
        <>
          {linkedPersonaPills.length > 0 && (
            <LinkedPillGroup
              icon={Users}
              title="Linked Personas"
              pills={linkedPersonaPills}
              emptyText=""
            />
          )}
          {linkedFeaturePills.length > 0 && (
            <LinkedPillGroup
              icon={Puzzle}
              title="Linked Features"
              pills={linkedFeaturePills}
              emptyText=""
            />
          )}
        </>
      )}

      {/* Evidence strip (collapsed, from provenance) */}
      {evidence.length > 0 && (
        <div>
          <button
            onClick={() => setEvidenceExpanded(!evidenceExpanded)}
            className="flex items-center gap-1.5 text-[11px] font-medium text-text-placeholder hover:text-[#666666] transition-colors"
          >
            {evidenceExpanded ? (
              <ChevronDown className="w-3 h-3" />
            ) : (
              <ChevronRight className="w-3 h-3" />
            )}
            Evidence ({evidence.length} source{evidence.length !== 1 ? 's' : ''})
          </button>
          {evidenceExpanded && (
            <div className="mt-2">
              <EvidenceBlock evidence={evidence} maxItems={5} />
            </div>
          )}
        </div>
      )}

      {loading && !detail && (
        <Spinner size="sm" label="Loading details..." />
      )}
    </div>
  )
}

// ============================================================================
// Financial Overview (inline at top of KPI Overview tab)
// ============================================================================

const IMPACT_TYPES = [
  { id: 'cost_reduction', label: 'Cost Reduction' },
  { id: 'revenue_increase', label: 'Revenue Increase' },
  { id: 'revenue_new', label: 'New Revenue' },
  { id: 'risk_avoidance', label: 'Risk Avoidance' },
  { id: 'productivity_gain', label: 'Productivity Gain' },
] as const

const TIMEFRAMES = [
  { id: 'annual', label: 'Annual' },
  { id: 'monthly', label: 'Monthly' },
  { id: 'quarterly', label: 'Quarterly' },
  { id: 'one_time', label: 'One-time' },
] as const

function FinancialOverview({
  d,
  editing,
  saving,
  onEdit,
  onCancel,
  onSave,
}: {
  d: BusinessDriver | BusinessDriverDetail
  editing: boolean
  saving: boolean
  onEdit: () => void
  onCancel: () => void
  onSave: (values: {
    monetary_type?: string | null
    monetary_value_low?: number | null
    monetary_value_high?: number | null
    monetary_timeframe?: string | null
    monetary_confidence?: number | null
    monetary_source?: string | null
  }) => void
}) {
  const hasValues = d.monetary_value_low || d.monetary_value_high
  const [type, setType] = useState(d.monetary_type || '')
  const [low, setLow] = useState(d.monetary_value_low?.toString() || '')
  const [high, setHigh] = useState(d.monetary_value_high?.toString() || '')
  const [timeframe, setTimeframe] = useState(d.monetary_timeframe || 'annual')
  const [confidence, setConfidence] = useState(d.monetary_confidence != null ? Math.round(d.monetary_confidence * 100) : 50)
  const [source, setSource] = useState(d.monetary_source || '')

  if (!editing && !hasValues) {
    return (
      <button
        onClick={onEdit}
        className="flex items-center gap-2 w-full px-3 py-2.5 text-[12px] font-medium text-[#25785A] bg-white border border-brand-primary border-dashed rounded-lg hover:bg-[#E8F5E9] transition-colors"
      >
        <DollarSign className="w-3.5 h-3.5" />
        Add Financial Impact
      </button>
    )
  }

  if (!editing) {
    return (
      <div className="space-y-2">
        <FinancialImpactCard
          monetaryValueLow={d.monetary_value_low}
          monetaryValueHigh={d.monetary_value_high}
          monetaryType={d.monetary_type}
          monetaryTimeframe={d.monetary_timeframe}
          monetaryConfidence={d.monetary_confidence}
          monetarySource={d.monetary_source}
        />
        <button
          onClick={onEdit}
          className="flex items-center gap-1.5 text-[12px] font-medium text-[#666666] hover:text-[#25785A] transition-colors"
        >
          <Pencil className="w-3 h-3" />
          Edit estimate
        </button>
      </div>
    )
  }

  return (
    <div className="border border-border rounded-xl overflow-hidden bg-white">
      <div className="px-4 py-3 bg-[#F4F4F4] border-b border-border">
        <div className="flex items-center gap-2">
          <DollarSign className="w-4 h-4 text-brand-primary" />
          <span className="text-[13px] font-semibold text-text-body">Financial Impact</span>
        </div>
      </div>
      <div className="p-4 space-y-3">
        <div>
          <span className="text-[11px] font-medium text-text-placeholder uppercase tracking-wide block mb-1.5">Type</span>
          <div className="flex flex-wrap gap-1.5">
            {IMPACT_TYPES.map((t) => (
              <button
                key={t.id}
                onClick={() => setType(t.id)}
                className={`px-2.5 py-1 text-[11px] font-medium rounded-lg transition-colors ${
                  type === t.id
                    ? 'bg-brand-primary text-white'
                    : 'bg-white border border-border text-[#666666] hover:border-brand-primary'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>
        <div>
          <span className="text-[11px] font-medium text-text-placeholder uppercase tracking-wide block mb-1.5">Value Range</span>
          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[12px] text-text-placeholder">$</span>
              <input type="text" value={low} onChange={(e) => setLow(e.target.value)} placeholder="Low" className="w-full pl-6 pr-3 py-1.5 text-[12px] border border-border rounded-lg bg-white text-text-body placeholder:text-text-placeholder focus:outline-none focus:border-brand-primary" />
            </div>
            <span className="text-[12px] text-text-placeholder">—</span>
            <div className="relative flex-1">
              <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[12px] text-text-placeholder">$</span>
              <input type="text" value={high} onChange={(e) => setHigh(e.target.value)} placeholder="High" className="w-full pl-6 pr-3 py-1.5 text-[12px] border border-border rounded-lg bg-white text-text-body placeholder:text-text-placeholder focus:outline-none focus:border-brand-primary" />
            </div>
          </div>
        </div>
        <div>
          <span className="text-[11px] font-medium text-text-placeholder uppercase tracking-wide block mb-1.5">Timeframe</span>
          <div className="flex gap-1">
            {TIMEFRAMES.map((tf) => (
              <button
                key={tf.id}
                onClick={() => setTimeframe(tf.id)}
                className={`flex-1 px-2 py-1.5 text-[11px] font-medium rounded-lg transition-colors ${
                  timeframe === tf.id
                    ? 'bg-brand-primary text-white'
                    : 'bg-white border border-border text-[#666666] hover:border-brand-primary'
                }`}
              >
                {tf.label}
              </button>
            ))}
          </div>
        </div>
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-[11px] font-medium text-text-placeholder uppercase tracking-wide">Confidence</span>
            <span className="text-[12px] font-semibold text-text-body">{confidence}%</span>
          </div>
          <input type="range" min={0} max={100} value={confidence} onChange={(e) => setConfidence(parseInt(e.target.value))} className="w-full h-1.5 bg-border rounded-full appearance-none cursor-pointer accent-brand-primary" />
        </div>
        <div>
          <span className="text-[11px] font-medium text-text-placeholder uppercase tracking-wide block mb-1.5">Source (optional)</span>
          <input type="text" value={source} onChange={(e) => setSource(e.target.value)} placeholder="e.g. CFO estimate, industry benchmark..." className="w-full px-3 py-1.5 text-[12px] border border-border rounded-lg bg-white text-text-body placeholder:text-text-placeholder focus:outline-none focus:border-brand-primary" />
        </div>
        <div className="flex items-center justify-end gap-2 pt-1">
          <button onClick={onCancel} className="px-3 py-1.5 text-[12px] font-medium text-[#666666] hover:text-text-body rounded-lg hover:bg-[#F0F0F0] transition-colors">Cancel</button>
          <button
            onClick={() => onSave({
              monetary_type: type || null,
              monetary_value_low: parseFloat(low.replace(/[^0-9.]/g, '')) || null,
              monetary_value_high: parseFloat(high.replace(/[^0-9.]/g, '')) || null,
              monetary_timeframe: timeframe || null,
              monetary_confidence: confidence / 100,
              monetary_source: source || null,
            })}
            disabled={saving}
            className="px-4 py-1.5 text-[12px] font-medium rounded-lg bg-brand-primary text-white hover:bg-[#25785A] transition-colors disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  )
}

function buildNarrative(driverType: DriverType, d: BusinessDriver | BusinessDriverDetail): string | null {
  const parts: string[] = []

  if (driverType === 'pain') {
    parts.push(`This pain point`)
    if ('associated_personas' in d && (d as BusinessDriverDetail).associated_personas?.length) {
      parts.push(`affects ${(d as BusinessDriverDetail).associated_personas.map((p: AssociatedPersona) => p.name).join(', ')}`)
    } else if ('associated_persona_names' in d && (d as BusinessDriver).associated_persona_names?.length) {
      parts.push(`affects ${(d as BusinessDriver).associated_persona_names!.join(', ')}`)
    }
    if (d.severity) parts.push(`with ${d.severity.toLowerCase()} severity`)
    if (d.business_impact) parts.push(`— ${d.business_impact}`)
    if (d.current_workaround) parts.push(`Current workaround: ${d.current_workaround}`)
  } else if (driverType === 'goal') {
    parts.push(`This business goal`)
    if (d.owner) parts.push(`is owned by ${d.owner}`)
    if (d.goal_timeframe) parts.push(`with a target timeframe of ${d.goal_timeframe}`)
    if (d.success_criteria) parts.push(`Success criteria: ${d.success_criteria}`)
  } else {
    parts.push(`This KPI`)
    if (d.baseline_value && d.target_value) {
      parts.push(`tracks from ${d.baseline_value} to ${d.target_value}`)
    } else if (d.target_value) {
      parts.push(`targets ${d.target_value}`)
    }
    if (d.measurement_method) parts.push(`measured via ${d.measurement_method}`)
    if (d.tracking_frequency) parts.push(`tracked ${d.tracking_frequency}`)
    if (d.responsible_team) parts.push(`by ${d.responsible_team}`)
    if (d.monetary_value_low || d.monetary_value_high) {
      const low = d.monetary_value_low ?? 0
      const high = d.monetary_value_high ?? low
      const fmt = (v: number) => v >= 1_000_000 ? `$${(v / 1_000_000).toFixed(1)}M` : v >= 1_000 ? `$${Math.round(v / 1_000)}K` : `$${v}`
      const range = low > 0 && high > 0 && low !== high ? `${fmt(low)}-${fmt(high)}` : fmt(high || low)
      parts.push(`with an estimated impact of ${range}/year`)
    }
  }

  if (parts.length <= 1) return null

  const linked = d.linked_feature_count ?? 0
  if (linked > 0) {
    parts.push(`It is addressed by ${linked} feature${linked > 1 ? 's' : ''}.`)
  }

  return parts.join(' ').replace(/\s+/g, ' ').trim() + '.'
}

function VisionAlignmentBadge({ alignment }: { alignment: VisionAlignment }) {
  const config: Record<string, { bg: string; text: string; label: string }> = {
    high: { bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]', label: 'High alignment' },
    medium: { bg: 'bg-[#F0F0F0]', text: 'text-[#666666]', label: 'Medium alignment' },
    low: { bg: 'bg-[#F0F0F0]', text: 'text-text-placeholder', label: 'Low alignment' },
    unrelated: { bg: 'bg-[#F0F0F0]', text: 'text-text-placeholder', label: 'Unrelated' },
  }
  const c = config[alignment] || config.low
  return (
    <div className="flex-shrink-0 text-center">
      <span className="text-[10px] font-medium text-text-placeholder uppercase tracking-wide block mb-1">Vision</span>
      <span className={`inline-flex px-2.5 py-1 text-[11px] font-medium rounded-full ${c.bg} ${c.text}`}>
        {c.label}
      </span>
    </div>
  )
}

// ============================================================================
// Horizons Tab
// ============================================================================

interface HorizonOutcome {
  id: string
  title: string
  threshold?: string | null
  current_value?: string | null
  progress: number
  trend?: string | null
  horizon_title: string
}

interface HorizonGroup {
  horizon_number: number
  outcomes: HorizonOutcome[]
}

const HORIZON_COLORS: Record<number, string> = {
  1: 'bg-[#E8F5E9] text-[#25785A]',
  2: 'bg-[#E8EDF2] text-[#0A1E2F]',
  3: 'bg-[#F0F0F0] text-[#666666]',
}

const TrendIcon = ({ trend }: { trend?: string | null }) => {
  if (trend === 'up') return <TrendingUp className="w-3 h-3 text-[#25785A]" />
  if (trend === 'down') return <TrendingDown className="w-3 h-3 text-red-400" />
  return <Minus className="w-3 h-3 text-text-placeholder" />
}

function HorizonsTab({
  projectId,
  driverId,
}: {
  projectId: string
  driverId: string
}) {
  const [data, setData] = useState<HorizonGroup[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getDriverHorizons(projectId, driverId)
      .then((resp) => { if (!cancelled) setData(resp.horizons || []) })
      .catch((err) => console.error('Failed to load horizons:', err))
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [projectId, driverId])

  if (loading) {
    return <Spinner size="sm" label="Loading horizons..." />
  }

  if (data.length === 0) {
    return (
      <EmptyState
        icon={<Compass className="w-8 h-8 text-border" />}
        title="No horizon outcomes linked yet"
        description="Horizon outcomes will appear here once they are linked to this driver."
      />
    )
  }

  return (
    <div className="space-y-6">
      {data.map((group) => (
        <div key={group.horizon_number}>
          <div className="flex items-center gap-2 mb-3">
            <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${HORIZON_COLORS[group.horizon_number] || HORIZON_COLORS[3]}`}>
              H{group.horizon_number}
            </span>
            {group.outcomes[0]?.horizon_title && (
              <span className="text-[12px] text-[#666666] font-medium">{group.outcomes[0].horizon_title}</span>
            )}
          </div>
          <div className="space-y-2">
            {group.outcomes.map((o) => (
              <div key={o.id} className="bg-[#F4F4F4] border border-border rounded-lg px-3 py-2.5">
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="text-[13px] text-text-body font-medium flex-1 min-w-0 truncate">
                    {o.title}
                  </span>
                  <TrendIcon trend={o.trend} />
                </div>
                {/* Progress bar */}
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-2 bg-[#E8E8E8] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-brand-primary rounded-full transition-all duration-500"
                      style={{ width: `${Math.min(Math.max(o.progress * 100, 0), 100)}%` }}
                    />
                  </div>
                  <span className="text-[11px] font-semibold text-text-body w-10 text-right">
                    {Math.round(o.progress * 100)}%
                  </span>
                </div>
                {(o.current_value || o.threshold) && (
                  <div className="flex items-center gap-3 mt-1.5 text-[11px] text-text-placeholder">
                    {o.current_value && <span>Current: {o.current_value}</span>}
                    {o.threshold && <span>Target: {o.threshold}</span>}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

// ============================================================================
// History Tab
// ============================================================================

function HistoryTab({
  revisions,
  loading,
}: {
  revisions: RevisionEntry[]
  loading: boolean
}) {
  if (loading && revisions.length === 0) {
    return <Spinner size="sm" label="Loading history..." />
  }

  if (revisions.length === 0) {
    return (
      <EmptyState
        icon={<Clock className="w-8 h-8 text-border" />}
        title="No revision history"
        description="Changes will appear here as the driver is updated."
      />
    )
  }

  return (
    <div className="space-y-3">
      <h4 className="text-[11px] font-medium text-text-placeholder uppercase tracking-wide">
        Change History ({revisions.length})
      </h4>
      {revisions.map((rev, idx) => (
        <RevisionCard key={idx} revision={rev} />
      ))}
    </div>
  )
}

function RevisionCard({ revision }: { revision: RevisionEntry }) {
  const [expanded, setExpanded] = useState(false)
  const hasChanges = revision.changes && Object.keys(revision.changes).length > 0

  const typeCls = REVISION_TYPE_COLORS[revision.revision_type] || 'bg-[#F0F0F0] text-[#666666]'
  const timeAgo = formatRelativeTime(revision.created_at)

  return (
    <div className="bg-[#F4F4F4] border border-border rounded-xl px-3 py-2.5">
      <div className="flex items-center gap-2 mb-1">
        <span className={`inline-flex px-1.5 py-0.5 text-[10px] font-medium rounded ${typeCls}`}>
          {revision.revision_type}
        </span>
        <span className="text-[11px] text-text-placeholder">{timeAgo}</span>
        <span className="text-[11px] text-text-placeholder">
          by {formatRevisionAuthor(revision.created_by)}
        </span>
      </div>
      {revision.diff_summary && (
        <p className="text-[12px] text-[#666666] leading-relaxed">
          {revision.diff_summary}
        </p>
      )}
      {hasChanges && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-1.5 flex items-center gap-1 text-[11px] text-text-placeholder hover:text-[#666666] transition-colors"
        >
          {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
          Field changes
        </button>
      )}
      {expanded && revision.changes && (
        <div className="mt-2 space-y-1 pl-2 border-l-2 border-border">
          {Object.entries(revision.changes).map(([field, change]) => (
            <div key={field} className="text-[11px]">
              <span className="font-medium text-[#666666]">{field}:</span>{' '}
              {typeof change === 'object' && change !== null && 'old' in change && 'new' in change ? (
                <>
                  <span className="text-red-400 line-through">{String((change as { old: unknown }).old || '—')}</span>
                  {' → '}
                  <span className="text-brand-primary">{String((change as { new: unknown }).new || '—')}</span>
                </>
              ) : (
                <span className="text-[#666666]">{String(change)}</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
