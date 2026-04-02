'use client'

import { useState, useMemo, useCallback, useEffect } from 'react'
import { Calculator, ChevronDown, Check, HelpCircle } from 'lucide-react'
import type { ROISummary } from '@/types/workspace'

interface ValueCalculatorProps {
  roiSummary: ROISummary[]
  workflowPairCount: number
  currentTotalMinutes: number
  futureTotalMinutes: number
  onValuesChange?: (values: CalculatedValues) => void
}

export interface CalculatedValues {
  directSavings: number
  revenueUnlock: number
  additionalClients: number
  totalValue: number
  paybackMonths: number | null
  currentRevenue: number
  futureRevenue: number
  hoursFreedPerYear: number
  isNoBrainer: boolean // payback < 12 months AND directSavings > 0
  engagementValue: number
  engagementsPerYear: number
}

function formatCurrency(n: number) {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`
  return `$${n.toLocaleString()}`
}

// Styled number input that hides browser spinners
function NumberInput({
  value,
  onChange,
  prefix,
  suffix,
  min,
  max,
  step,
  confirmed,
}: {
  value: number
  onChange: (v: number) => void
  prefix?: string
  suffix?: string
  min?: number
  max?: number
  step?: number
  confirmed?: boolean
}) {
  const [localValue, setLocalValue] = useState(String(value))

  // Sync when parent changes
  useEffect(() => {
    setLocalValue(String(value))
  }, [value])

  const handleBlur = () => {
    const parsed = Number(localValue.replace(/[^0-9.-]/g, ''))
    if (!isNaN(parsed)) {
      const clamped = Math.min(max ?? Infinity, Math.max(min ?? 0, parsed))
      onChange(clamped)
      setLocalValue(String(clamped))
    } else {
      setLocalValue(String(value))
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      (e.target as HTMLInputElement).blur()
    }
    if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
      e.preventDefault()
      const delta = (step ?? 1) * (e.key === 'ArrowUp' ? 1 : -1)
      const next = Math.min(max ?? Infinity, Math.max(min ?? 0, value + delta))
      onChange(next)
    }
  }

  return (
    <div className="relative flex items-center">
      {prefix && (
        <span className="absolute left-3 text-[12px] text-text-placeholder pointer-events-none">{prefix}</span>
      )}
      <input
        type="text"
        inputMode="numeric"
        value={localValue}
        onChange={(e) => setLocalValue(e.target.value)}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
        className={`w-full text-[13px] font-medium text-text-body border rounded-lg py-2 focus:outline-none focus:ring-1 focus:ring-brand-primary/30 focus:border-brand-primary bg-white appearance-none ${
          prefix ? 'pl-7' : 'pl-3'
        } ${suffix ? 'pr-8' : 'pr-3'} ${
          confirmed ? 'border-brand-primary/40' : 'border-border'
        }`}
        style={{ MozAppearance: 'textfield' } as React.CSSProperties}
      />
      {suffix && (
        <span className="absolute right-3 text-[11px] text-text-placeholder pointer-events-none">{suffix}</span>
      )}
      {confirmed && (
        <Check className="absolute right-2 w-3 h-3 text-brand-primary" style={suffix ? { right: suffix.length > 2 ? 36 : 28 } : {}} />
      )}
    </div>
  )
}

export function ValueCalculator({
  roiSummary,
  workflowPairCount,
  currentTotalMinutes,
  futureTotalMinutes,
  onValuesChange,
}: ValueCalculatorProps) {
  const [isOpen, setIsOpen] = useState(false)

  const [engagementValue, setEngagementValue] = useState(15000)
  const [engagementsPerYear, setEngagementsPerYear] = useState(18)
  const [teamSize, setTeamSize] = useState(1)
  const [hoursPerEngagement, setHoursPerEngagement] = useState(35)
  const [platformReduction, setPlatformReduction] = useState(45)
  const [estimatedBuildCost, setEstimatedBuildCost] = useState(50000)

  const [confirmed, setConfirmed] = useState<Set<string>>(new Set())
  const markConfirmed = useCallback((key: string) => {
    setConfirmed(prev => new Set(prev).add(key))
  }, [])

  const wrap = useCallback((key: string, setter: (v: number) => void) => {
    return (v: number) => { setter(v); markConfirmed(key) }
  }, [markConfirmed])

  const calculated = useMemo(() => {
    const currentRevenue = engagementsPerYear * engagementValue
    const futureHoursPerEngagement = hoursPerEngagement * (1 - platformReduction / 100)
    const hoursFreedPerYear = (hoursPerEngagement - futureHoursPerEngagement) * engagementsPerYear
    const effectiveHourlyRate = engagementValue / hoursPerEngagement
    const directSavings = Math.round(hoursFreedPerYear * effectiveHourlyRate * 0.6)
    const additionalClients = Math.floor(hoursFreedPerYear / futureHoursPerEngagement)
    const revenueUnlock = additionalClients * engagementValue
    const totalValue = directSavings + revenueUnlock
    const paybackMonths = totalValue > 0 ? Math.round((estimatedBuildCost / totalValue) * 12) : null
    const isNoBrainer = paybackMonths !== null && paybackMonths <= 12 && directSavings > 5000

    const result: CalculatedValues = {
      directSavings, revenueUnlock, additionalClients, totalValue, paybackMonths,
      currentRevenue, futureRevenue: currentRevenue + revenueUnlock,
      hoursFreedPerYear: Math.round(hoursFreedPerYear), isNoBrainer,
      engagementValue, engagementsPerYear,
    }
    return result
  }, [engagementValue, engagementsPerYear, teamSize, hoursPerEngagement, platformReduction, estimatedBuildCost])

  // Notify parent of changes
  useEffect(() => {
    onValuesChange?.(calculated)
  }, [calculated, onValuesChange])

  const confidenceCount = confirmed.size

  return (
    <div className="border border-border rounded-xl overflow-hidden bg-white">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-surface-page transition-colors"
      >
        <div className="flex items-center gap-2">
          <Calculator className="w-4 h-4 text-text-placeholder" />
          <span className="text-[12px] font-semibold text-text-body">Value Calculator</span>
          {!isOpen && (
            <span className="text-[11px] text-text-placeholder ml-1">
              — {formatCurrency(calculated.totalValue)}/yr
              {calculated.paybackMonths !== null && ` · ${calculated.paybackMonths}mo payback`}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {confidenceCount > 0 && (
            <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-brand-primary-light text-[#25785A]">
              {confidenceCount}/6 confirmed
            </span>
          )}
          <ChevronDown className={`w-4 h-4 text-text-placeholder transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </div>
      </button>

      {isOpen && (
        <div className="px-4 pb-4 border-t border-border">
          {/* 2 rows × 3 columns */}
          <div className="grid grid-cols-3 gap-3 mt-3 mb-4">
            <div>
              <label className="text-[10px] font-semibold text-text-placeholder uppercase tracking-wider block mb-1">Avg engagement value</label>
              <NumberInput value={engagementValue} onChange={wrap('engagementValue', setEngagementValue)} prefix="$" min={1000} max={500000} step={1000} confirmed={confirmed.has('engagementValue')} />
            </div>
            <div>
              <label className="text-[10px] font-semibold text-text-placeholder uppercase tracking-wider block mb-1">Engagements / year</label>
              <NumberInput value={engagementsPerYear} onChange={wrap('engagementsPerYear', setEngagementsPerYear)} min={1} max={500} step={1} confirmed={confirmed.has('engagementsPerYear')} />
            </div>
            <div>
              <label className="text-[10px] font-semibold text-text-placeholder uppercase tracking-wider block mb-1">Team size</label>
              <NumberInput value={teamSize} onChange={wrap('teamSize', setTeamSize)} min={1} max={100} step={1} confirmed={confirmed.has('teamSize')} />
            </div>
            <div>
              <label className="text-[10px] font-semibold text-text-placeholder uppercase tracking-wider block mb-1">Hrs / engagement (today)</label>
              <NumberInput value={hoursPerEngagement} onChange={wrap('hoursPerEngagement', setHoursPerEngagement)} suffix="hrs" min={5} max={200} step={1} confirmed={confirmed.has('hoursPerEngagement')} />
            </div>
            <div>
              <label className="text-[10px] font-semibold text-text-placeholder uppercase tracking-wider block mb-1">Platform time reduction</label>
              <NumberInput value={platformReduction} onChange={wrap('platformReduction', setPlatformReduction)} suffix="%" min={10} max={80} step={5} confirmed={confirmed.has('platformReduction')} />
            </div>
            <div>
              <label className="text-[10px] font-semibold text-text-placeholder uppercase tracking-wider block mb-1">Estimated build cost</label>
              <NumberInput value={estimatedBuildCost} onChange={wrap('estimatedBuildCost', setEstimatedBuildCost)} prefix="$" min={5000} max={1000000} step={5000} confirmed={confirmed.has('estimatedBuildCost')} />
            </div>
          </div>

          {/* Results — 2×2 grid + total */}
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div className="rounded-lg px-3 py-2.5 border border-border bg-white">
              <div className="text-[10px] font-semibold text-text-placeholder uppercase">Current Revenue</div>
              <div className="text-[15px] font-semibold text-text-body">{formatCurrency(calculated.currentRevenue)}<span className="text-[10px] font-normal text-text-placeholder">/yr</span></div>
              <div className="text-[10px] text-text-placeholder">{engagementsPerYear} × {formatCurrency(engagementValue)}</div>
            </div>
            <div className="rounded-lg px-3 py-2.5 border border-border bg-white">
              <div className="text-[10px] font-semibold text-text-placeholder uppercase">Hours Freed</div>
              <div className="text-[15px] font-semibold text-text-body">{calculated.hoursFreedPerYear} hrs<span className="text-[10px] font-normal text-text-placeholder">/yr</span></div>
              <div className="text-[10px] text-text-placeholder">{Math.round(calculated.hoursFreedPerYear / 52)} hrs/week</div>
            </div>
            <div className="rounded-lg px-3 py-2.5 border border-border bg-white">
              <div className="text-[10px] font-semibold text-text-placeholder uppercase">Direct Savings</div>
              <div className="text-[15px] font-bold text-text-body">{formatCurrency(calculated.directSavings)}<span className="text-[10px] font-normal text-text-placeholder">/yr</span></div>
              <div className="text-[10px] text-text-placeholder">Time reinvested into delivery</div>
            </div>
            <div className="rounded-lg px-3 py-2.5 border border-brand-primary/20 bg-white">
              <div className="text-[10px] font-semibold text-text-placeholder uppercase">Revenue Capacity</div>
              <div className="text-[15px] font-bold text-text-body">{formatCurrency(calculated.revenueUnlock)}<span className="text-[10px] font-normal text-text-placeholder">/yr</span></div>
              <div className="text-[10px] text-text-placeholder">+{calculated.additionalClients} clients at {formatCurrency(engagementValue)}</div>
            </div>
          </div>

          <div className="flex items-center justify-between rounded-lg px-4 py-3 border border-border bg-white">
            <div>
              <div className="text-[10px] font-semibold text-text-placeholder uppercase">Total Annual Value</div>
              <div className="text-[20px] font-bold text-text-body">{formatCurrency(calculated.totalValue)}<span className="text-[11px] font-normal text-text-placeholder">/yr</span></div>
            </div>
            {calculated.paybackMonths !== null && (
              <div className="text-right">
                <div className="text-[10px] font-semibold text-text-placeholder uppercase">Payback</div>
                <div className={`text-[20px] font-bold ${calculated.isNoBrainer ? 'text-[#25785A]' : 'text-text-body'}`}>
                  {calculated.paybackMonths < 12 ? `${calculated.paybackMonths} mo` : `${(calculated.paybackMonths / 12).toFixed(1)} yr`}
                </div>
                <div className="text-[10px] text-text-placeholder">on {formatCurrency(estimatedBuildCost)}</div>
              </div>
            )}
          </div>

          {confidenceCount < 3 && (
            <div className="flex items-center gap-2 mt-3">
              <HelpCircle className="w-3.5 h-3.5 text-text-placeholder shrink-0" />
              <span className="text-[11px] text-text-placeholder">
                Edit the inputs above to confirm them. {6 - confidenceCount} unconfirmed values are using estimates.
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
