'use client'

import { useState } from 'react'
import { Download, ChevronDown, ChevronUp, Clock, Users, CheckCircle2 } from 'lucide-react'
import { Card, CardHeader } from '../ui/Card'
import { Button } from '../ui/Button'
import {
  MeetingAgenda,
  exportAgendaAsMarkdown,
} from '@/lib/export-utils'

interface MeetingAgendaDisplayProps {
  agenda: MeetingAgenda
  onClose?: () => void
}

export function MeetingAgendaDisplay({ agenda, onClose }: MeetingAgendaDisplayProps) {
  const [expandedItems, setExpandedItems] = useState<Set<number>>(new Set([0]))

  const toggleItem = (index: number) => {
    const newExpanded = new Set(expandedItems)
    if (newExpanded.has(index)) {
      newExpanded.delete(index)
    } else {
      newExpanded.add(index)
    }
    setExpandedItems(newExpanded)
  }

  const handleExport = () => {
    const content = exportAgendaAsMarkdown(agenda)
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${agenda.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '')}.md`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  const expandAll = () => {
    setExpandedItems(new Set(agenda.agenda.map((_, i) => i)))
  }

  const collapseAll = () => {
    setExpandedItems(new Set())
  }

  return (
    <div className="space-y-4">
      {/* Header Card */}
      <Card className="border-2 border-brand-primary/30 bg-gradient-to-br from-brand-primary-light to-purple-50">
        <CardHeader
          title={
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-green-600" />
              <span>{agenda.title}</span>
            </div>
          }
          actions={
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={handleExport}
                title="Export as Markdown"
              >
                <Download className="h-4 w-4 mr-1" />
                Export
              </Button>
              {onClose && (
                <Button size="sm" variant="outline" onClick={onClose}>
                  Close
                </Button>
              )}
            </div>
          }
        />

        <div className="px-6 pb-6 space-y-4">
          {/* Pre-read / Summary */}
          {agenda.pre_read && (
            <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
              <p className="text-sm font-medium text-yellow-800 mb-1">Pre-read for client:</p>
              <p className="text-sm text-yellow-700">{agenda.pre_read}</p>
            </div>
          )}

          {/* Stats */}
          <div className="flex gap-6 text-sm">
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-gray-500" />
              <span className="font-medium">{agenda.duration_estimate}</span>
            </div>
            <div className="flex items-center gap-2">
              <Users className="h-4 w-4 text-gray-500" />
              <span className="font-medium">{agenda.confirmation_count} confirmations</span>
            </div>
            <div className="text-gray-600">{agenda.agenda.length} agenda items</div>
          </div>
        </div>
      </Card>

      {/* Expand/Collapse Controls */}
      <div className="flex justify-end gap-2">
        <Button size="sm" variant="ghost" onClick={expandAll}>
          Expand All
        </Button>
        <Button size="sm" variant="ghost" onClick={collapseAll}>
          Collapse All
        </Button>
      </div>

      {/* Agenda Items */}
      <div className="space-y-3">
        {agenda.agenda.map((item, index) => {
          const isExpanded = expandedItems.has(index)

          return (
            <Card key={index} className="overflow-hidden">
              <div
                className="flex items-start justify-between p-4 cursor-pointer hover:bg-gray-50 transition-colors"
                onClick={() => toggleItem(index)}
              >
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <span className="flex items-center justify-center w-8 h-8 rounded-full bg-brand-primary text-white text-sm font-semibold">
                      {index + 1}
                    </span>
                    <div>
                      <h3 className="font-semibold text-gray-900">{item.topic}</h3>
                      <p className="text-sm text-gray-500">{item.time_minutes} minutes</p>
                    </div>
                  </div>
                </div>
                <button className="p-1 hover:bg-gray-100 rounded">
                  {isExpanded ? (
                    <ChevronUp className="h-5 w-5 text-gray-500" />
                  ) : (
                    <ChevronDown className="h-5 w-5 text-gray-500" />
                  )}
                </button>
              </div>

              {isExpanded && (
                <div className="px-4 pb-4 space-y-4 border-t bg-gray-50/50">
                  {/* Description */}
                  {item.description && (
                    <div className="pt-4">
                      <h4 className="text-sm font-semibold text-gray-700 mb-2">
                        Discussion Points
                      </h4>
                      <p className="text-sm text-gray-600">{item.description}</p>
                    </div>
                  )}

                  {/* Related Confirmations */}
                  {item.confirmation_ids && item.confirmation_ids.length > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold text-gray-700 mb-1">
                        Related Confirmations
                      </h4>
                      <p className="text-sm text-gray-500">
                        {item.confirmation_ids.length} confirmation
                        {item.confirmation_ids.length !== 1 ? 's' : ''} grouped in this
                        topic
                      </p>
                    </div>
                  )}
                </div>
              )}
            </Card>
          )
        })}
      </div>
    </div>
  )
}
