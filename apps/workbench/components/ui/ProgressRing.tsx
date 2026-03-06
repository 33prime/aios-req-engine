'use client'

interface ProgressRingProps {
  /** Progress value 0-100 */
  value: number
  /** Size in px (default 32) */
  size?: number
  /** Stroke width (default 3) */
  strokeWidth?: number
  /** Show percentage text inside */
  showLabel?: boolean
  className?: string
}

export function ProgressRing({
  value,
  size = 32,
  strokeWidth = 3,
  showLabel = false,
  className = '',
}: ProgressRingProps) {
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (Math.min(Math.max(value, 0), 100) / 100) * circumference

  return (
    <svg
      width={size}
      height={size}
      className={className}
      viewBox={`0 0 ${size} ${size}`}
    >
      {/* Background circle */}
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        className="text-gray-200"
      />
      {/* Progress circle */}
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        className="text-brand-primary transition-[stroke-dashoffset] duration-500"
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
      />
      {showLabel && (
        <text
          x="50%"
          y="50%"
          textAnchor="middle"
          dominantBaseline="central"
          className="fill-text-secondary text-[9px] font-medium"
        >
          {Math.round(value)}%
        </text>
      )}
    </svg>
  )
}
