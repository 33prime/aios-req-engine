'use client'

import React, { useState, useCallback } from 'react'
import { Popover, PopoverTrigger, PopoverContent } from '@/components/ui/popover'
import { getStageStatus, advanceStage } from '@/lib/api'
import type { StageStatusResponse, StageGateCriterion } from '@/types/api'

const STAGE_LABELS: Record<string, string> = {
  discovery: 'Discovery',
  validation: 'Validation',
  prototype: 'Prototype',
  proposal: 'Proposal',
  build: 'Build',
  live: 'Live',
}

interface StageAdvancePopoverProps {
  projectId: string
  children: React.ReactNode
  onStageAdvanced?: () => void
}

export function StageAdvancePopover({
  projectId,
  children,
  onStageAdvanced,
}: StageAdvancePopoverProps) {
  const [open, setOpen] = useState(false)
  const [status, setStatus] = useState<StageStatusResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [advancing, setAdvancing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showForce, setShowForce] = useState(false)
  const [forceReason, setForceReason] = useState('')

  const loadStatus = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getStageStatus(projectId)
      setStatus(data)
    } catch (e) {
      setError('Failed to load stage status')
    } finally {
      setLoading(false)
    }
  }, [projectId])

  const handleOpenChange = (isOpen: boolean) => {
    setOpen(isOpen)
    if (isOpen) {
      loadStatus()
      setShowForce(false)
      setForceReason('')
    }
  }

  const handleAdvance = async (force = false) => {
    if (!status?.next_stage) return
    setAdvancing(true)
    setError(null)
    try {
      await advanceStage(projectId, {
        target_stage: status.next_stage,
        force,
        reason: force ? forceReason || undefined : undefined,
      })
      setOpen(false)
      onStageAdvanced?.()
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Failed to advance stage'
      // Try to parse backend detail from JSON error
      try {
        const parsed = JSON.parse(msg)
        setError(parsed.detail || msg)
      } catch {
        setError(msg)
      }
    } finally {
      setAdvancing(false)
    }
  }

  return (
    <Popover open={open} onOpenChange={handleOpenChange}>
      <PopoverTrigger asChild>{children}</PopoverTrigger>
      <PopoverContent
        align="start"
        sideOffset={8}
        className="w-80 p-0"
        onClick={(e) => e.stopPropagation()}
      >
        {loading ? (
          <div className="p-4 text-center">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-[#3FAF7A] mx-auto mb-2" />
            <p className="text-xs text-[#999999]">Loading criteria...</p>
          </div>
        ) : error && !status ? (
          <div className="p-4 text-center">
            <p className="text-xs text-red-600">{error}</p>
          </div>
        ) : status ? (
          <div>
            {/* Header */}
            <div className="px-4 pt-3 pb-2 border-b border-[#E5E5E5]">
              <div className="flex items-center gap-1.5 text-sm font-medium text-[#333333]">
                <span>{STAGE_LABELS[status.current_stage] || status.current_stage}</span>
                <svg className="w-3.5 h-3.5 text-[#999999]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
                <span>{status.next_stage ? (STAGE_LABELS[status.next_stage] || status.next_stage) : 'Final'}</span>
              </div>
              {status.transition_description && (
                <p className="text-xs text-[#999999] mt-0.5">{status.transition_description}</p>
              )}
            </div>

            {/* Progress bar */}
            {status.criteria_total > 0 && (
              <div className="px-4 pt-2">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-[#999999]">
                    {status.criteria_met} / {status.criteria_total} criteria met
                  </span>
                  <span className="text-xs font-medium text-[#333333]">
                    {Math.round(status.progress_pct)}%
                  </span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-1.5">
                  <div
                    className={`h-1.5 rounded-full transition-all ${
                      status.can_advance ? 'bg-emerald-500' : 'bg-amber-400'
                    }`}
                    style={{ width: `${status.progress_pct}%` }}
                  />
                </div>
              </div>
            )}

            {/* Criteria checklist */}
            {status.criteria.length > 0 && (
              <div className="px-4 py-2 space-y-1.5">
                {status.criteria.map((c) => (
                  <CriterionRow key={c.gate_name} criterion={c} />
                ))}
              </div>
            )}

            {/* Error */}
            {error && (
              <div className="px-4 py-1">
                <p className="text-xs text-red-600">{error}</p>
              </div>
            )}

            {/* Actions */}
            <div className="px-4 py-3 border-t border-[#E5E5E5] space-y-2">
              {status.can_advance && status.next_stage && (
                <button
                  onClick={() => handleAdvance(false)}
                  disabled={advancing}
                  className="w-full px-3 py-1.5 text-xs font-medium text-white bg-[#3FAF7A] rounded-md hover:bg-[#008574] disabled:opacity-50 transition-colors"
                >
                  {advancing ? 'Advancing...' : `Advance to ${STAGE_LABELS[status.next_stage] || status.next_stage}`}
                </button>
              )}

              {!status.is_final_stage && status.next_stage && (
                <>
                  {!showForce ? (
                    <button
                      onClick={() => setShowForce(true)}
                      className="w-full text-xs text-[#999999] hover:text-[#333333] transition-colors"
                    >
                      Override...
                    </button>
                  ) : (
                    <div className="space-y-1.5">
                      <input
                        type="text"
                        placeholder="Reason for override"
                        value={forceReason}
                        onChange={(e) => setForceReason(e.target.value)}
                        className="w-full px-2 py-1 text-xs border border-[#E5E5E5] rounded-md focus:outline-none focus:ring-1 focus:ring-[#3FAF7A]"
                      />
                      <button
                        onClick={() => handleAdvance(true)}
                        disabled={advancing}
                        className="w-full px-3 py-1.5 text-xs font-medium text-amber-700 bg-amber-50 border border-amber-200 rounded-md hover:bg-amber-100 disabled:opacity-50 transition-colors"
                      >
                        {advancing ? 'Advancing...' : 'Force Advance'}
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        ) : null}
      </PopoverContent>
    </Popover>
  )
}

function CriterionRow({ criterion }: { criterion: StageGateCriterion }) {
  const [expanded, setExpanded] = useState(false)
  const hasDetails = !criterion.satisfied && (criterion.missing.length > 0 || criterion.how_to_acquire.length > 0)

  return (
    <div>
      <button
        onClick={() => hasDetails && setExpanded(!expanded)}
        className={`flex items-start gap-2 w-full text-left ${hasDetails ? 'cursor-pointer' : 'cursor-default'}`}
      >
        {criterion.satisfied ? (
          <svg className="w-4 h-4 text-emerald-500 mt-px flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        ) : (
          <svg className="w-4 h-4 text-gray-300 mt-px flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <circle cx="12" cy="12" r="10" />
          </svg>
        )}
        <span className={`text-xs ${criterion.satisfied ? 'text-[#333333]' : 'text-[#999999]'}`}>
          {criterion.gate_label}
        </span>
        {hasDetails && (
          <svg
            className={`w-3 h-3 text-[#999999] ml-auto mt-0.5 flex-shrink-0 transition-transform ${expanded ? 'rotate-90' : ''}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
          </svg>
        )}
      </button>

      {expanded && hasDetails && (
        <div className="ml-6 mt-1 space-y-1">
          {criterion.missing.length > 0 && (
            <div>
              <p className="text-[10px] font-medium text-[#999999] uppercase tracking-wide">Missing</p>
              <ul className="text-[11px] text-[#333333] space-y-0.5">
                {criterion.missing.map((m, i) => (
                  <li key={i} className="flex items-start gap-1">
                    <span className="text-red-400 mt-px">-</span>
                    <span>{m}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {criterion.how_to_acquire.length > 0 && (
            <div>
              <p className="text-[10px] font-medium text-[#999999] uppercase tracking-wide">How to acquire</p>
              <ul className="text-[11px] text-[#333333] space-y-0.5">
                {criterion.how_to_acquire.map((h, i) => (
                  <li key={i} className="flex items-start gap-1">
                    <span className="text-[#3FAF7A] mt-px">+</span>
                    <span>{h}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
