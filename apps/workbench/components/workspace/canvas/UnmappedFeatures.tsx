/**
 * UnmappedFeatures - Pool of features not yet assigned to journey steps
 *
 * Droppable area where features can be placed when unassigned.
 */

'use client'

import { useDroppable } from '@dnd-kit/core'
import { Package } from 'lucide-react'
import { FeatureChip } from './FeatureChip'
import type { FeatureSummary } from '@/types/workspace'

interface UnmappedFeaturesProps {
  features: FeatureSummary[]
}

export function UnmappedFeatures({ features }: UnmappedFeaturesProps) {
  const { isOver, setNodeRef } = useDroppable({
    id: 'unmapped-pool',
  })

  return (
    <div
      ref={setNodeRef}
      className={`
        bg-[#F9F9F9] rounded-lg border-2 border-dashed p-4 min-h-[100px]
        transition-all duration-200
        ${isOver
          ? 'border-[#3FAF7A] bg-emerald-50/50'
          : 'border-[#E5E5E5]'
        }
      `}
    >
      {features.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {features.map((feature) => (
            <FeatureChip key={feature.id} feature={feature} />
          ))}
        </div>
      ) : (
        <div className="flex items-center justify-center h-full min-h-[60px] text-center">
          <div>
            <Package className="w-8 h-8 text-gray-300 mx-auto mb-2" />
            <p className="text-sm text-[#999999]">
              {isOver ? 'Drop here to unassign' : 'All features are mapped to journey steps'}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

export default UnmappedFeatures
