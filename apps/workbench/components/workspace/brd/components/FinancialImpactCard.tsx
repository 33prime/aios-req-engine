'use client'

interface FinancialImpactCardProps {
  monetaryValueLow?: number | null
  monetaryValueHigh?: number | null
  monetaryType?: string | null
  monetaryTimeframe?: string | null
  monetaryConfidence?: number | null
  monetarySource?: string | null
}

function formatCurrency(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `$${Math.round(value / 1_000)}K`
  return `$${value.toFixed(0)}`
}

const TYPE_LABELS: Record<string, string> = {
  cost_reduction: 'Cost Reduction',
  revenue_increase: 'Revenue Increase',
  revenue_new: 'New Revenue',
  risk_avoidance: 'Risk Avoidance',
  productivity_gain: 'Productivity Gain',
}

const TIMEFRAME_LABELS: Record<string, string> = {
  annual: '/ year',
  monthly: '/ month',
  quarterly: '/ quarter',
  per_transaction: '/ transaction',
  one_time: 'one-time',
}

export function FinancialImpactCard({
  monetaryValueLow,
  monetaryValueHigh,
  monetaryType,
  monetaryTimeframe,
  monetaryConfidence,
  monetarySource,
}: FinancialImpactCardProps) {
  const hasValues = monetaryValueLow != null || monetaryValueHigh != null
  if (!hasValues) return null

  const low = monetaryValueLow ?? 0
  const high = monetaryValueHigh ?? low
  const timeLabel = TIMEFRAME_LABELS[monetaryTimeframe || 'annual'] || '/ year'
  const typeLabel = TYPE_LABELS[monetaryType || ''] || monetaryType || ''

  // Build range display
  let rangeText: string
  if (low > 0 && high > 0 && low !== high) {
    rangeText = `${formatCurrency(low)} - ${formatCurrency(high)}`
  } else if (high > 0) {
    rangeText = formatCurrency(high)
  } else {
    rangeText = formatCurrency(low)
  }

  return (
    <div className="border border-border rounded-xl overflow-hidden bg-white">
      {/* Header: big number */}
      <div className="px-4 py-3 bg-[#F4F4F4] border-b border-border">
        <div className="flex items-baseline gap-2">
          <span className="text-[20px] font-bold text-text-body">{rangeText}</span>
          <span className="text-[13px] text-[#666666]">{timeLabel}</span>
        </div>
      </div>

      <div className="px-4 py-3 space-y-3">
        {/* Type badge */}
        {typeLabel && (
          <div>
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-[#F0F0F0] text-[#666666]">
              {typeLabel}
            </span>
          </div>
        )}

        {/* Confidence bar */}
        {monetaryConfidence != null && (
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-[11px] text-text-placeholder">Confidence</span>
              <span className="text-[11px] font-medium text-[#666666]">
                {Math.round(monetaryConfidence * 100)}%
              </span>
            </div>
            <div className="h-1.5 bg-[#F0F0F0] rounded-full overflow-hidden">
              <div
                className="h-full bg-brand-primary rounded-full transition-all"
                style={{ width: `${monetaryConfidence * 100}%` }}
              />
            </div>
          </div>
        )}

        {/* Source explanation */}
        {monetarySource && (
          <p className="text-[11px] text-text-placeholder leading-relaxed">{monetarySource}</p>
        )}
      </div>
    </div>
  )
}
