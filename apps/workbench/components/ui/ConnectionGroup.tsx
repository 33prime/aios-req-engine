interface ConnectionGroupProps {
  icon: React.ComponentType<{ className?: string }>
  title: string
  count: number
  children: React.ReactNode
}

export function ConnectionGroup({ icon: GroupIcon, title, count, children }: ConnectionGroupProps) {
  return (
    <div>
      <h4 className="text-[11px] font-medium text-text-placeholder uppercase tracking-wide mb-2 flex items-center gap-1.5">
        <GroupIcon className="w-3.5 h-3.5" />
        {title}
        <span className="text-[10px] bg-[#F0F0F0] text-[#666666] px-1.5 py-0.5 rounded-full ml-1">{count}</span>
      </h4>
      <div className="border border-border rounded-xl overflow-hidden bg-white">{children}</div>
    </div>
  )
}
