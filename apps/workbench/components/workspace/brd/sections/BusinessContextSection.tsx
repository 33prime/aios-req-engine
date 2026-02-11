'use client'

import { useState } from 'react'
import { Building2, AlertTriangle, Target, Eye, BarChart3, Pencil, ChevronDown, ChevronRight } from 'lucide-react'
import { SectionHeader } from '../components/SectionHeader'
import { BRDStatusBadge } from '../components/StatusBadge'
import { ConfirmActions } from '../components/ConfirmActions'
import { EvidenceBlock } from '../components/EvidenceBlock'
import { BusinessDriverDetailDrawer } from '../components/BusinessDriverDetailDrawer'
import type { BRDWorkspaceData, BusinessDriver } from '@/types/workspace'

interface BusinessContextSectionProps {
  data: BRDWorkspaceData['business_context']
  projectId: string
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
  onConfirmAll: (entityType: string, ids: string[]) => void
  onUpdateVision: (vision: string) => void
  onUpdateBackground: (background: string) => void
  onStatusClick?: (entityType: string, entityId: string, entityName: string, status?: string | null) => void
}

const SHOW_MAX_PAINS = 8
const SHOW_MAX_GOALS = 8
const SHOW_MAX_METRICS = 5

// ============================================================================
// Pain Point Accordion Card
// ============================================================================

function PainPointCard({
  pain,
  onConfirm,
  onNeedsReview,
  onStatusClick,
  onDetailClick,
}: {
  pain: BusinessDriver
  onConfirm: () => void
  onNeedsReview: () => void
  onStatusClick?: () => void
  onDetailClick: () => void
}) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-gray-50/50 transition-colors"
      >
        <ChevronRight
          className={`w-4 h-4 text-[#999999] shrink-0 transition-transform duration-200 ${expanded ? 'rotate-90' : ''}`}
        />
        <AlertTriangle className="w-4 h-4 text-[#999999] shrink-0" />
        <span className="text-[14px] font-semibold text-[#333333] truncate flex-1">{pain.description}</span>
        <span onClick={(e) => e.stopPropagation()}>
          <BRDStatusBadge status={pain.confirmation_status} onClick={onStatusClick} />
        </span>
      </button>

      <div className={`overflow-hidden transition-all duration-200 ${expanded ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'}`}>
        <div className="px-5 pb-5 pt-1">
          {/* Detail fields */}
          <div className="space-y-2 text-[13px] text-[#666666] mb-3">
            {pain.severity && (
              <div><span className="font-medium text-[#333333]">Severity:</span> {pain.severity}</div>
            )}
            {pain.business_impact && (
              <div><span className="font-medium text-[#333333]">Impact:</span> {pain.business_impact}</div>
            )}
            {pain.affected_users && (
              <div><span className="font-medium text-[#333333]">Affected Users:</span> {pain.affected_users}</div>
            )}
            {pain.current_workaround && (
              <div><span className="font-medium text-[#333333]">Current Workaround:</span> {pain.current_workaround}</div>
            )}
          </div>

          {/* Persona chips */}
          {pain.associated_persona_names && pain.associated_persona_names.length > 0 && (
            <div className="flex flex-wrap gap-1 mb-3">
              {pain.associated_persona_names.map((name) => (
                <span key={name} className="px-2 py-0.5 text-[10px] font-medium bg-[#E8F5E9] text-[#25785A] rounded-full">
                  {name}
                </span>
              ))}
            </div>
          )}

          <EvidenceBlock evidence={pain.evidence || []} />

          {/* Actions row */}
          <div className="mt-3 pt-3 border-t border-[#E5E5E5] flex items-center justify-between">
            <ConfirmActions status={pain.confirmation_status} onConfirm={onConfirm} onNeedsReview={onNeedsReview} />
            <button
              onClick={onDetailClick}
              className="text-[11px] text-[#999999] hover:text-[#3FAF7A] transition-colors"
            >
              View details →
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// Goal Accordion Card
// ============================================================================

