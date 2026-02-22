'use client'

import { Check } from 'lucide-react'

interface DesignCardProps {
  id: string
  label: string
  description: string
  colors: string[]
  isSelected: boolean
  onSelect: () => void
  logoUrl?: string | null
  source?: string
  size?: 'sm' | 'md'
}

export function DesignCard({
  label,
  description,
  colors,
  isSelected,
  onSelect,
  logoUrl,
  source,
  size = 'md',
}: DesignCardProps) {
  const isSmall = size === 'sm'

  return (
    <button
      onClick={onSelect}
      className={`
        relative text-left border-2 rounded-lg transition-all
        ${isSmall ? 'p-3' : 'p-4'}
        ${
          isSelected
            ? 'border-[#3FAF7A] bg-[#3FAF7A]/5 ring-1 ring-[#3FAF7A]/20'
            : 'border-[#E5E5E5] bg-white hover:border-gray-300 hover:shadow-sm'
        }
      `}
    >
      {/* Selection indicator */}
      {isSelected && (
        <div className="absolute top-2 right-2 w-5 h-5 rounded-full bg-[#3FAF7A] flex items-center justify-center">
          <Check className="w-3 h-3 text-white" />
        </div>
      )}

      {/* Logo if available */}
      {logoUrl && (
        <div className="mb-3 h-8 flex items-center">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={logoUrl}
            alt="Brand logo"
            className="h-6 max-w-[120px] object-contain"
          />
        </div>
      )}

      {/* Color swatches */}
      <div className="flex items-center gap-1.5 mb-2">
        {colors.slice(0, 5).map((color, i) => (
          <div
            key={i}
            className="rounded-full border border-black/10"
            style={{
              backgroundColor: color,
              width: isSmall ? 16 : 20,
              height: isSmall ? 16 : 20,
            }}
          />
        ))}
      </div>

      {/* Label */}
      <div className={`font-medium text-[#333333] ${isSmall ? 'text-sm' : 'text-base'}`}>
        {label}
      </div>

      {/* Description */}
      <p className={`text-[#999999] mt-0.5 ${isSmall ? 'text-xs' : 'text-sm'}`}>
        {description}
      </p>

      {/* Source attribution */}
      {source && (
        <p className="text-xs text-[#999999] mt-1.5 italic">
          Source: {source}
        </p>
      )}
    </button>
  )
}
