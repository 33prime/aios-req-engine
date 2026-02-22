'use client'

import { useState, useEffect, useMemo } from 'react'
import {
  AlertTriangle,
  Target,
  BarChart3,
  FileText,
  Users,
  Puzzle,
  Link2,
  ChevronDown,
  ChevronRight,
  Workflow,
  Sparkles,
  CheckCircle2,
  Circle,
  Info,
  DollarSign,
  Pencil,
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
import { getBRDDriverDetail, updateDriverFinancials } from '@/lib/api'
import { getTopicsForDriverType, inferTopicsFromText } from '@/lib/topic-role-map'
import type {
  BusinessDriver,
  BusinessDriverDetail,
  RevisionEntry,
  AssociatedPersona,
  VisionAlignment,
  StakeholderBRDSummary,
} from '@/types/workspace'

type DriverType = 'pain' | 'goal' | 'kpi'
type TabId = 'intelligence' | 'who_has_data' | 'evidence_history' | 'connections'

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
  const [activeTab, setActiveTab] = useState<TabId>('intelligence')
  const [detail, setDetail] = useState<BusinessDriverDetail | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getBRDDriverDetail(projectId, driverId)
      .then((data) => {
        if (!cancelled) setDetail(data)
      })
      .catch((err) => {
        console.error('Failed to load driver detail:', err)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [projectId, driverId])

  const config = TYPE_CONFIG[driverType]
  const Icon = config.icon

  const connectionCount = useMemo(() => {
    if (detail) {
      return (detail.associated_personas?.length || 0) +
        (detail.associated_features?.length || 0) +
        (detail.related_drivers?.length || 0)
    }
    return (initialData.linked_persona_count ?? 0) +
      (initialData.linked_feature_count ?? 0) +
      (initialData.linked_workflow_count ?? 0)
  }, [detail, initialData])

  const tabs: DrawerTab[] = useMemo(() => [
    { id: 'intelligence', label: 'Intelligence', icon: Sparkles },
    { id: 'who_has_data', label: 'Who Has Data', icon: Users },
    { id: 'evidence_history', label: 'Evidence', icon: FileText },
    {
      id: 'connections',
      label: 'Connections',
      icon: Link2,
      badge: connectionCount > 0 ? (
        <span className="ml-1 text-[10px] bg-[#F0F0F0] text-[#666666] px-1.5 py-0.5 rounded-full">
          {connectionCount}
        </span>
      ) : undefined,
    },
  ], [connectionCount])

  return (
    <DrawerShell
      onClose={onClose}
      icon={Icon}
      entityLabel={config.label}
      title={initialData.description}
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
      {activeTab === 'intelligence' && (
        <IntelligenceTab
          driverType={driverType}
          projectId={projectId}
          driverId={driverId}
          initialData={initialData}
          detail={detail}
          loading={loading}
          onDetailUpdate={setDetail}
        />
      )}
      {activeTab === 'who_has_data' && (
        <WhoHasTheData
          topics={[
            ...getTopicsForDriverType(driverType),
            ...inferTopicsFromText(initialData.description),
          ]}
          stakeholders={stakeholders}
          evidence={detail?.evidence || initialData.evidence || []}
        />
      )}
      {activeTab === 'evidence_history' && (
        <EvidenceHistoryTab
          evidence={detail?.evidence || initialData.evidence || []}
          revisions={detail?.revisions || []}
          loading={loading}
        />
      )}
      {activeTab === 'connections' && (
        <ConnectionsTab
          detail={detail}
          initialData={initialData}
          loading={loading}
        />
      )}
    </DrawerShell>
  )
}

// ============================================================================
// Intelligence Tab (replaces Details)
// ============================================================================

function IntelligenceTab({
  driverType,
  projectId,
  driverId,
  initialData,
  detail,
  loading,
  onDetailUpdate,
}: {
  driverType: DriverType
  projectId: string
  driverId: string
  initialData: BusinessDriver
  detail: BusinessDriverDetail | null
  loading: boolean
  onDetailUpdate: (d: BusinessDriverDetail) => void
}) {
  const d = detail || initialData
  const [editingFinancial, setEditingFinancial] = useState(false)
  const [savingFinancial, setSavingFinancial] = useState(false)

  // Build narrative from available data
  const narrative = useMemo(() => buildNarrative(driverType, d), [driverType, d])
  const score = d.relatability_score ?? 0
  const va = d.vision_alignment

  // Detect missing data
  const missingData = useMemo(() => {
    const items: string[] = []
    if (!d.linked_persona_count && !(detail?.associated_personas?.length))
      items.push('Not linked to any persona — consider mapping who experiences this')
    if (!d.linked_workflow_count)
      items.push('Not linked to any workflow — consider mapping where this occurs')
    if (!d.linked_feature_count && !(detail?.associated_features?.length))
      items.push('Not linked to any feature — consider mapping what addresses this')
    if (driverType === 'kpi') {
      if (!d.baseline_value) items.push('Missing baseline value')
      if (!d.target_value) items.push('Missing target value')
      if (!d.measurement_method) items.push('Missing measurement method')
    }
    if (driverType === 'pain' && !d.severity) items.push('Missing severity assessment')
    if (driverType === 'goal' && !d.success_criteria) items.push('Missing success criteria')
    return items
  }, [d, detail, driverType])

  return (
    <div className="space-y-6">
      {/* Financial Impact Overview (KPI only — top position) */}
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
              const updated = await getBRDDriverDetail(projectId, driverId)
              onDetailUpdate(updated)
              setEditingFinancial(false)
            } catch (err) {
              console.error('Failed to save financial impact:', err)
            } finally {
              setSavingFinancial(false)
            }
          }}
        />
      )}

      {/* AI Narrative */}
      {narrative && (
        <div className="bg-[#F4F4F4] border border-[#E5E5E5] rounded-xl px-4 py-3">
          <p className="text-[13px] text-[#333333] leading-relaxed">{narrative}</p>
        </div>
      )}

      {/* Relatability Score + Vision Alignment */}
      <div className="flex items-center gap-4">
        <div className="flex-1">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-medium text-[#999999] uppercase tracking-wide">
              Relevance Score
            </span>
            <span className="text-[12px] font-semibold text-[#333333]">{score.toFixed(1)}</span>
          </div>
          <div className="h-2 bg-[#F0F0F0] rounded-full overflow-hidden">
            <div
              className="h-full bg-[#3FAF7A] rounded-full transition-all duration-500"
              style={{ width: `${Math.min((score / 30) * 100, 100)}%` }}
            />
          </div>
        </div>
        {va && <VisionAlignmentBadge alignment={va} />}
      </div>

      {/* Missing Data Callouts */}
      {missingData.length > 0 && (
        <div className="space-y-1.5">
          {missingData.map((msg, i) => (
            <div
              key={i}
              className="flex items-start gap-2 text-[12px] text-[#666666] bg-[#F4F4F4] border border-[#E5E5E5] rounded-lg px-3 py-2"
            >
              <Info className="w-3.5 h-3.5 mt-0.5 flex-shrink-0 text-[#999999]" />
              {msg}
            </div>
          ))}
        </div>
      )}

      {/* Type-specific fields */}
      <div>
        <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-3">
          {driverType === 'pain' ? 'Pain Details' : driverType === 'goal' ? 'Goal Details' : 'Metric Details'}
        </h4>

        {driverType === 'pain' && (
          <div className="space-y-3">
            <FieldRow label="Severity" value={d.severity} badge />
            <FieldRow label="Business Impact" value={d.business_impact} />
            <FieldRow label="Affected Users" value={d.affected_users} />
            <FieldRow label="Current Workaround" value={d.current_workaround} />
            <FieldRow label="Frequency" value={d.frequency} />
          </div>
        )}

        {driverType === 'goal' && (
          <div className="space-y-3">
            <FieldRow label="Success Criteria" value={d.success_criteria} />
            <FieldRow label="Owner" value={d.owner} />
            <FieldRow label="Timeframe" value={d.goal_timeframe} />
            <FieldRow label="Dependencies" value={d.dependencies} />
          </div>
        )}

        {driverType === 'kpi' && (
          <div className="space-y-3">
            <KPIField label="Baseline" value={d.baseline_value} />
            <KPIField label="Target" value={d.target_value} />
            <KPIField label="Measurement Method" value={d.measurement_method} />
            <KPIField label="Tracking Frequency" value={d.tracking_frequency} />
            <KPIField label="Data Source" value={d.data_source} />
            <KPIField label="Responsible Team" value={d.responsible_team} />
          </div>
        )}

      </div>

      {loading && !detail && (
        <Spinner size="sm" label="Loading details..." />
      )}
    </div>
  )
}