function GoalCard({
  goal,
  onConfirm,
  onNeedsReview,
  onStatusClick,
  onDetailClick,
}: {
  goal: BusinessDriver
  onConfirm: () => void
  onNeedsReview: () => void
  onStatusClick?: () => void
  onDetailClick: () => void
}) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-gray-50/50 transition-colors"
      >
        <ChevronRight
          className={`w-4 h-4 text-[#999999] shrink-0 transition-transform duration-200 ${expanded ? 'rotate-90' : ''}`}
        />
        <Target className="w-4 h-4 text-[#3FAF7A] shrink-0" />
        <span className="text-[14px] font-semibold text-[#333333] truncate flex-1">{goal.description}</span>
        <span onClick={(e) => e.stopPropagation()}>
          <BRDStatusBadge status={goal.confirmation_status} onClick={onStatusClick} />
        </span>
      </button>

      <div className={`overflow-hidden transition-all duration-200 ${expanded ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'}`}>
        <div className="px-5 pb-5 pt-1">
          <div className="space-y-2 text-[13px] text-[#666666] mb-3">
            {goal.success_criteria && (
              <div><span className="font-medium text-[#333333]">Success Criteria:</span> {goal.success_criteria}</div>
            )}
            {goal.owner && (
              <div><span className="font-medium text-[#333333]">Owner:</span> {goal.owner}</div>
            )}
            {goal.goal_timeframe && (
              <div><span className="font-medium text-[#333333]">Timeframe:</span> {goal.goal_timeframe}</div>
            )}
          </div>

          {/* Persona chips */}
          {goal.associated_persona_names && goal.associated_persona_names.length > 0 && (
            <div className="flex flex-wrap gap-1 mb-3">
              {goal.associated_persona_names.map((name) => (
                <span key={name} className="px-2 py-0.5 text-[10px] font-medium bg-[#E8F5E9] text-[#25785A] rounded-full">
                  {name}
                </span>
              ))}
            </div>
          )}

          <EvidenceBlock evidence={goal.evidence || []} />

          <div className="mt-3 pt-3 border-t border-[#E5E5E5] flex items-center justify-between">
            <ConfirmActions status={goal.confirmation_status} onConfirm={onConfirm} onNeedsReview={onNeedsReview} />
            <button
              onClick={onDetailClick}
              className="text-[11px] text-[#999999] hover:text-[#3FAF7A] transition-colors"
            >
              View details →
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// Metric Accordion Card
// ============================================================================

function MetricCard({
  metric,
  onConfirm,
  onNeedsReview,
  onStatusClick,
  onDetailClick,
}: {
  metric: BusinessDriver
  onConfirm: () => void
  onNeedsReview: () => void
  onStatusClick?: () => void
  onDetailClick: () => void
}) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-gray-50/50 transition-colors"
      >
        <ChevronRight
          className={`w-4 h-4 text-[#999999] shrink-0 transition-transform duration-200 ${expanded ? 'rotate-90' : ''}`}
        />
        <BarChart3 className="w-4 h-4 text-[#3FAF7A] shrink-0" />
        <span className="text-[14px] font-semibold text-[#333333] truncate flex-1">{metric.description}</span>
        <span onClick={(e) => e.stopPropagation()}>
          <BRDStatusBadge status={metric.confirmation_status} onClick={onStatusClick} />
        </span>
      </button>

      <div className={`overflow-hidden transition-all duration-200 ${expanded ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'}`}>
        <div className="px-5 pb-5 pt-1">
          <div className="space-y-2 text-[13px] text-[#666666] mb-3">
            {metric.baseline_value && (
              <div><span className="font-medium text-[#333333]">Current State:</span> {metric.baseline_value}</div>
            )}
            {metric.target_value && (
              <div><span className="font-medium text-[#333333]">Target:</span> {metric.target_value}</div>
            )}
            {metric.measurement_method && (
              <div><span className="font-medium text-[#333333]">Measurement:</span> {metric.measurement_method}</div>
            )}
          </div>

          {/* Missing fields indicator */}
          {(metric.missing_field_count ?? 0) > 0 && (
            <div className="flex items-center gap-1 text-[11px] text-[#999999] mb-3">
              <span className="w-1.5 h-1.5 rounded-full bg-[#999999]" />
              {metric.missing_field_count} field(s) need data
            </div>
          )}

          <EvidenceBlock evidence={metric.evidence || []} />

          <div className="mt-3 pt-3 border-t border-[#E5E5E5] flex items-center justify-between">
            <ConfirmActions status={metric.confirmation_status} onConfirm={onConfirm} onNeedsReview={onNeedsReview} />
            <button
              onClick={onDetailClick}
              className="text-[11px] text-[#999999] hover:text-[#3FAF7A] transition-colors"
            >
              View details →
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// Main Section
// ============================================================================

