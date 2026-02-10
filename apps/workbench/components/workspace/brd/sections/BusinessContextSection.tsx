'use client'

import { useState } from 'react'
import { Building2, AlertTriangle, Target, Eye, BarChart3, Pencil, AlertCircle, ChevronDown } from 'lucide-react'
import { SectionHeader } from '../components/SectionHeader'
import { CollapsibleCard } from '../components/CollapsibleCard'
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
}

const SHOW_MAX_PAINS = 8
const SHOW_MAX_GOALS = 8
const SHOW_MAX_METRICS = 5

export function BusinessContextSection({
  data,
  projectId,
  onConfirm,
  onNeedsReview,
  onConfirmAll,
  onUpdateVision,
  onUpdateBackground,
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
        <h2 className="text-lg font-semibold text-[#37352f] mb-3 flex items-center gap-2">
          <Building2 className="w-5 h-5 text-[rgba(55,53,47,0.45)]" />
          Background
        </h2>
        <div className="bg-white border border-[#e9e9e7] rounded-[3px] p-4">
          {editingBackground ? (
            <div className="space-y-3">
              <textarea
                value={backgroundDraft}
                onChange={(e) => setBackgroundDraft(e.target.value)}
                className="w-full p-3 text-[14px] text-[#37352f] border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-teal-200 focus:border-teal-300 resize-y min-h-[80px]"
                placeholder="Describe the company background..."
                autoFocus
              />
              <div className="flex items-center gap-2">
                <button
                  onClick={handleSaveBackground}
                  className="px-3 py-1.5 text-[12px] font-medium text-white bg-[#009b87] rounded-md hover:bg-[#008474] transition-colors"
                >
                  Save
                </button>
                <button
                  onClick={() => { setEditingBackground(false); setBackgroundDraft(data.background || '') }}
                  className="px-3 py-1.5 text-[12px] font-medium text-gray-600 bg-white border border-gray-200 rounded-md hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="group">
              {data.company_name && (
                <p className="text-[14px] font-medium text-[#37352f] mb-1">
                  {data.company_name}
                  {data.industry && (
                    <span className="text-[rgba(55,53,47,0.65)] font-normal"> &mdash; {data.industry}</span>
                  )}
                </p>
              )}
              {data.background ? (
                <p className="text-[14px] text-[rgba(55,53,47,0.65)] leading-relaxed">
                  {data.background}
                </p>
              ) : (
                <p className="text-[13px] text-[rgba(55,53,47,0.35)] italic">
                  No background description yet. Click to add one.
                </p>
              )}
              <button
                onClick={() => { setBackgroundDraft(data.background || ''); setEditingBackground(true) }}
                className="mt-2 inline-flex items-center gap-1 text-[12px] text-gray-400 hover:text-[#009b87] transition-colors opacity-0 group-hover:opacity-100"
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
          onConfirmAll={() =>
            onConfirmAll('business_driver', data.pain_points.map((p) => p.id))
          }
        />
        {data.pain_points.length === 0 ? (
          <p className="text-[13px] text-[rgba(55,53,47,0.45)] italic">No pain points identified yet</p>
        ) : (
          <div className="space-y-2">
            {visiblePains.map((pain) => (
              <CollapsibleCard
                key={pain.id}
                title={pain.description}
                icon={<AlertTriangle className="w-4 h-4 text-red-400" />}
                status={pain.confirmation_status}
                onConfirm={() => onConfirm('business_driver', pain.id)}
                onNeedsReview={() => onNeedsReview('business_driver', pain.id)}
                onDetailClick={() => setSelectedDriver({ id: pain.id, type: 'pain', data: pain })}
              >
                <div className="space-y-2 text-[13px] text-[rgba(55,53,47,0.65)]">
                  {pain.severity && (
                    <div><span className="font-medium text-[#37352f]">Severity:</span> {pain.severity}</div>
                  )}
                  {pain.business_impact && (
                    <div><span className="font-medium text-[#37352f]">Impact:</span> {pain.business_impact}</div>
                  )}
                  {pain.affected_users && (
                    <div><span className="font-medium text-[#37352f]">Affected Users:</span> {pain.affected_users}</div>
                  )}
                  {pain.current_workaround && (
                    <div><span className="font-medium text-[#37352f]">Current Workaround:</span> {pain.current_workaround}</div>
                  )}
                </div>
                {/* Persona chips */}
                {pain.associated_persona_names && pain.associated_persona_names.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {pain.associated_persona_names.map((name) => (
                      <span key={name} className="px-2 py-0.5 text-[11px] bg-indigo-50 text-indigo-700 rounded-full">
                        {name}
                      </span>
                    ))}
                  </div>
                )}
                <EvidenceBlock evidence={pain.evidence || []} />
              </CollapsibleCard>
            ))}
            {data.pain_points.length > SHOW_MAX_PAINS && !showAllPains && (
              <button
                onClick={() => setShowAllPains(true)}
                className="flex items-center gap-1.5 px-3 py-2 text-[12px] font-medium text-gray-500 hover:text-[#009b87] transition-colors w-full justify-center"
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
          onConfirmAll={() =>
            onConfirmAll('business_driver', data.goals.map((g) => g.id))
          }
        />
        {data.goals.length === 0 ? (
          <p className="text-[13px] text-[rgba(55,53,47,0.45)] italic">No business goals identified yet</p>
        ) : (
          <div className="space-y-2">
            {visibleGoals.map((goal) => (
              <CollapsibleCard
                key={goal.id}
                title={goal.description}
                icon={<Target className="w-4 h-4 text-blue-400" />}
                status={goal.confirmation_status}
                onConfirm={() => onConfirm('business_driver', goal.id)}
                onNeedsReview={() => onNeedsReview('business_driver', goal.id)}
                onDetailClick={() => setSelectedDriver({ id: goal.id, type: 'goal', data: goal })}
              >
                <div className="space-y-2 text-[13px] text-[rgba(55,53,47,0.65)]">
                  {goal.success_criteria && (
                    <div><span className="font-medium text-[#37352f]">Success Criteria:</span> {goal.success_criteria}</div>
                  )}
                  {goal.owner && (
                    <div><span className="font-medium text-[#37352f]">Owner:</span> {goal.owner}</div>
                  )}
                  {goal.goal_timeframe && (
                    <div><span className="font-medium text-[#37352f]">Timeframe:</span> {goal.goal_timeframe}</div>
                  )}
                </div>
                {/* Persona chips */}
                {goal.associated_persona_names && goal.associated_persona_names.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {goal.associated_persona_names.map((name) => (
                      <span key={name} className="px-2 py-0.5 text-[11px] bg-indigo-50 text-indigo-700 rounded-full">
                        {name}
                      </span>
                    ))}
                  </div>
                )}
                <EvidenceBlock evidence={goal.evidence || []} />
              </CollapsibleCard>
            ))}
            {data.goals.length > SHOW_MAX_GOALS && !showAllGoals && (
              <button
                onClick={() => setShowAllGoals(true)}
                className="flex items-center gap-1.5 px-3 py-2 text-[12px] font-medium text-gray-500 hover:text-[#009b87] transition-colors w-full justify-center"
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
        <h2 className="text-lg font-semibold text-[#37352f] mb-3 flex items-center gap-2">
          <Eye className="w-5 h-5 text-[rgba(55,53,47,0.45)]" />
          Vision
        </h2>
        <div className="bg-white border border-[#e9e9e7] rounded-[3px] p-4">
          {editingVision ? (
            <div className="space-y-3">
              <textarea
                value={visionDraft}
                onChange={(e) => setVisionDraft(e.target.value)}
                className="w-full p-3 text-[14px] text-[#37352f] border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-teal-200 focus:border-teal-300 resize-y min-h-[80px]"
                placeholder="Describe the product vision..."
                autoFocus
              />
              <div className="flex items-center gap-2">
                <button
                  onClick={handleSaveVision}
                  className="px-3 py-1.5 text-[12px] font-medium text-white bg-[#009b87] rounded-md hover:bg-[#008474] transition-colors"
                >
                  Save
                </button>
                <button
                  onClick={() => { setEditingVision(false); setVisionDraft(data.vision || '') }}
                  className="px-3 py-1.5 text-[12px] font-medium text-gray-600 bg-white border border-gray-200 rounded-md hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="group">
              {data.vision ? (
                <p className="text-[14px] text-[rgba(55,53,47,0.65)] leading-relaxed">{data.vision}</p>
              ) : (
                <p className="text-[13px] text-[rgba(55,53,47,0.35)] italic">No vision statement yet. Click to add one.</p>
              )}
              <button
                onClick={() => { setVisionDraft(data.vision || ''); setEditingVision(true) }}
                className="mt-2 inline-flex items-center gap-1 text-[12px] text-gray-400 hover:text-[#009b87] transition-colors opacity-0 group-hover:opacity-100"
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
          onConfirmAll={() =>
            onConfirmAll('business_driver', data.success_metrics.map((m) => m.id))
          }
        />
        {data.success_metrics.length === 0 ? (
          <p className="text-[13px] text-[rgba(55,53,47,0.45)] italic">No success metrics defined yet</p>
        ) : (
          <div className="space-y-2">
            {visibleMetrics.map((metric) => (
              <CollapsibleCard
                key={metric.id}
                title={metric.description}
                icon={<BarChart3 className="w-4 h-4 text-purple-400" />}
                status={metric.confirmation_status}
                onConfirm={() => onConfirm('business_driver', metric.id)}
                onNeedsReview={() => onNeedsReview('business_driver', metric.id)}
                onDetailClick={() => setSelectedDriver({ id: metric.id, type: 'kpi', data: metric })}
              >
                <div className="space-y-2 text-[13px] text-[rgba(55,53,47,0.65)]">
                  {metric.baseline_value && (
                    <div><span className="font-medium text-[#37352f]">Baseline:</span> {metric.baseline_value}</div>
                  )}
                  {metric.target_value && (
                    <div><span className="font-medium text-[#37352f]">Target:</span> {metric.target_value}</div>
                  )}
                  {metric.measurement_method && (
                    <div><span className="font-medium text-[#37352f]">Measurement:</span> {metric.measurement_method}</div>
                  )}
                </div>
                {/* Missing field indicator */}
                {(metric.missing_field_count ?? 0) > 0 && (
                  <div className="flex items-center gap-1 text-[11px] text-amber-600 mt-2">
                    <AlertCircle className="w-3 h-3" />
                    {metric.missing_field_count} field(s) need data
                  </div>
                )}
                <EvidenceBlock evidence={metric.evidence || []} />
              </CollapsibleCard>
            ))}
            {data.success_metrics.length > SHOW_MAX_METRICS && !showAllMetrics && (
              <button
                onClick={() => setShowAllMetrics(true)}
                className="flex items-center gap-1.5 px-3 py-2 text-[12px] font-medium text-gray-500 hover:text-[#009b87] transition-colors w-full justify-center"
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
