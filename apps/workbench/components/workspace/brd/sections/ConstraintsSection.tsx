'use client'

import { useState } from 'react'
import { Shield, ChevronRight, AlertTriangle } from 'lucide-react'
import { SectionHeader } from '../components/SectionHeader'
import { BRDStatusBadge } from '../components/StatusBadge'
import { ConfirmActions } from '../components/ConfirmActions'
import type { ConstraintItem } from '@/types/workspace'

interface ConstraintsSectionProps {
  constraints: ConstraintItem[]
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
  onConfirmAll: (entityType: string, ids: string[]) => void
  onStatusClick?: (entityType: string, entityId: string, entityName: string, status?: string | null) => void
}

// Brand-appropriate severity indicators — no red/orange/yellow
const SEVERITY_CONFIG: Record<string, { label: string; bg: string; text: string; dot: string }> = {
  critical: { label: 'Critical', bg: 'bg-[#0A1E2F]', text: 'text-white', dot: '#0A1E2F' },
  high: { label: 'High', bg: 'bg-[#25785A]', text: 'text-white', dot: '#25785A' },
  medium: { label: 'Medium', bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]', dot: '#3FAF7A' },
  low: { label: 'Low', bg: 'bg-[#F0F0F0]', text: 'text-[#666666]', dot: '#999999' },
}

function ConstraintAccordionCard({
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
  const sev = SEVERITY_CONFIG[constraint.severity] || SEVERITY_CONFIG.medium

  return (
    <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] overflow-hidden">
      {/* Header row */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-gray-50/50 transition-colors"
      >
        <ChevronRight
          className={`w-4 h-4 text-[#999999] shrink-0 transition-transform duration-200 ${expanded ? 'rotate-90' : ''}`}
        />
        <Shield className="w-4 h-4 text-[#25785A] shrink-0" />
        <span className="text-[14px] font-semibold text-[#333333] truncate">{constraint.title}</span>
        {constraint.constraint_type && (
          <span className="text-[12px] text-[#999999] shrink-0">({constraint.constraint_type})</span>
        )}
        <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full shrink-0 ${sev.bg} ${sev.text}`}>
          {sev.label}
        </span>
        <span onClick={(e) => e.stopPropagation()}>
          <BRDStatusBadge
            status={constraint.confirmation_status}
            onClick={onStatusClick ? () => onStatusClick('constraint', constraint.id, constraint.title, constraint.confirmation_status) : undefined}
          />
        </span>
      </button>

      {/* Expanded body */}
      <div className={`overflow-hidden transition-all duration-200 ${expanded ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'}`}>
        <div className="px-5 pb-5 pt-1">
          {/* Description */}
          {constraint.description && (
            <p className="text-[13px] text-[#666666] leading-relaxed mb-4">{constraint.description}</p>
          )}

          {/* Constraint metadata */}
          <div className="flex gap-6">
            <div className="flex-1 min-w-0">
              <div className="px-3 py-1.5 rounded-lg mb-3 bg-[#E8F5E9] text-[#25785A]">
                <span className="text-[11px] font-semibold uppercase tracking-wider">Details</span>
              </div>
              <ul className="space-y-2">
                <li className="flex items-start gap-2 text-[13px] text-[#666666]">
                  <span className="text-[#3FAF7A] mt-0.5 shrink-0">&#8226;</span>
                  <span>Severity: <span className="font-medium text-[#333333]">{sev.label}</span></span>
                </li>
                {constraint.constraint_type && (
                  <li className="flex items-start gap-2 text-[13px] text-[#666666]">
                    <span className="text-[#3FAF7A] mt-0.5 shrink-0">&#8226;</span>
                    <span>Type: <span className="font-medium text-[#333333]">{constraint.constraint_type}</span></span>
                  </li>
                )}
              </ul>
            </div>

            {/* Evidence */}
            {constraint.evidence && constraint.evidence.length > 0 && (
              <div className="flex-1 min-w-0">
                <div className="px-3 py-1.5 rounded-lg mb-3 bg-[#F0F0F0] text-[#666666]">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">Evidence</span>
                </div>
                <ul className="space-y-2">
                  {constraint.evidence.slice(0, 3).map((ev, i) => (
                    <li key={i} className="flex items-start gap-2 text-[13px] text-[#666666]">
                      <span className="text-[#999999] mt-0.5 shrink-0">&#8226;</span>
                      <span className="line-clamp-2">{ev.rationale || ev.excerpt || 'Source evidence'}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="mt-4 pt-3 border-t border-[#E5E5E5]">
            <ConfirmActions
              status={constraint.confirmation_status}
              onConfirm={() => onConfirm('constraint', constraint.id)}
              onNeedsReview={() => onNeedsReview('constraint', constraint.id)}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

export function ConstraintsSection({ constraints, onConfirm, onNeedsReview, onConfirmAll, onStatusClick }: ConstraintsSectionProps) {
  const confirmedCount = constraints.filter(
    (c) => c.confirmation_status === 'confirmed_consultant' || c.confirmation_status === 'confirmed_client'
  ).length

  return (
    <section>
      <SectionHeader
        title="Constraints"
        count={constraints.length}
        confirmedCount={confirmedCount}
        onConfirmAll={() => onConfirmAll('constraint', constraints.map((c) => c.id))}
      />
      {constraints.length === 0 ? (
        <p className="text-[13px] text-[#999999] italic">No constraints identified yet</p>
      ) : (
        <div className="space-y-3">
          {constraints.map((constraint) => (
            <ConstraintAccordionCard
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
