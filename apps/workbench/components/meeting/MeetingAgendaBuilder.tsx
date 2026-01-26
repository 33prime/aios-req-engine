'use client'

import { useState } from 'react'
import { Calendar, CheckSquare, X, AlertCircle } from 'lucide-react'
import { Card, CardHeader } from '../ui/Card'
import { Button } from '../ui/Button'
import type { Confirmation } from '@/types/api'

interface MeetingAgendaBuilderProps {
  confirmations: Confirmation[]
  onGenerate: (confirmationIds: string[]) => Promise<void>
  onClose: () => void
}

export function MeetingAgendaBuilder({
  confirmations,
  onGenerate,
  onClose,
}: MeetingAgendaBuilderProps) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [generating, setGenerating] = useState(false)

  // Filter to only open or queued confirmations
  const availableConfirmations = confirmations.filter(
    (c) => c.status === 'open' || c.status === 'queued'
  )

  const toggleSelection = (confirmationId: string) => {
    const newSelected = new Set(selectedIds)
    if (newSelected.has(confirmationId)) {
      newSelected.delete(confirmationId)
    } else {
      newSelected.add(confirmationId)
    }
    setSelectedIds(newSelected)
  }

  const selectAll = () => {
    setSelectedIds(new Set(availableConfirmations.map((c) => c.id)))
  }

  const deselectAll = () => {
    setSelectedIds(new Set())
  }

  const handleGenerate = async () => {
    if (selectedIds.size === 0) return

    try {
      setGenerating(true)
      await onGenerate(Array.from(selectedIds))
    } finally {
      setGenerating(false)
    }
  }

  // Estimate total time
  const estimatedMinutes = selectedIds.size * 8 // ~8 minutes per confirmation

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-3xl w-full max-h-[80vh] overflow-hidden flex flex-col">
        <Card className="flex-1 flex flex-col overflow-hidden">
          <CardHeader
            title={
              <div className="flex items-center gap-2">
                <Calendar className="h-5 w-5 text-brand-primary" />
                <span>Generate Meeting Agenda</span>
              </div>
            }
            actions={
              <button
                onClick={onClose}
                className="text-ui-supportText hover:text-ui-bodyText text-2xl leading-none"
                disabled={generating}
              >
                <X className="h-6 w-6" />
              </button>
            }
          />

          <div className="flex-1 overflow-y-auto px-6 pb-6">
            {/* Info Banner */}
            <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg flex gap-3">
              <AlertCircle className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-blue-900">
                <p className="font-medium mb-1">Select confirmations for your client meeting</p>
                <p className="text-blue-700">
                  The AI will intelligently group related items, suggest discussion topics, and
                  estimate time for each section.
                </p>
              </div>
            </div>

            {/* Selection Controls */}
            <div className="mb-4 flex items-center justify-between">
              <div className="text-sm text-gray-600">
                {selectedIds.size} of {availableConfirmations.length} selected
                {selectedIds.size > 0 && (
                  <span className="ml-2 text-brand-primary font-medium">
                    (~{estimatedMinutes} min meeting)
                  </span>
                )}
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="ghost" onClick={selectAll}>
                  Select All
                </Button>
                <Button size="sm" variant="ghost" onClick={deselectAll}>
                  Deselect All
                </Button>
              </div>
            </div>

            {/* Confirmations List */}
            {availableConfirmations.length === 0 ? (
              <div className="text-center py-8">
                <CheckSquare className="h-12 w-12 text-gray-300 mx-auto mb-3" />
                <p className="text-gray-500">No confirmations available for meeting</p>
                <p className="text-sm text-gray-400 mt-1">
                  Only open or queued confirmations can be included
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {availableConfirmations.map((confirmation) => {
                  const isSelected = selectedIds.has(confirmation.id)

                  return (
                    <div
                      key={confirmation.id}
                      className={`border rounded-lg p-3 cursor-pointer transition-all ${
                        isSelected
                          ? 'border-brand-primary bg-brand-primary/5'
                          : 'border-gray-200 hover:border-gray-300 bg-white'
                      }`}
                      onClick={() => toggleSelection(confirmation.id)}
                    >
                      <div className="flex items-start gap-3">
                        {/* Checkbox */}
                        <div className="pt-0.5">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleSelection(confirmation.id)}
                            className="h-4 w-4 text-brand-primary border-gray-300 rounded focus:ring-brand-primary cursor-pointer"
                            onClick={(e) => e.stopPropagation()}
                          />
                        </div>

                        {/* Content */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between gap-2 mb-1">
                            <h4 className="font-medium text-gray-900 text-sm">
                              {confirmation.title}
                            </h4>
                            <span
                              className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium flex-shrink-0 ${
                                confirmation.kind === 'vp'
                                  ? 'bg-purple-100 text-purple-800'
                                  : confirmation.kind === 'feature'
                                  ? 'bg-blue-100 text-blue-800'
                                  : confirmation.kind === 'persona'
                                  ? 'bg-green-100 text-green-800'
                                  : 'bg-orange-100 text-orange-800'
                              }`}
                            >
                              {confirmation.kind.toUpperCase()}
                            </span>
                          </div>
                          {confirmation.ask && (
                            <p className="text-sm text-gray-600 line-clamp-2">
                              {confirmation.ask}
                            </p>
                          )}
                          <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                            <span className="capitalize">{confirmation.status}</span>
                            <span className="capitalize">Priority: {confirmation.priority}</span>
                            {confirmation.evidence.length > 0 && (
                              <span>{confirmation.evidence.length} evidence</span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Footer Actions */}
          <div className="border-t border-gray-200 p-4 bg-gray-50 flex items-center justify-between">
            <div className="text-sm text-gray-600">
              {selectedIds.size > 0 ? (
                <>
                  <strong>{selectedIds.size}</strong> confirmation
                  {selectedIds.size !== 1 ? 's' : ''} selected
                </>
              ) : (
                'Select confirmations to generate agenda'
              )}
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={onClose} disabled={generating}>
                Cancel
              </Button>
              <Button
                onClick={handleGenerate}
                disabled={selectedIds.size === 0 || generating}
              >
                {generating ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Generating...
                  </>
                ) : (
                  <>
                    <Calendar className="h-4 w-4 mr-2" />
                    Generate Agenda
                  </>
                )}
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}
