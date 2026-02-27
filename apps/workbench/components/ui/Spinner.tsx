interface SpinnerProps {
  /** 'sm' = h-5, 'md' = h-6, 'lg' = h-8 */
  size?: 'sm' | 'md' | 'lg'
  label?: string
}

const SIZE_CLASSES = {
  sm: 'h-5 w-5',
  md: 'h-6 w-6',
  lg: 'h-8 w-8',
}

export function Spinner({ size = 'md', label = 'Loading...' }: SpinnerProps) {
  return (
    <div className="text-center py-8">
      <div className={`animate-spin rounded-full ${SIZE_CLASSES[size]} border-b-2 border-brand-primary mx-auto`} />
      {label && <p className="text-[12px] text-text-placeholder mt-2">{label}</p>}
    </div>
  )
}
