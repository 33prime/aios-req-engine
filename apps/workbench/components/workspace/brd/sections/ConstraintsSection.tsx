'use client'

import { useState, useMemo } from 'react'
import {
  Shield,
  ChevronRight,
  DollarSign,
  Clock,
  Scale,
  Building2,
  Server,
  Target,
  Sparkles,
  Check,
  X,
} from 'lucide-react'
import { SectionHeader } from '../components/SectionHeader'
import { BRDStatusBadge } from '../components/StatusBadge'
import { ConfirmActions } from '../components/ConfirmActions'
import { EvidenceBlock } from '../components/EvidenceBlock'
import type { ConstraintItem, SectionScore } from '@/types/workspace'

interface ConstraintsSectionProps {
  constraints: ConstraintItem[]
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
  onConfirmAll: (entityType: string, ids: string[]) => void
  onStatusClick?: (entityType: string, entityId: string, entityName: string, status?: string | null) => void
  onInferConstraints?: () => Promise<void>
  sectionScore?: SectionScore | null
}

// 6-category type config with icons
const TYPE_CONFIG: Record<string, { icon: typeof DollarSign; label: string }> = {
  budget: { icon: DollarSign, label: 'Budget' },
  timeline: { icon: Clock, label: 'Timeline' },
  regulatory: { icon: Scale, label: 'Regulatory' },
  organizational: { icon: Building2, label: 'Organizational' },
  technical: { icon: Server, label: 'Technical' },
  strategic: { icon: Target, label: 'Strategic' },
}

// Brand-appropriate severity indicators
const SEVERITY_CONFIG: Record<string, { label: string; bg: string; text: string }> = {
  critical: { label: 'Critical', bg: 'bg-[#0A1E2F]', text: 'text-white' },
  high: { label: 'High', bg: 'bg-[#25785A]', text: 'text-white' },
  medium: { label: 'Medium', bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]' },
  low: { label: 'Low', bg: 'bg-[#F0F0F0]', text: 'text-[#666666]' },
}

