/**
 * PendingQueue Component
 *
 * Shows items needing client input, grouped by type.
 * Feeds into the package generation flow.
 */

'use client'

import React, { useState } from 'react'
import {
  Layers,
  Users,
  MessageSquare,
  FileText,
  Target,
  TrendingUp,
  AlertCircle,
  Sparkles,
  ChevronDown,
  ChevronUp,
  X,
} from 'lucide-react'
import type { PendingItem, PendingItemType, PendingItemsQueue } from '@/types/api'

interface PendingQueueProps {
  queue: PendingItemsQueue
  onGeneratePackage: (itemIds?: string[]) => void
  onRemoveItem?: (itemId: string) => void
  isGenerating?: boolean
}

const TYPE_CONFIG: Record<
  PendingItemType,
  { label: string; icon: React.ElementType; color: string }
> = {
  feature: { label: 'Features', icon: Layers, color: 'text-[#009b87] bg-[#009b87]/10' },
  persona: { label: 'Personas', icon: Users, color: 'text-[#009b87] bg-[#009b87]/10' },
  vp_step: { label: 'Value Path', icon: Target, color: 'text-[#009b87] bg-[#009b87]/10' },
  question: { label: 'Questions', icon: MessageSquare, color: 'text-[#009b87] bg-[#009b87]/10' },
  document: { label: 'Documents', icon: FileText, color: 'text-gray-600 bg-gray-100' },
  kpi: { label: 'KPIs', icon: TrendingUp, color: 'text-[#009b87] bg-[#009b87]/10' },
  goal: { label: 'Goals', icon: Target, color: 'text-[#009b87] bg-[#009b87]/10' },
  pain_point: { label: 'Pain Points', icon: AlertCircle, color: 'text-red-600 bg-red-50' },
  requirement: { label: 'Requirements', icon: FileText, color: 'text-gray-600 bg-gray-100' },
  competitor: { label: 'Competitors', icon: Target, color: 'text-gray-600 bg-gray-100' },
  design_preference: { label: 'Design Prefs', icon: Layers, color: 'text-gray-600 bg-gray-100' },
  stakeholder: { label: 'Stakeholders', icon: Users, color: 'text-[#009b87] bg-[#009b87]/10' },
}