// ============================================================================
// Financial Overview (inline at top of KPI Intelligence tab)
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
        className="flex items-center gap-2 w-full px-3 py-2.5 text-[12px] font-medium text-[#25785A] bg-white border border-[#3FAF7A] border-dashed rounded-lg hover:bg-[#E8F5E9] transition-colors"
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
    <div className="border border-[#E5E5E5] rounded-xl overflow-hidden bg-white">
      <div className="px-4 py-3 bg-[#F4F4F4] border-b border-[#E5E5E5]">
        <div className="flex items-center gap-2">
          <DollarSign className="w-4 h-4 text-[#3FAF7A]" />
          <span className="text-[13px] font-semibold text-[#333333]">Financial Impact</span>
        </div>
      </div>
      <div className="p-4 space-y-3">
        {/* Impact Type */}
        <div>
          <span className="text-[11px] font-medium text-[#999999] uppercase tracking-wide block mb-1.5">Type</span>
          <div className="flex flex-wrap gap-1.5">
            {IMPACT_TYPES.map((t) => (
              <button
                key={t.id}
                onClick={() => setType(t.id)}
                className={`px-2.5 py-1 text-[11px] font-medium rounded-lg transition-colors ${
                  type === t.id
                    ? 'bg-[#3FAF7A] text-white'
                    : 'bg-white border border-[#E5E5E5] text-[#666666] hover:border-[#3FAF7A]'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* Range */}
        <div>
          <span className="text-[11px] font-medium text-[#999999] uppercase tracking-wide block mb-1.5">Value Range</span>
          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[12px] text-[#999999]">$</span>
              <input
                type="text"
                value={low}
                onChange={(e) => setLow(e.target.value)}
                placeholder="Low"
                className="w-full pl-6 pr-3 py-1.5 text-[12px] border border-[#E5E5E5] rounded-lg bg-white text-[#333333] placeholder:text-[#999999] focus:outline-none focus:border-[#3FAF7A]"
              />
            </div>
            <span className="text-[12px] text-[#999999]">—</span>
            <div className="relative flex-1">
              <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[12px] text-[#999999]">$</span>
              <input
                type="text"
                value={high}
                onChange={(e) => setHigh(e.target.value)}
                placeholder="High"
                className="w-full pl-6 pr-3 py-1.5 text-[12px] border border-[#E5E5E5] rounded-lg bg-white text-[#333333] placeholder:text-[#999999] focus:outline-none focus:border-[#3FAF7A]"
              />
            </div>
          </div>
        </div>

        {/* Timeframe */}
        <div>
          <span className="text-[11px] font-medium text-[#999999] uppercase tracking-wide block mb-1.5">Timeframe</span>
          <div className="flex gap-1">
            {TIMEFRAMES.map((tf) => (
              <button
                key={tf.id}
                onClick={() => setTimeframe(tf.id)}
                className={`flex-1 px-2 py-1.5 text-[11px] font-medium rounded-lg transition-colors ${
                  timeframe === tf.id
                    ? 'bg-[#3FAF7A] text-white'
                    : 'bg-white border border-[#E5E5E5] text-[#666666] hover:border-[#3FAF7A]'
                }`}
              >
                {tf.label}
              </button>
            ))}
          </div>
        </div>

        {/* Confidence */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-[11px] font-medium text-[#999999] uppercase tracking-wide">Confidence</span>
            <span className="text-[12px] font-semibold text-[#333333]">{confidence}%</span>
          </div>
          <input
            type="range"
            min={0}
            max={100}
            value={confidence}
            onChange={(e) => setConfidence(parseInt(e.target.value))}
            className="w-full h-1.5 bg-[#E5E5E5] rounded-full appearance-none cursor-pointer accent-[#3FAF7A]"
          />
        </div>

        {/* Source */}
        <div>
          <span className="text-[11px] font-medium text-[#999999] uppercase tracking-wide block mb-1.5">Source (optional)</span>
          <input
            type="text"
            value={source}
            onChange={(e) => setSource(e.target.value)}
            placeholder="e.g. CFO estimate, industry benchmark..."
            className="w-full px-3 py-1.5 text-[12px] border border-[#E5E5E5] rounded-lg bg-white text-[#333333] placeholder:text-[#999999] focus:outline-none focus:border-[#3FAF7A]"
          />
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-2 pt-1">
          <button
            onClick={onCancel}
            className="px-3 py-1.5 text-[12px] font-medium text-[#666666] hover:text-[#333333] rounded-lg hover:bg-[#F0F0F0] transition-colors"
          >
            Cancel
          </button>
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
            className="px-4 py-1.5 text-[12px] font-medium rounded-lg bg-[#3FAF7A] text-white hover:bg-[#25785A] transition-colors disabled:opacity-50"
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
  const desc = d.description

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
    low: { bg: 'bg-[#F0F0F0]', text: 'text-[#999999]', label: 'Low alignment' },
    unrelated: { bg: 'bg-[#F0F0F0]', text: 'text-[#999999]', label: 'Unrelated' },
  }
  const c = config[alignment] || config.low
  return (
    <div className="flex-shrink-0 text-center">
      <span className="text-[10px] font-medium text-[#999999] uppercase tracking-wide block mb-1">Vision</span>
      <span className={`inline-flex px-2.5 py-1 text-[11px] font-medium rounded-full ${c.bg} ${c.text}`}>
        {c.label}
      </span>
    </div>
  )
}

// ============================================================================
// Connections Tab
// ============================================================================

function ConnectionsTab({
  detail,
  initialData,
  loading,
}: {
  detail: BusinessDriverDetail | null
  initialData: BusinessDriver
  loading: boolean
}) {
  const personas = detail?.associated_personas || []
  const features = detail?.associated_features || []
  const relatedDrivers = detail?.related_drivers || []
  const workflowCount = (detail || initialData).linked_workflow_count ?? 0

  if (loading && !detail) {
    return <Spinner size="sm" label="Loading connections..." />
  }

  const isEmpty = personas.length === 0 && features.length === 0 && relatedDrivers.length === 0 && workflowCount === 0

  if (isEmpty) {
    return (
      <EmptyState
        icon={<Link2 className="w-8 h-8 text-[#E5E5E5]" />}
        title="No connections found"
        description="Run enrichment or manually link entities to build the relationship graph."
      />
    )
  }

  return (
    <div className="space-y-6">
      {/* Actors */}
      {personas.length > 0 && (
        <ConnectionGroup
          icon={Users}
          title="Actors"
          count={personas.length}
        >
          {personas.map((p) => (
            <ConnectionItem
              key={p.id}
              name={p.name}
              subtitle={p.role || undefined}
              reason={p.association_reason}
            />
          ))}
        </ConnectionGroup>
      )}

      {/* Features */}
      {features.length > 0 && (
        <ConnectionGroup
          icon={Puzzle}
          title="Features"
          count={features.length}
        >
          {features.map((f) => (
            <ConnectionItem
              key={f.id}
              name={f.name}
              subtitle={f.category || undefined}
              reason={f.association_reason}
              confirmed={f.confirmation_status === 'confirmed_consultant' || f.confirmation_status === 'confirmed_client'}
            />
          ))}
        </ConnectionGroup>
      )}

      {/* Workflows */}
      {workflowCount > 0 && (
        <ConnectionGroup
          icon={Workflow}
          title="Workflow Steps"
          count={workflowCount}
        >
          <p className="text-[12px] text-[#999999] px-3 py-2">
            {workflowCount} workflow step{workflowCount > 1 ? 's' : ''} linked via enrichment analysis.
          </p>
        </ConnectionGroup>
      )}

      {/* Related Drivers */}
      {relatedDrivers.length > 0 && (
        <ConnectionGroup
          icon={Link2}
          title="Related Drivers"
          count={relatedDrivers.length}
        >
          {relatedDrivers.map((r) => (
            <div key={r.id} className="px-3 py-2 border-b border-[#F0F0F0] last:border-0">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-medium uppercase px-1.5 py-0.5 rounded bg-[#F0F0F0] text-[#666666]">
                  {r.driver_type}
                </span>
                <span className="text-[13px] text-[#333333] line-clamp-1">{r.description}</span>
              </div>
              {r.relationship && (
                <p className="text-[11px] text-[#999999] mt-1 pl-0.5">{r.relationship}</p>
              )}
            </div>
          ))}
        </ConnectionGroup>
      )}
    </div>
  )
}

function ConnectionItem({
  name,
  subtitle,
  reason,
  confirmed,
}: {
  name: string
  subtitle?: string
  reason?: string
  confirmed?: boolean
}) {
  return (
    <div className="px-3 py-2.5 border-b border-[#F0F0F0] last:border-0">
      <div className="flex items-center gap-2">
        {confirmed !== undefined && (
          confirmed
            ? <CheckCircle2 className="w-3.5 h-3.5 text-[#3FAF7A] flex-shrink-0" />
            : <Circle className="w-3.5 h-3.5 text-[#E5E5E5] flex-shrink-0" />
        )}
        <span className="text-[13px] text-[#333333] font-medium">{name}</span>
        {subtitle && (
          <span className="text-[11px] text-[#999999]">{subtitle}</span>
        )}
      </div>
      {reason && (
        <p className="text-[11px] text-[#999999] mt-0.5 pl-5">{reason}</p>
      )}
    </div>
  )
}

// ============================================================================
// Evidence & History Tab (combined)
// ============================================================================

function EvidenceHistoryTab({
  evidence,
  revisions,
  loading,
}: {
  evidence: import('@/types/workspace').BRDEvidence[]
  revisions: RevisionEntry[]
  loading: boolean
}) {
  if (loading && evidence.length === 0 && revisions.length === 0) {
    return <Spinner size="sm" label="Loading..." />
  }

  return (
    <div className="space-y-6">
      {/* Evidence */}
      <div>
        <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2">
          Evidence Sources
        </h4>
        {evidence.length > 0 ? (
          <EvidenceBlock evidence={evidence} maxItems={100} />
        ) : (
          <p className="text-[13px] text-[#999999] italic">No evidence sources linked.</p>
        )}
      </div>

      {/* History */}
      {revisions.length > 0 && (
        <div>
          <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2">
            Change History
          </h4>
          <div className="space-y-3">
            {revisions.map((rev, idx) => (
              <RevisionCard key={idx} revision={rev} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function RevisionCard({ revision }: { revision: RevisionEntry }) {
  const [expanded, setExpanded] = useState(false)
  const hasChanges = revision.changes && Object.keys(revision.changes).length > 0

  const typeCls = REVISION_TYPE_COLORS[revision.revision_type] || 'bg-[#F0F0F0] text-[#666666]'
  const timeAgo = formatRelativeTime(revision.created_at)

  return (
    <div className="bg-[#F4F4F4] border border-[#E5E5E5] rounded-xl px-3 py-2.5">
      <div className="flex items-center gap-2 mb-1">
        <span className={`inline-flex px-1.5 py-0.5 text-[10px] font-medium rounded ${typeCls}`}>
          {revision.revision_type}
        </span>
        <span className="text-[11px] text-[#999999]">{timeAgo}</span>
        <span className="text-[11px] text-[#999999]">
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
          className="mt-1.5 flex items-center gap-1 text-[11px] text-[#999999] hover:text-[#666666] transition-colors"
        >
          {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
          Field changes
        </button>
      )}
      {expanded && revision.changes && (
        <div className="mt-2 space-y-1 pl-2 border-l-2 border-[#E5E5E5]">
          {Object.entries(revision.changes).map(([field, change]) => (
            <div key={field} className="text-[11px]">
              <span className="font-medium text-[#666666]">{field}:</span>{' '}
              {typeof change === 'object' && change !== null && 'old' in change && 'new' in change ? (
                <>
                  <span className="text-red-400 line-through">{String((change as { old: unknown }).old || '—')}</span>
                  {' → '}
                  <span className="text-[#3FAF7A]">{String((change as { new: unknown }).new || '—')}</span>
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

// ============================================================================
// Shared helpers
// ============================================================================

function FieldRow({ label, value, badge }: { label: string; value?: string | null; badge?: boolean }) {
  if (!value) return null
  return (
    <div className="flex items-start gap-3">
      <span className="text-[12px] font-medium text-[#999999] min-w-[120px] pt-0.5">{label}</span>
      {badge ? (
        <SeverityBadge value={value} />
      ) : (
        <span className="text-[13px] text-[#333333] leading-relaxed">{value}</span>
      )}
    </div>
  )
}

function KPIField({ label, value }: { label: string; value?: string | null }) {
  const isMissing = !value
  return (
    <div className={`flex items-start gap-3 ${isMissing ? 'rounded-lg border border-dashed border-[#E5E5E5] bg-[#F4F4F4] px-3 py-2 -mx-3' : ''}`}>
      <span className="text-[12px] font-medium text-[#999999] min-w-[140px] pt-0.5">{label}</span>
      {isMissing ? (
        <span className="text-[12px] text-[#999999] italic">Data needed</span>
      ) : (
        <span className="text-[13px] text-[#333333] leading-relaxed">{value}</span>
      )}
    </div>
  )
}

function SeverityBadge({ value }: { value: string }) {
  const isHigh = value.toLowerCase() === 'critical' || value.toLowerCase() === 'high'
  return (
    <span className={`inline-flex px-2 py-0.5 text-[11px] font-medium rounded-full ${
      isHigh ? 'bg-red-100 text-red-700' : 'bg-[#F0F0F0] text-[#666666]'
    }`}>
      {value}
    </span>
  )
}