function ConstraintCard({
  constraint,
  onConfirm,
  onNeedsReview,
  onStatusClick,
}: {
  constraint: ConstraintItem
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
  onStatusClick?: (entityType: string, entityId: string, entityName: string, status?: string | null) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const [hasBeenExpanded, setHasBeenExpanded] = useState(false)
  const sev = SEVERITY_CONFIG[constraint.severity] || SEVERITY_CONFIG.medium
  const typeConfig = TYPE_CONFIG[constraint.constraint_type] || TYPE_CONFIG.technical
  const TypeIcon = typeConfig.icon
  const isAiInferred = constraint.source === 'ai_inferred'

  return (
    <div className={`bg-white rounded-2xl shadow-md overflow-hidden ${
      isAiInferred
        ? 'border-2 border-dashed border-[#3FAF7A]/40'
        : 'border border-[#E5E5E5]'
    }`}>
      {/* Header row */}
      <button
        onClick={() => { const next = !expanded; setExpanded(next); if (next && !hasBeenExpanded) setHasBeenExpanded(true) }}
        className="w-full flex items-center gap-3 px-5 py-3.5 text-left hover:bg-gray-50/50 transition-colors"
      >
        <ChevronRight
          className={`w-4 h-4 text-[#999999] shrink-0 transition-transform duration-200 ${expanded ? 'rotate-90' : ''}`}
        />
        <TypeIcon className="w-4 h-4 text-[#25785A] shrink-0" />
        <span className="text-[14px] font-semibold text-[#333333] truncate flex-1">{constraint.title}</span>
        {isAiInferred && (
          <span className="inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-[#E8F5E9] text-[#3FAF7A] shrink-0">
            <Sparkles className="w-2.5 h-2.5" />
            AI
          </span>
        )}
        {constraint.confidence != null && isAiInferred && (
          <span className="text-[10px] text-[#999999] shrink-0">
            {Math.round(constraint.confidence * 100)}%
          </span>
        )}
        <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full shrink-0 ${sev.bg} ${sev.text}`}>
          {sev.label}
        </span>
        <span className="shrink-0" onClick={(e) => e.stopPropagation()}>
          <BRDStatusBadge
            status={constraint.confirmation_status}
            onClick={onStatusClick ? () => onStatusClick('constraint', constraint.id, constraint.title, constraint.confirmation_status) : undefined}
          />
        </span>
      </button>

      {/* Expanded body */}
      {hasBeenExpanded && (
        <div className={`overflow-hidden transition-all duration-200 ${expanded ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'}`}>
          <div className="px-5 pb-5 pt-1 border-t border-[#E5E5E5]">
            {/* Description */}
            {constraint.description && (
              <p className="text-[13px] text-[#666666] leading-relaxed mb-3">{constraint.description}</p>
            )}

            {/* Impact */}
            {constraint.impact_description && (
              <div className="bg-[#F9F9F9] rounded-lg p-3 mb-3">
                <p className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-1">Impact if Ignored</p>
                <p className="text-[12px] text-[#666666]">{constraint.impact_description}</p>
              </div>
            )}

            {/* Evidence */}
            <EvidenceBlock evidence={constraint.evidence || []} maxItems={3} />

            {/* Actions */}
            <div className="mt-3 pt-3 border-t border-[#E5E5E5]">
              <ConfirmActions
                status={constraint.confirmation_status}
                onConfirm={() => onConfirm('constraint', constraint.id)}
                onNeedsReview={() => onNeedsReview('constraint', constraint.id)}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export function ConstraintsSection({
  constraints,
  onConfirm,
  onNeedsReview,
  onConfirmAll,
  onStatusClick,
  onInferConstraints,
  sectionScore,
}: ConstraintsSectionProps) {
  const [inferring, setInferring] = useState(false)

  const confirmedCount = constraints.filter(
    (c) => c.confirmation_status === 'confirmed_consultant' || c.confirmation_status === 'confirmed_client'
  ).length

  // Group constraints by type
  const grouped = useMemo(() => {
    const groups: Record<string, ConstraintItem[]> = {}
    const order = ['budget', 'timeline', 'regulatory', 'organizational', 'technical', 'strategic']
    for (const type of order) {
      groups[type] = []
    }
    for (const c of constraints) {
      const type = c.constraint_type || 'technical'
      if (!groups[type]) groups[type] = []
      groups[type].push(c)
    }
    return groups
  }, [constraints])

  const nonEmptyGroups = Object.entries(grouped).filter(([, items]) => items.length > 0)

  const handleInfer = async () => {
    if (!onInferConstraints) return
    setInferring(true)
    try {
      await onInferConstraints()
    } finally {
      setInferring(false)
    }
  }

  return (
    <section id="brd-section-constraints">
      <div className="flex items-center justify-between mb-4">
        <SectionHeader
          title="Constraints"
          count={constraints.length}
          confirmedCount={confirmedCount}
          onConfirmAll={() => onConfirmAll('constraint', constraints.map((c) => c.id))}
          sectionScore={sectionScore}
        />
        {onInferConstraints && (
          <button
            onClick={handleInfer}
            disabled={inferring}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-[#3FAF7A] bg-[#E8F5E9] rounded-xl hover:bg-[#d4edda] transition-colors disabled:opacity-50"
          >
            <Sparkles className={`w-3.5 h-3.5 ${inferring ? 'animate-spin' : ''}`} />
            {inferring ? 'Analyzing...' : 'Suggest Constraints'}
          </button>
        )}
      </div>
      {constraints.length === 0 ? (
        <div className="text-center py-6">
          <Shield className="w-6 h-6 text-[#999999] mx-auto mb-2" />
          <p className="text-[13px] text-[#999999]">No constraints identified yet</p>
          {onInferConstraints && (
            <button
              onClick={handleInfer}
              disabled={inferring}
              className="mt-3 inline-flex items-center gap-1.5 px-4 py-2 text-[12px] font-medium text-white bg-[#3FAF7A] rounded-xl hover:bg-[#25785A] transition-colors disabled:opacity-50"
            >
              <Sparkles className="w-3.5 h-3.5" />
              {inferring ? 'Analyzing...' : 'Suggest Constraints with AI'}
            </button>
          )}
        </div>
      ) : nonEmptyGroups.length > 1 ? (
        // Grouped view: show category headers
        <div className="space-y-6">
          {nonEmptyGroups.map(([type, items]) => {
            const config = TYPE_CONFIG[type] || TYPE_CONFIG.technical
            const Icon = config.icon
            return (
              <div key={type}>
                <div className="flex items-center gap-2 mb-2">
                  <Icon className="w-4 h-4 text-[#999999]" />
                  <h3 className="text-[12px] font-semibold text-[#666666] uppercase tracking-wide">
                    {config.label}
                  </h3>
                  <span className="text-[11px] text-[#999999]">({items.length})</span>
                </div>
                <div className="space-y-2">
                  {items.map((constraint) => (
                    <ConstraintCard
                      key={constraint.id}
                      constraint={constraint}
                      onConfirm={onConfirm}
                      onNeedsReview={onNeedsReview}
                      onStatusClick={onStatusClick}
                    />
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        // Flat view for single category
        <div className="space-y-2">
          {constraints.map((constraint) => (
            <ConstraintCard
              key={constraint.id}
              constraint={constraint}
              onConfirm={onConfirm}
              onNeedsReview={onNeedsReview}
              onStatusClick={onStatusClick}
            />
          ))}
        </div>
      )}
    </section>
  )
}
