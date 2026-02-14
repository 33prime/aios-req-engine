'use client'

interface CompletenessRingProps {
  score: number // 0-100
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
}

const SIZE_MAP = {
  sm: { width: 28, stroke: 3, fontSize: '8px', fontWeight: 700 },
  md: { width: 40, stroke: 4, fontSize: '11px', fontWeight: 700 },
  lg: { width: 64, stroke: 5, fontSize: '16px', fontWeight: 700 },
} as const

export function CompletenessRing({ score, size = 'sm', showLabel = true }: CompletenessRingProps) {
  const { width, stroke, fontSize, fontWeight } = SIZE_MAP[size]
  const radius = (width - stroke) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (score / 100) * circumference

  // Color based on score
  const color = score >= 80
    ? '#25785A'  // dark green — excellent
    : score >= 60
      ? '#3FAF7A'  // brand green — good
      : '#999999'  // gray — fair/poor

  return (
    <div className="inline-flex items-center gap-1.5" title={`Completeness: ${Math.round(score)}%`}>
      <svg width={width} height={width} className="shrink-0">
        {/* Background circle */}
        <circle
          cx={width / 2}
          cy={width / 2}
          r={radius}
          fill="none"
          stroke="#E5E5E5"
          strokeWidth={stroke}
        />
        {/* Progress arc */}
        <circle
          cx={width / 2}
          cy={width / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform={`rotate(-90 ${width / 2} ${width / 2})`}
          className="transition-all duration-500"
        />
        {/* Score text (only on md and lg) */}
        {size !== 'sm' && showLabel && (
          <text
            x="50%"
            y="50%"
            textAnchor="middle"
            dominantBaseline="central"
            fill={color}
            style={{ fontSize, fontWeight }}
          >
            {Math.round(score)}
          </text>
        )}
      </svg>
    </div>
  )
}
