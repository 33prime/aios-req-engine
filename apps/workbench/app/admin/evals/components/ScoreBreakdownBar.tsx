'use client'

interface Props {
  score: number
  label?: string
  showValue?: boolean
}

function getColor(score: number) {
  if (score >= 0.8) return '#3FAF7A'
  if (score >= 0.5) return '#f59e0b'
  return '#ef4444'
}

export function ScoreBreakdownBar({ score, label, showValue = true }: Props) {
  const pct = Math.min(score * 100, 100)
  const color = getColor(score)

  return (
    <div className="flex items-center gap-2">
      {label && (
        <span className="text-[11px] text-[#666666] w-24 truncate">{label}</span>
      )}
      <div className="flex-1 h-2 bg-border rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      {showValue && (
        <span className="text-[11px] font-medium w-10 text-right" style={{ color }}>
          {(score * 100).toFixed(0)}%
        </span>
      )}
    </div>
  )
}

export function ActionBadge({ action }: { action: string }) {
  const styles: Record<string, string> = {
    accept: 'bg-[#E8F5E9] text-brand-primary',
    retry: 'bg-[#FEF3C7] text-[#92400e]',
    notify: 'bg-[#FEE2E2] text-[#991b1b]',
    pending: 'bg-[#F0F0F0] text-[#666666]',
  }

  return (
    <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${styles[action] || styles.pending}`}>
      {action}
    </span>
  )
}
