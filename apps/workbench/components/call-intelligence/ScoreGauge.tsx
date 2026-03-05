'use client'

export function ScoreGauge({ score, label, size = 'normal' }: { score: number; label: string; size?: 'normal' | 'small' }) {
  const pct = Math.round(score * 100)
  const color = pct < 40 ? 'text-red-500' : pct < 70 ? 'text-amber-500' : 'text-green-500'
  const trackColor = pct < 40 ? 'stroke-red-100' : pct < 70 ? 'stroke-amber-100' : 'stroke-green-100'
  const fillColor = pct < 40 ? 'stroke-red-500' : pct < 70 ? 'stroke-amber-500' : 'stroke-green-500'

  const sz = size === 'small' ? 56 : 96
  const r = size === 'small' ? 22 : 40
  const sw = size === 'small' ? 5 : 8
  const center = sz / 2
  const circumference = 2 * Math.PI * r
  const dashOffset = circumference - (pct / 100) * circumference

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={sz} height={sz} viewBox={`0 0 ${sz} ${sz}`}>
        <circle cx={center} cy={center} r={r} fill="none" strokeWidth={sw} className={trackColor} />
        <circle
          cx={center} cy={center} r={r} fill="none" strokeWidth={sw}
          className={fillColor}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          transform={`rotate(-90 ${center} ${center})`}
        />
        <text x={center} y={center} textAnchor="middle" dominantBaseline="central"
          className={`${size === 'small' ? 'text-sm' : 'text-xl'} font-bold ${color}`} fill="currentColor">
          {pct}%
        </text>
      </svg>
      <span className={`${size === 'small' ? 'text-[10px]' : 'text-xs'} text-text-muted font-medium text-center leading-tight`}>{label}</span>
    </div>
  )
}
