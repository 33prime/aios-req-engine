'use client'

import { Settings } from 'lucide-react'

interface BuildingGearBadgeProps {
  onClick: (e: React.MouseEvent) => void
}

export function BuildingGearBadge({ onClick }: BuildingGearBadgeProps) {
  return (
    <button
      onClick={(e) => {
        e.stopPropagation()
        onClick(e)
      }}
      className="absolute top-3 right-3 z-10 flex items-center gap-1.5 bg-[#E8F5E9] text-[#25785A] rounded-full px-2.5 py-1 shadow-sm hover:bg-[#d4edda] transition-colors"
      title="Build in progress — click for details"
    >
      <Settings
        className="w-3.5 h-3.5 animate-spin"
        style={{ animationDuration: '3s' }}
      />
      <span className="text-[10px] font-medium">Building</span>
    </button>
  )
}
