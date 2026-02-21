/**
 * FeatureChip - Draggable feature badge with click popover
 *
 * Shows feature name, MVP status, and confirmation state.
 * Can be dragged between journey steps and unmapped pool.
 * Click (without drag) shows a detail popover.
 */

'use client'

import { useState, useRef, useEffect } from 'react'
import { useDraggable } from '@dnd-kit/core'
import { CSS } from '@dnd-kit/utilities'
import { GripVertical, Star, CheckCircle, AlertCircle, X } from 'lucide-react'
import type { FeatureSummary } from '@/types/workspace'

interface FeatureChipProps {
  feature: FeatureSummary
  isDragging?: boolean
}

export function FeatureChip({ feature, isDragging = false }: FeatureChipProps) {
  const { attributes, listeners, setNodeRef, transform } = useDraggable({
    id: feature.id,
  })
  const [showPopover, setShowPopover] = useState(false)
  const pointerDownTime = useRef(0)
  const popoverRef = useRef<HTMLDivElement>(null)
  const chipRef = useRef<HTMLDivElement>(null)

  const style = transform
    ? {
        transform: CSS.Translate.toString(transform),
      }
    : undefined

  // Close popover on outside click
  useEffect(() => {
    if (!showPopover) return
    const handleClick = (e: MouseEvent) => {
      if (
        popoverRef.current && !popoverRef.current.contains(e.target as Node) &&
        chipRef.current && !chipRef.current.contains(e.target as Node)
      ) {
        setShowPopover(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [showPopover])

  const handlePointerDown = () => {
    pointerDownTime.current = Date.now()
  }

  const handleClick = () => {
    const elapsed = Date.now() - pointerDownTime.current
    // Only trigger click if pointer was held for less than 200ms (not a drag)
    if (elapsed < 200) {
      setShowPopover(!showPopover)
    }
  }

  const getStatusColor = (status?: string | null) => {
    switch (status) {
      case 'confirmed_client':
        return 'border-green-300 bg-green-50'
      case 'confirmed_consultant':
        return 'border-blue-300 bg-blue-50'
      case 'needs_client':
      case 'needs_confirmation':
        return 'border-amber-300 bg-amber-50'
      default:
        return 'border-ui-cardBorder bg-white'
    }
  }

  const getStatusIcon = (status?: string | null) => {
    switch (status) {
      case 'confirmed_client':
        return <CheckCircle className="w-3 h-3 text-green-500" />
      case 'confirmed_consultant':
        return <CheckCircle className="w-3 h-3 text-blue-500" />
      case 'needs_client':
      case 'needs_confirmation':
        return <AlertCircle className="w-3 h-3 text-amber-500" />
      default:
        return null
    }
  }

  const getStatusLabel = (status?: string | null) => {
    switch (status) {
      case 'confirmed_client': return 'Client Confirmed'
      case 'confirmed_consultant': return 'Consultant Confirmed'
      case 'needs_client':
      case 'needs_confirmation': return 'Needs Confirmation'
      default: return 'AI Generated'
    }
  }

  // NEW/UPDATED badge — only for ai_generated within 24h
  const getEntityBadge = () => {
    if (feature.confirmation_status && feature.confirmation_status !== 'ai_generated') return null
    const createdAt = (feature as { created_at?: string | null }).created_at
    const version = (feature as { version?: number | null }).version
    if (!createdAt) return null
    const age = Date.now() - new Date(createdAt).getTime()
    const isRecent = age < 24 * 60 * 60 * 1000
    if (!isRecent) return null
    if (version === 1 || version == null) return { label: 'NEW', color: 'bg-emerald-500' }
    return { label: 'UPDATED', color: 'bg-indigo-500' }
  }

  const badge = getEntityBadge()

  return (
    <div className="relative" ref={chipRef}>
      <div
        ref={setNodeRef}
        style={style}
        {...attributes}
        {...listeners}
        onPointerDown={(e) => {
          handlePointerDown()
          // Call dnd-kit's listener
          listeners?.onPointerDown?.(e)
        }}
        onClick={handleClick}
        title={feature.description || feature.name}
        className={`
          inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border
          text-sm cursor-grab active:cursor-grabbing
          transition-all hover:shadow-sm hover:scale-[1.02]
          ${getStatusColor(feature.confirmation_status)}
          ${isDragging ? 'shadow-lg opacity-90 scale-105' : ''}
        `}
      >
        <GripVertical className="w-3 h-3 text-ui-supportText flex-shrink-0" />

        {feature.is_mvp && (
          <Star className="w-4 h-4 text-amber-500 fill-amber-500 flex-shrink-0" />
        )}

        <span className="font-medium text-ui-headingDark truncate max-w-[150px]">
          {feature.name}
        </span>

        {badge && (
          <span className={`px-1 py-px text-[9px] font-bold text-white rounded ${badge.color} leading-tight`}>
            {badge.label}
          </span>
        )}

        {getStatusIcon(feature.confirmation_status)}
      </div>

      {/* Popover */}
      {showPopover && !isDragging && (
        <div
          ref={popoverRef}
          className="absolute z-50 top-full left-0 mt-2 w-72 bg-white rounded-lg border border-ui-cardBorder shadow-lg p-4"
        >
          <div className="flex items-start justify-between gap-2 mb-2">
            <h4 className="text-sm font-semibold text-ui-headingDark">{feature.name}</h4>
            <button
              onClick={(e) => { e.stopPropagation(); setShowPopover(false) }}
              className="p-0.5 rounded text-ui-supportText hover:text-ui-headingDark"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          {feature.description && (
            <p className="text-sm text-ui-bodyText mb-3">{feature.description}</p>
          )}

          <div className="flex flex-wrap gap-2">
            {feature.is_mvp && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-amber-100 text-amber-700">
                <Star className="w-3 h-3 fill-amber-500" />
                MVP
              </span>
            )}
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium ${
              feature.confirmation_status === 'confirmed_client' ? 'bg-green-100 text-green-700' :
              feature.confirmation_status === 'confirmed_consultant' ? 'bg-blue-100 text-blue-700' :
              feature.confirmation_status === 'needs_client' || feature.confirmation_status === 'needs_confirmation' ? 'bg-amber-100 text-amber-700' :
              'bg-gray-100 text-gray-600'
            }`}>
              {getStatusLabel(feature.confirmation_status)}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}

export default FeatureChip