export function BusinessContextSection({
  data,
  projectId,
  onConfirm,
  onNeedsReview,
  onConfirmAll,
  onUpdateVision,
  onUpdateBackground,
  onStatusClick,
}: BusinessContextSectionProps) {
  const [editingVision, setEditingVision] = useState(false)
  const [visionDraft, setVisionDraft] = useState(data.vision || '')
  const [editingBackground, setEditingBackground] = useState(false)
  const [backgroundDraft, setBackgroundDraft] = useState(data.background || '')
  const [showAllPains, setShowAllPains] = useState(false)
  const [showAllGoals, setShowAllGoals] = useState(false)
  const [showAllMetrics, setShowAllMetrics] = useState(false)
  const [selectedDriver, setSelectedDriver] = useState<{ id: string; type: 'pain' | 'goal' | 'kpi'; data: BusinessDriver } | null>(null)

  const handleSaveVision = () => {
    onUpdateVision(visionDraft)
    setEditingVision(false)
  }

  const handleSaveBackground = () => {
    onUpdateBackground(backgroundDraft)
    setEditingBackground(false)
  }

  const confirmedPains = data.pain_points.filter(
    (p) => p.confirmation_status === 'confirmed_consultant' || p.confirmation_status === 'confirmed_client'
  ).length
  const confirmedGoals = data.goals.filter(
    (g) => g.confirmation_status === 'confirmed_consultant' || g.confirmation_status === 'confirmed_client'
  ).length
  const confirmedMetrics = data.success_metrics.filter(
    (m) => m.confirmation_status === 'confirmed_consultant' || m.confirmation_status === 'confirmed_client'
  ).length

  const visiblePains = showAllPains ? data.pain_points : data.pain_points.slice(0, SHOW_MAX_PAINS)
  const visibleGoals = showAllGoals ? data.goals : data.goals.slice(0, SHOW_MAX_GOALS)
  const visibleMetrics = showAllMetrics ? data.success_metrics : data.success_metrics.slice(0, SHOW_MAX_METRICS)

  return (
    <section className="space-y-8">
      {/* Background */}
      <div>
        <h2 className="text-lg font-semibold text-[#333333] mb-3 flex items-center gap-2">
          <Building2 className="w-5 h-5 text-[#999999]" />
          Background
        </h2>
        <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] p-5">
          {editingBackground ? (
            <div className="space-y-3">
              <textarea
                value={backgroundDraft}
                onChange={(e) => setBackgroundDraft(e.target.value)}
                className="w-full p-3 text-[14px] text-[#333333] border border-[#E5E5E5] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#3FAF7A]/30 focus:border-[#3FAF7A] resize-y min-h-[80px]"
                placeholder="Describe the company background..."
                autoFocus
              />
              <div className="flex items-center gap-2">
                <button
                  onClick={handleSaveBackground}
                  className="px-3 py-1.5 text-[12px] font-medium text-white bg-[#3FAF7A] rounded-xl hover:bg-[#25785A] transition-colors"
                >
                  Save
                </button>
                <button
                  onClick={() => { setEditingBackground(false); setBackgroundDraft(data.background || '') }}
                  className="px-3 py-1.5 text-[12px] font-medium text-[#666666] bg-white border border-[#E5E5E5] rounded-xl hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="group">
              {data.company_name && (
                <p className="text-[14px] font-medium text-[#333333] mb-1">
                  {data.company_name}
                  {data.industry && (
                    <span className="text-[#666666] font-normal"> &mdash; {data.industry}</span>
                  )}
                </p>
              )}
              {data.background ? (
                <p className="text-[14px] text-[#666666] leading-relaxed">{data.background}</p>
              ) : (
                <p className="text-[13px] text-[#999999] italic">No background description yet. Click to add one.</p>
              )}
              <button
                onClick={() => { setBackgroundDraft(data.background || ''); setEditingBackground(true) }}
                className="mt-2 inline-flex items-center gap-1 text-[12px] text-[#999999] hover:text-[#3FAF7A] transition-colors opacity-0 group-hover:opacity-100"
              >
                <Pencil className="w-3 h-3" />
                Edit
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Pain Points */}
      <div>
        <SectionHeader
          title="Pain Points"
          count={data.pain_points.length}
          confirmedCount={confirmedPains}
          onConfirmAll={() => onConfirmAll('business_driver', data.pain_points.map((p) => p.id))}
        />
        {data.pain_points.length === 0 ? (
          <p className="text-[13px] text-[#999999] italic">No pain points identified yet</p>
        ) : (
          <div className="space-y-3">
            {visiblePains.map((pain) => (
              <PainPointCard
                key={pain.id}
                pain={pain}
                onConfirm={() => onConfirm('business_driver', pain.id)}
                onNeedsReview={() => onNeedsReview('business_driver', pain.id)}
                onStatusClick={onStatusClick ? () => onStatusClick('business_driver', pain.id, pain.description.slice(0, 60), pain.confirmation_status) : undefined}
                onDetailClick={() => setSelectedDriver({ id: pain.id, type: 'pain', data: pain })}
              />
            ))}
            {data.pain_points.length > SHOW_MAX_PAINS && !showAllPains && (
              <button
                onClick={() => setShowAllPains(true)}
                className="flex items-center gap-1.5 px-3 py-2 text-[12px] font-medium text-[#999999] hover:text-[#3FAF7A] transition-colors w-full justify-center"
              >
                <ChevronDown className="w-3.5 h-3.5" />
                Show all {data.pain_points.length} pain points
              </button>
            )}
          </div>
        )}
      </div>

      {/* Business Goals */}
      <div>
        <SectionHeader
          title="Business Goals"
          count={data.goals.length}
          confirmedCount={confirmedGoals}
          onConfirmAll={() => onConfirmAll('business_driver', data.goals.map((g) => g.id))}
        />
        {data.goals.length === 0 ? (
          <p className="text-[13px] text-[#999999] italic">No business goals identified yet</p>
        ) : (
          <div className="space-y-3">
            {visibleGoals.map((goal) => (
              <GoalCard
                key={goal.id}
                goal={goal}
                onConfirm={() => onConfirm('business_driver', goal.id)}
                onNeedsReview={() => onNeedsReview('business_driver', goal.id)}
                onStatusClick={onStatusClick ? () => onStatusClick('business_driver', goal.id, goal.description.slice(0, 60), goal.confirmation_status) : undefined}
                onDetailClick={() => setSelectedDriver({ id: goal.id, type: 'goal', data: goal })}
              />
            ))}
            {data.goals.length > SHOW_MAX_GOALS && !showAllGoals && (
              <button
                onClick={() => setShowAllGoals(true)}
                className="flex items-center gap-1.5 px-3 py-2 text-[12px] font-medium text-[#999999] hover:text-[#3FAF7A] transition-colors w-full justify-center"
              >
                <ChevronDown className="w-3.5 h-3.5" />
                Show all {data.goals.length} goals
              </button>
            )}
          </div>
        )}
      </div>

      {/* Vision */}
      <div>
        <h2 className="text-lg font-semibold text-[#333333] mb-3 flex items-center gap-2">
          <Eye className="w-5 h-5 text-[#999999]" />
          Vision
        </h2>
        <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] p-5">
          {editingVision ? (
            <div className="space-y-3">
              <textarea
                value={visionDraft}
                onChange={(e) => setVisionDraft(e.target.value)}
                className="w-full p-3 text-[14px] text-[#333333] border border-[#E5E5E5] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#3FAF7A]/30 focus:border-[#3FAF7A] resize-y min-h-[80px]"
                placeholder="Describe the product vision..."
                autoFocus
              />
              <div className="flex items-center gap-2">
                <button
                  onClick={handleSaveVision}
                  className="px-3 py-1.5 text-[12px] font-medium text-white bg-[#3FAF7A] rounded-xl hover:bg-[#25785A] transition-colors"
                >
                  Save
                </button>
                <button
                  onClick={() => { setEditingVision(false); setVisionDraft(data.vision || '') }}
                  className="px-3 py-1.5 text-[12px] font-medium text-[#666666] bg-white border border-[#E5E5E5] rounded-xl hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="group">
              {data.vision ? (
                <p className="text-[14px] text-[#666666] leading-relaxed">{data.vision}</p>
              ) : (
                <p className="text-[13px] text-[#999999] italic">No vision statement yet. Click to add one.</p>
              )}
              <button
                onClick={() => { setVisionDraft(data.vision || ''); setEditingVision(true) }}
                className="mt-2 inline-flex items-center gap-1 text-[12px] text-[#999999] hover:text-[#3FAF7A] transition-colors opacity-0 group-hover:opacity-100"
              >
                <Pencil className="w-3 h-3" />
                Edit
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Success Metrics */}
      <div>
        <SectionHeader
          title="Success Metrics"
          count={data.success_metrics.length}
          confirmedCount={confirmedMetrics}
          onConfirmAll={() => onConfirmAll('business_driver', data.success_metrics.map((m) => m.id))}
        />
        {data.success_metrics.length === 0 ? (
          <p className="text-[13px] text-[#999999] italic">No success metrics defined yet</p>
        ) : (
          <div className="space-y-3">
            {visibleMetrics.map((metric) => (
              <MetricCard
                key={metric.id}
                metric={metric}
                onConfirm={() => onConfirm('business_driver', metric.id)}
                onNeedsReview={() => onNeedsReview('business_driver', metric.id)}
                onStatusClick={onStatusClick ? () => onStatusClick('business_driver', metric.id, metric.description.slice(0, 60), metric.confirmation_status) : undefined}
                onDetailClick={() => setSelectedDriver({ id: metric.id, type: 'kpi', data: metric })}
              />
            ))}
            {data.success_metrics.length > SHOW_MAX_METRICS && !showAllMetrics && (
              <button
                onClick={() => setShowAllMetrics(true)}
                className="flex items-center gap-1.5 px-3 py-2 text-[12px] font-medium text-[#999999] hover:text-[#3FAF7A] transition-colors w-full justify-center"
              >
                <ChevronDown className="w-3.5 h-3.5" />
                Show all {data.success_metrics.length} metrics
              </button>
            )}
          </div>
        )}
      </div>

      {/* Detail Drawer */}
      {selectedDriver && (
        <BusinessDriverDetailDrawer
          driverId={selectedDriver.id}
          driverType={selectedDriver.type}
          projectId={projectId}
          initialData={selectedDriver.data}
          onClose={() => setSelectedDriver(null)}
          onConfirm={onConfirm}
          onNeedsReview={onNeedsReview}
        />
      )}
    </section>
  )
}
