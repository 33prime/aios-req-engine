interface EmptyStateProps {
  icon: React.ReactNode
  title: string
  description: string
}

export function EmptyState({ icon, title, description }: EmptyStateProps) {
  return (
    <div className="text-center py-8">
      <div className="mx-auto mb-3">{icon}</div>
      <p className="text-[13px] text-[#666666] mb-1">{title}</p>
      <p className="text-[12px] text-text-placeholder">{description}</p>
    </div>
  )
}