export function PendingQueue({
  queue,
  onGeneratePackage,
  onRemoveItem,
  isGenerating = false,
}: PendingQueueProps) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [expandedTypes, setExpandedTypes] = useState<Set<string>>(new Set())

  const toggleSelection = (itemId: string) => {
    const newSelected = new Set(selectedIds)
    if (newSelected.has(itemId)) {
      newSelected.delete(itemId)
    } else {
      newSelected.add(itemId)
    }
    setSelectedIds(newSelected)
  }

  const toggleType = (type: string) => {
    const newExpanded = new Set(expandedTypes)
    if (newExpanded.has(type)) {
      newExpanded.delete(type)
    } else {
      newExpanded.add(type)
    }
    setExpandedTypes(newExpanded)
  }

  const selectAll = () => {
    setSelectedIds(new Set(queue.items.map((item) => item.id)))
  }

  const selectNone = () => {
    setSelectedIds(new Set())
  }

  const handleGenerate = () => {
    if (selectedIds.size > 0) {
      onGeneratePackage(Array.from(selectedIds))
    } else {
      onGeneratePackage()
    }
  }

  // Group items by type
  const groupedItems = queue.items.reduce((acc, item) => {
    const type = item.item_type
    if (!acc[type]) {
      acc[type] = []
    }
    acc[type].push(item)
    return acc
  }, {} as Record<string, PendingItem[]>)

  if (queue.total_count === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center gap-2 mb-4">
          <MessageSquare className="w-5 h-5 text-[#009b87]" />
          <h3 className="text-lg font-semibold text-gray-900">Pending Input Queue</h3>
        </div>
        <div className="text-center py-8">
          <MessageSquare className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No items pending client input</p>
          <p className="text-sm text-gray-400 mt-1">
            Mark features or personas as "needs review" to add them here
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-5 h-5 text-[#009b87]" />
          <h3 className="text-lg font-semibold text-gray-900">Pending Input Queue</h3>
          <span className="text-sm text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
            {queue.total_count} items
          </span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <button onClick={selectAll} className="text-[#009b87] hover:underline">
            Select all
          </button>
          <span className="text-gray-300">|</span>
          <button onClick={selectNone} className="text-gray-500 hover:underline">
            Clear
          </button>
        </div>
      </div>

      {/* Type summary badges */}
      <div className="flex flex-wrap gap-2 mb-4">
        {Object.entries(queue.by_type).map(([type, count]) => {
          const config = TYPE_CONFIG[type as PendingItemType]
          if (!config) return null
          const Icon = config.icon
          return (
            <button
              key={type}
              onClick={() => toggleType(type)}
              className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium transition-colors ${
                expandedTypes.has(type)
                  ? config.color
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              <Icon className="w-3 h-3" />
              {config.label} ({count})
            </button>
          )
        })}
      </div>

      {/* Grouped items */}
      <div className="space-y-3 max-h-80 overflow-y-auto">
        {Object.entries(groupedItems).map(([type, items]) => {
          const config = TYPE_CONFIG[type as PendingItemType]
          if (!config) return null
          const Icon = config.icon
          const isExpanded = expandedTypes.has(type)

          return (
            <div key={type} className="border border-gray-100 rounded-lg">
              <button
                onClick={() => toggleType(type)}
                className="w-full flex items-center justify-between p-3 hover:bg-gray-50"
              >
                <div className="flex items-center gap-2">
                  <div className={`p-1.5 rounded ${config.color}`}>
                    <Icon className="w-3.5 h-3.5" />
                  </div>
                  <span className="font-medium text-gray-900">{config.label}</span>
                  <span className="text-sm text-gray-500">({items.length})</span>
                </div>
                {isExpanded ? (
                  <ChevronUp className="w-4 h-4 text-gray-400" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-gray-400" />
                )}
              </button>

              {isExpanded && (
                <div className="border-t border-gray-100 p-2 space-y-1">
                  {items.map((item) => (
                    <div
                      key={item.id}
                      className={`flex items-center gap-2 p-2 rounded hover:bg-gray-50 ${
                        selectedIds.has(item.id) ? 'bg-[#009b87]/5' : ''
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={selectedIds.has(item.id)}
                        onChange={() => toggleSelection(item.id)}
                        className="w-4 h-4 text-[#009b87] border-gray-300 rounded focus:ring-[#009b87]"
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {item.title}
                        </p>
                        {item.description && (
                          <p className="text-xs text-gray-500 truncate">
                            {item.description}
                          </p>
                        )}
                      </div>
                      {item.priority === 'high' && (
                        <span className="text-xs px-1.5 py-0.5 bg-red-100 text-red-700 rounded">
                          High
                        </span>
                      )}
                      {onRemoveItem && (
                        <button
                          onClick={() => onRemoveItem(item.id)}
                          className="p-1 text-gray-400 hover:text-red-500"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Generate button */}
      <div className="mt-4 pt-4 border-t border-gray-100">
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-500">
            {selectedIds.size > 0
              ? `${selectedIds.size} items selected`
              : `Generate from all ${queue.total_count} items`}
          </p>
          <button
            onClick={handleGenerate}
            disabled={isGenerating}
            className="inline-flex items-center gap-2 px-4 py-2 bg-[#009b87] text-white text-sm font-medium rounded-lg hover:bg-[#008775] disabled:opacity-50 transition-colors"
          >
            <Sparkles className="w-4 h-4" />
            {isGenerating ? 'Generating...' : 'Generate Client Questions'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default PendingQueue
