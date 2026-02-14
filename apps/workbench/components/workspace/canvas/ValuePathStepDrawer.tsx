'use client'

import { useState, useEffect } from 'react'
import {
  X,
  Route,
  User,
  TrendingUp,
  CheckCircle,
  Zap,
  Database,
  Sparkles,
  ArrowDownRight,
  ArrowUpRight,
  Puzzle,
  Cpu,
  Target,
} from 'lucide-react'
import { getValuePathStepDetail } from '@/lib/api'
import type {
  ValuePathStepDetail,
  StepActor,
  StepDataOperation,
  StepLinkedFeature,
  RecommendedComponent,
  StepBusinessLogic,
} from '@/types/workspace'

interface ValuePathStepDrawerProps {
  projectId: string
  stepIndex: number
  stepTitle: string
  onClose: () => void
}

type TabId = 'actors' | 'system_flow' | 'business_calcs' | 'components'

const TABS: { id: TabId; label: string }[] = [
  { id: 'actors', label: 'Actors' },
  { id: 'system_flow', label: 'System Flow' },
  { id: 'business_calcs', label: 'Business Calculations' },
  { id: 'components', label: 'Components' },
]

export function ValuePathStepDrawer({
  projectId,
  stepIndex,
  stepTitle,
  onClose,
}: ValuePathStepDrawerProps) {
  const [activeTab, setActiveTab] = useState<TabId>('actors')
  const [detail, setDetail] = useState<ValuePathStepDetail | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getValuePathStepDetail(projectId, stepIndex)
      .then((data) => {
        if (!cancelled) setDetail(data)
      })
      .catch((err) => {
        console.error('Failed to load value path step detail:', err)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [projectId, stepIndex])

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 z-40"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-[560px] max-w-full bg-white shadow-xl z-50 flex flex-col animate-slide-in-right">
        {/* Header */}
        <div className="flex-shrink-0 border-b border-[#E5E5E5] px-6 py-4">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3 min-w-0 flex-1">
              <div className="w-8 h-8 rounded-full bg-[#0A1E2F] flex items-center justify-center flex-shrink-0 mt-0.5">
                <Route className="w-4 h-4 text-white" />
              </div>
              <div className="min-w-0">
                <p className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-1">
                  VALUE PATH STEP
                </p>
                <h2 className="text-[15px] font-semibold text-[#333333] line-clamp-2 leading-snug">
                  {stepTitle}
                </h2>
                {detail && (
                  <div className="flex items-center gap-2 mt-1.5">
                    <AutomationBadge level={detail.automation_level} />
                    {detail.time_minutes != null && (
                      <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[#F0F0F0] text-[#666666]">
                        {detail.time_minutes}min
                      </span>
                    )}
                    <RoiImpactDot impact={detail.roi_impact} />
                  </div>
                )}
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-[#999999] hover:text-[#666666] hover:bg-gray-100 transition-colors flex-shrink-0"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Tabs */}
          <div className="flex gap-0 mt-4 -mb-4 border-b-0">
            {TABS.map((tab) => {
              const isActive = activeTab === tab.id
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-3 py-2 text-[12px] font-medium border-b-2 transition-colors ${
                    isActive
                      ? 'border-[#3FAF7A] text-[#25785A]'
                      : 'border-transparent text-[#999999] hover:text-[#666666]'
                  }`}
                >
                  {tab.label}
                </button>
              )
            })}
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {loading && !detail ? (
            <div className="flex items-center justify-center py-16">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[#3FAF7A]" />
            </div>
          ) : detail ? (
            <>
              {activeTab === 'actors' && <ActorsTab detail={detail} />}
              {activeTab === 'system_flow' && <SystemFlowTab detail={detail} />}
              {activeTab === 'business_calcs' && <BusinessCalculationsTab logic={detail.business_logic} />}
              {activeTab === 'components' && <ComponentsTab detail={detail} />}
            </>
          ) : (
            <div className="text-center py-8">
              <p className="text-[13px] text-[#666666]">Failed to load step details.</p>
            </div>
          )}
        </div>
      </div>
    </>
  )
}

// ============================================================================
// Header Helpers
// ============================================================================

function AutomationBadge({ level }: { level: string }) {
  const config: Record<string, { bg: string; text: string; label: string }> = {
    manual: { bg: 'bg-[#F0F0F0]', text: 'text-[#666666]', label: 'Manual' },
    semi_automated: { bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]', label: 'Semi-Auto' },
    fully_automated: { bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]', label: 'Fully Auto' },
  }
  const c = config[level] || config.manual
  return (
    <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${c.bg} ${c.text}`}>
      {c.label}
    </span>
  )
}

function RoiImpactDot({ impact }: { impact: string }) {
  const config: Record<string, { color: string; label: string }> = {
    high: { color: 'bg-[#3FAF7A]', label: 'High ROI' },
    medium: { color: 'bg-[#999999]', label: 'Medium ROI' },
    low: { color: 'bg-[#E5E5E5]', label: 'Low ROI' },
  }
  const c = config[impact] || config.low
  return (
    <span className="flex items-center gap-1">
      <span className={`w-2 h-2 rounded-full ${c.color}`} />
      <span className="text-[10px] text-[#999999]">{c.label}</span>
    </span>
  )
}

// ============================================================================
// Tab 1: Actors & Context
// ============================================================================

function ActorsTab({ detail }: { detail: ValuePathStepDetail }) {
  return (
    <div className="space-y-4">
      {/* Combined Value callout */}
      {detail.combined_value && (
        <div className="bg-[#E8F5E9] border border-[#3FAF7A]/20 rounded-xl p-4">
          <p className="text-[13px] text-[#333333] leading-relaxed">
            {detail.combined_value}
          </p>
        </div>
      )}

      {/* Actors list */}
      {detail.actors.length > 0 ? (
        <div className="space-y-3">
          {detail.actors.map((actor) => (
            <ActorCard key={actor.persona_id} actor={actor} />
          ))}
        </div>
      ) : (
        <EmptyState
          icon={<User className="w-8 h-8 text-[#E5E5E5]" />}
          title="No actors mapped"
          description="Actors will appear here once personas are linked to this value path step."
        />
      )}
    </div>
  )
}

function ActorCard({ actor }: { actor: StepActor }) {
  return (
    <div className="bg-white border border-[#E5E5E5] rounded-xl p-4">
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-full bg-[#F4F4F4] flex items-center justify-center flex-shrink-0">
          <User className="w-4 h-4 text-[#666666]" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-[14px] font-semibold text-[#333333]">
              {actor.persona_name}
            </span>
            <span
              className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${
                actor.is_primary
                  ? 'bg-[#E8F5E9] text-[#25785A]'
                  : 'bg-[#F0F0F0] text-[#666666]'
              }`}
            >
              {actor.is_primary ? 'Primary' : 'Secondary'}
            </span>
          </div>
          {actor.role && (
            <p className="text-[13px] text-[#666666] mt-0.5">{actor.role}</p>
          )}
          {actor.pain_at_step && (
            <p className="text-[12px] text-[#999999] italic mt-2">
              Pain: {actor.pain_at_step}
            </p>
          )}
          {actor.goal_at_step && (
            <p className="text-[12px] text-[#25785A] italic mt-1">
              Goal: {actor.goal_at_step}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// Tab 2: System Flow
// ============================================================================

function SystemFlowTab({ detail }: { detail: ValuePathStepDetail }) {
  return (
    <div className="space-y-6">
      {/* Data Operations */}
      <div>
        <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-3">
          Data Operations
        </h4>
        {detail.data_operations.length > 0 ? (
          <div className="border border-[#E5E5E5] rounded-xl overflow-hidden bg-white">
            {detail.data_operations.map((op, i) => (
              <DataOperationRow key={`${op.entity_id}-${i}`} operation={op} />
            ))}
          </div>
        ) : (
          <EmptyState
            icon={<Cpu className="w-8 h-8 text-[#E5E5E5]" />}
            title="No data operations mapped"
            description="No data operations mapped to this step."
          />
        )}
      </div>

      {/* Dependencies */}
      <div>
        <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-3">
          Dependencies
        </h4>
        <div className="space-y-4">
          {/* Input Dependencies */}
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <ArrowDownRight className="w-3.5 h-3.5 text-[#999999]" />
              <span className="text-[12px] font-medium text-[#666666]">
                Input Dependencies
              </span>
            </div>
            {detail.input_dependencies.length > 0 ? (
              <ul className="space-y-1.5 pl-5">
                {detail.input_dependencies.map((dep, i) => (
                  <li
                    key={i}
                    className="text-[13px] text-[#333333] leading-relaxed list-disc"
                  >
                    {dep}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-[12px] text-[#999999] italic pl-5">
                No input dependencies identified.
              </p>
            )}
          </div>

          {/* Output Effects */}
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <ArrowUpRight className="w-3.5 h-3.5 text-[#999999]" />
              <span className="text-[12px] font-medium text-[#666666]">
                Output Effects
              </span>
            </div>
            {detail.output_effects.length > 0 ? (
              <ul className="space-y-1.5 pl-5">
                {detail.output_effects.map((effect, i) => (
                  <li
                    key={i}
                    className="text-[13px] text-[#333333] leading-relaxed list-disc"
                  >
                    {effect}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-[12px] text-[#999999] italic pl-5">
                No output effects identified.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function DataOperationRow({ operation }: { operation: StepDataOperation }) {
  return (
    <div className="px-4 py-3 border-b border-[#F0F0F0] last:border-0">
      <div className="flex items-center gap-2 mb-1">
        <OperationBadge operation={operation.operation} />
        <span className="text-[13px] font-medium text-[#333333]">
          {operation.entity_name}
        </span>
        <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[#F0F0F0] text-[#666666]">
          {operation.entity_category}
        </span>
      </div>
      {operation.description && (
        <p className="text-[12px] text-[#666666] leading-relaxed mt-1 pl-7">
          {operation.description}
        </p>
      )}
    </div>
  )
}

function OperationBadge({ operation }: { operation: string }) {
  const config: Record<string, { bg: string; text: string }> = {
    CREATE: { bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]' },
    READ: { bg: 'bg-[#F0F0F0]', text: 'text-[#666666]' },
    UPDATE: { bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]' },
    DELETE: { bg: 'bg-[#0A1E2F]', text: 'text-white' },
  }
  const upper = operation.toUpperCase()
  const c = config[upper] || config.READ
  return (
    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${c.bg} ${c.text}`}>
      {upper}
    </span>
  )
}

// ============================================================================
// Tab 3: Business Calculations
// ============================================================================

function BusinessCalculationsTab({ logic }: { logic: StepBusinessLogic }) {
  const hasContent =
    logic.decision_points.length > 0 ||
    logic.validation_rules.length > 0 ||
    logic.edge_cases.length > 0 ||
    logic.success_criteria ||
    logic.error_states.length > 0

  if (!hasContent) {
    return (
      <EmptyState
        icon={<TrendingUp className="w-8 h-8 text-[#E5E5E5]" />}
        title="No business calculations yet"
        description="Calculations will appear once workflows have time and automation data."
      />
    )
  }

  return (
    <div className="space-y-5">
      {/* ROI Impact — from decision_points (time savings, volume impact) */}
      {logic.decision_points.length > 0 && (
        <div>
          <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2 flex items-center gap-1.5">
            <TrendingUp className="w-4 h-4 text-[#3FAF7A]" />
            ROI Impact
          </h4>
          <div className="bg-[#E8F5E9] border border-[#3FAF7A]/20 rounded-xl overflow-hidden">
            {logic.decision_points.map((point, i) => (
              <div
                key={i}
                className={`px-4 py-3 flex items-start gap-2.5 ${
                  i > 0 ? 'border-t border-[#3FAF7A]/10' : ''
                }`}
              >
                <TrendingUp className="w-3.5 h-3.5 text-[#25785A] flex-shrink-0 mt-0.5" />
                <p className="text-[13px] text-[#333333] leading-relaxed">{point}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Before / After — from validation_rules */}
      {logic.validation_rules.length > 0 && (
        <div>
          <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2 flex items-center gap-1.5">
            <ArrowDownRight className="w-4 h-4 text-[#666666]" />
            Before / After
          </h4>
          <div className="bg-white border border-[#E5E5E5] rounded-xl overflow-hidden">
            {logic.validation_rules.map((rule, i) => {
              const isBefore = rule.toLowerCase().startsWith('before:')
              return (
                <div
                  key={i}
                  className={`px-4 py-3 flex items-start gap-2.5 ${
                    i > 0 ? 'border-t border-[#F0F0F0]' : ''
                  }`}
                >
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded flex-shrink-0 mt-0.5 ${
                    isBefore
                      ? 'bg-[#F0F0F0] text-[#666666]'
                      : 'bg-[#E8F5E9] text-[#25785A]'
                  }`}>
                    {isBefore ? 'BEFORE' : 'AFTER'}
                  </span>
                  <p className="text-[13px] text-[#333333] leading-relaxed">
                    {rule.replace(/^(before|after):\s*/i, '')}
                  </p>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Automation Impact — from edge_cases */}
      {logic.edge_cases.length > 0 && (
        <div>
          <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2 flex items-center gap-1.5">
            <Zap className="w-4 h-4 text-[#666666]" />
            Automation Impact
          </h4>
          <div className="space-y-2">
            {logic.edge_cases.map((item, i) => (
              <div key={i} className="bg-white border border-[#E5E5E5] rounded-xl px-4 py-3">
                <div className="flex items-start gap-2">
                  <Zap className="w-3.5 h-3.5 text-[#999999] flex-shrink-0 mt-0.5" />
                  <p className="text-[13px] text-[#333333] leading-relaxed">{item}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Data Operations Summary — from error_states (repurposed) */}
      {logic.error_states.length > 0 && (
        <div>
          <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2 flex items-center gap-1.5">
            <Database className="w-4 h-4 text-[#666666]" />
            Data Operations
          </h4>
          <div className="space-y-2">
            {logic.error_states.map((item, i) => (
              <div key={i} className="bg-white border border-[#E5E5E5] rounded-xl px-4 py-3">
                <div className="flex items-start gap-2">
                  <Database className="w-3.5 h-3.5 text-[#999999] flex-shrink-0 mt-0.5" />
                  <p className="text-[13px] text-[#666666] leading-relaxed">{item}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Success Criteria */}
      {logic.success_criteria && (
        <div>
          <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2 flex items-center gap-1.5">
            <Target className="w-4 h-4 text-[#3FAF7A]" />
            Success Criteria
          </h4>
          <div className="bg-[#E8F5E9] border border-[#3FAF7A]/20 rounded-xl p-4">
            <div className="flex items-start gap-2">
              <CheckCircle className="w-4 h-4 text-[#3FAF7A] flex-shrink-0 mt-0.5" />
              <p className="text-[13px] text-[#333333] leading-relaxed">
                {logic.success_criteria}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Tab 4: Components & Features
// ============================================================================

function ComponentsTab({ detail }: { detail: ValuePathStepDetail }) {
  return (
    <div className="space-y-6">
      {/* Recommended Components */}
      <div>
        <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-3">
          Recommended Components
        </h4>
        {detail.recommended_components.length > 0 ? (
          <div className="space-y-3">
            {detail.recommended_components.map((comp, i) => (
              <RecommendedComponentCard key={i} component={comp} />
            ))}
          </div>
        ) : (
          <p className="text-[12px] text-[#999999] italic">
            No component recommendations yet.
          </p>
        )}
      </div>

      {/* Linked Features */}
      <div>
        <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-3 flex items-center gap-1.5">
          <Puzzle className="w-3.5 h-3.5" />
          Linked Features
          {detail.linked_features.length > 0 && (
            <span className="text-[10px] bg-[#F0F0F0] text-[#666666] px-1.5 py-0.5 rounded-full ml-1">
              {detail.linked_features.length}
            </span>
          )}
        </h4>
        {detail.linked_features.length > 0 ? (
          <div className="border border-[#E5E5E5] rounded-xl overflow-hidden bg-white">
            {detail.linked_features.map((feature) => (
              <LinkedFeatureRow key={feature.feature_id} feature={feature} />
            ))}
          </div>
        ) : (
          <p className="text-[12px] text-[#999999] italic">
            No features linked to this step.
          </p>
        )}
      </div>

      {/* AI Suggestions */}
      {detail.ai_suggestions.length > 0 && (
        <div>
          <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-3 flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-[#3FAF7A]" />
            AI Suggestions
          </h4>
          <div className="border border-[#3FAF7A]/20 rounded-xl overflow-hidden bg-[#E8F5E9]/30">
            <div className="divide-y divide-[#3FAF7A]/10">
              {detail.ai_suggestions.map((suggestion, i) => (
                <div key={i} className="px-4 py-3 flex items-start gap-2">
                  <Sparkles className="w-3.5 h-3.5 text-[#3FAF7A] flex-shrink-0 mt-0.5" />
                  <p className="text-[13px] text-[#333333] leading-relaxed">
                    {suggestion}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Effort Level */}
      <div>
        <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-3">
          Effort Level
        </h4>
        <EffortIndicator level={detail.effort_level} />
      </div>
    </div>
  )
}

function RecommendedComponentCard({ component }: { component: RecommendedComponent }) {
  const priorityConfig: Record<string, { bg: string; text: string }> = {
    must_have: { bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]' },
    nice_to_have: { bg: 'bg-[#F0F0F0]', text: 'text-[#666666]' },
  }
  const pConfig = priorityConfig[component.priority] || priorityConfig.nice_to_have

  return (
    <div className="bg-white border border-[#E5E5E5] rounded-xl p-4">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-[14px] font-semibold text-[#333333]">
          {component.name}
        </span>
        <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${pConfig.bg} ${pConfig.text}`}>
          {component.priority.replace('_', ' ')}
        </span>
      </div>
      <p className="text-[13px] text-[#333333] leading-relaxed">
        {component.description}
      </p>
      {component.rationale && (
        <p className="text-[12px] text-[#999999] italic mt-2">
          {component.rationale}
        </p>
      )}
    </div>
  )
}

function LinkedFeatureRow({ feature }: { feature: StepLinkedFeature }) {
  const isConfirmed =
    feature.confirmation_status === 'confirmed_consultant' ||
    feature.confirmation_status === 'confirmed_client'

  const priorityConfig: Record<string, { bg: string; text: string }> = {
    must_have: { bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]' },
    should_have: { bg: 'bg-[#F0F0F0]', text: 'text-[#666666]' },
    could_have: { bg: 'bg-[#F0F0F0]', text: 'text-[#999999]' },
    out_of_scope: { bg: 'bg-[#F0F0F0]', text: 'text-[#999999]' },
  }

  return (
    <div className="px-4 py-3 border-b border-[#F0F0F0] last:border-0 flex items-center gap-2">
      <span
        className={`w-2 h-2 rounded-full flex-shrink-0 ${
          isConfirmed ? 'bg-[#3FAF7A]' : 'bg-[#E5E5E5]'
        }`}
      />
      <span className="text-[13px] font-medium text-[#333333] truncate flex-1">
        {feature.feature_name}
      </span>
      {feature.category && (
        <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[#F0F0F0] text-[#666666] flex-shrink-0">
          {feature.category}
        </span>
      )}
      {feature.priority_group && (
        <span
          className={`text-[10px] font-medium px-1.5 py-0.5 rounded flex-shrink-0 ${
            (priorityConfig[feature.priority_group] || priorityConfig.could_have).bg
          } ${(priorityConfig[feature.priority_group] || priorityConfig.could_have).text}`}
        >
          {feature.priority_group.replace('_', ' ')}
        </span>
      )}
    </div>
  )
}

function EffortIndicator({ level }: { level: string }) {
  const normalized = level.toLowerCase()
  const levels: { key: string; label: string }[] = [
    { key: 'light', label: 'Light' },
    { key: 'medium', label: 'Medium' },
    { key: 'heavy', label: 'Heavy' },
  ]

  const activeIndex =
    normalized === 'light' ? 0 : normalized === 'medium' ? 1 : normalized === 'heavy' ? 2 : -1

  return (
    <div className="flex items-center gap-4 bg-[#F9F9F9] border border-[#E5E5E5] rounded-xl px-4 py-3">
      <div className="flex items-center gap-2">
        {levels.map((l, i) => (
          <div key={l.key} className="flex flex-col items-center gap-1">
            <span
              className={`w-3.5 h-3.5 rounded-full ${
                i <= activeIndex ? 'bg-[#3FAF7A]' : 'bg-[#E5E5E5]'
              }`}
            />
            <span
              className={`text-[10px] ${
                i === activeIndex ? 'font-semibold text-[#333333]' : 'text-[#999999]'
              }`}
            >
              {l.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ============================================================================
// Shared
// ============================================================================

function EmptyState({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode
  title: string
  description: string
}) {
  return (
    <div className="text-center py-8">
      <div className="mx-auto mb-3">{icon}</div>
      <p className="text-[13px] text-[#666666] mb-1">{title}</p>
      <p className="text-[12px] text-[#999999]">{description}</p>
    </div>
  )
}
