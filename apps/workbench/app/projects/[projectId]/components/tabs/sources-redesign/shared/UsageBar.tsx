/**
 * UsageBar Component
 *
 * Horizontal progress bar showing usage percentage.
 * Used to indicate how much a source has contributed to the project.
 */

interface UsageBarProps {
  /** Usage count */
  count: number
  /** Maximum value for 100% (optional, defaults to adaptive) */
  max?: number
  /** Show count label */
  showCount?: boolean
  /** Size variant */
  size?: 'sm' | 'md'
}

export function UsageBar({ count, max, showCount = true, size = 'sm' }: UsageBarProps) {
  // Calculate percentage - use adaptive max if not provided
  const adaptiveMax = max ?? Math.max(10, count * 2)
  const percentage = Math.min(100, (count / adaptiveMax) * 100)

  const barHeight = size === 'sm' ? 'h-1.5' : 'h-2'

  return (
    <div className="flex items-center gap-2">
      <div className={`flex-1 ${barHeight} bg-gray-200 rounded-full overflow-hidden`}>
        <div
          className={`${barHeight} bg-brand-primary rounded-full transition-all duration-300`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {showCount && (
        <span className="text-xs text-gray-500 tabular-nums min-w-[2rem]">
          {count}x
        </span>
      )}
    </div>
  )
}
