'use client'

export function ScoreGauge({ score, label, size = 'normal' }: { score: number; label: string; size?: 'normal' | 'small' }) {
  const pct = Math.round(score * 100)
  // BRD palette: low = navy, mid = teal, high = green
  const color = pct < 40 ? 'text-[#044159]' : pct < 70 ? 'text-[#044159]' : 'text-[#25785A]'
  const trackColor = 'stroke-[#F0F0F0]'
  const fillColor = pct < 40 ? 'stroke-[#044159]' : pct < 70 ? 'stroke-[#88BABF]' : 'stroke-[#3FAF7A]'

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
