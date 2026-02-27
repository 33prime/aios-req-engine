'use client'

import { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import type { AutomationLevel } from '@/types/workspace'

interface WorkflowStepEditorProps {
  open: boolean
  onClose: () => void
  stateType: 'current' | 'future'
  onSave: (data: {
    label: string
    description: string
    time_minutes: number | undefined
    automation_level: AutomationLevel
    operation_type: string | undefined
    pain_description: string
    benefit_description: string
  }) => void
  initialData?: {
    label?: string
    description?: string
    time_minutes?: number | null
    automation_level?: AutomationLevel
    operation_type?: string | null
    pain_description?: string | null
    benefit_description?: string | null
  }
}

const OPERATION_TYPES = [
  { value: '', label: 'None' },
  { value: 'create', label: 'Create' },
  { value: 'read', label: 'Read' },
  { value: 'update', label: 'Update' },
  { value: 'delete', label: 'Delete' },
  { value: 'validate', label: 'Validate' },
  { value: 'notify', label: 'Notify' },
  { value: 'transfer', label: 'Transfer' },
]

export function WorkflowStepEditor({
  open,
  onClose,
  stateType,
  onSave,
  initialData,
}: WorkflowStepEditorProps) {
  const [label, setLabel] = useState('')
  const [description, setDescription] = useState('')
  const [timeMinutes, setTimeMinutes] = useState('')
  const [automationLevel, setAutomationLevel] = useState<AutomationLevel>('manual')
  const [operationType, setOperationType] = useState('')
  const [painDescription, setPainDescription] = useState('')
  const [benefitDescription, setBenefitDescription] = useState('')

  // Reset all state from initialData (or defaults) when modal opens
  useEffect(() => {
    if (open) {
      setLabel(initialData?.label || '')
      setDescription(initialData?.description || '')
      setTimeMinutes(initialData?.time_minutes != null ? String(initialData.time_minutes) : '')
      setAutomationLevel(initialData?.automation_level || 'manual')
      setOperationType(initialData?.operation_type || '')
      setPainDescription(initialData?.pain_description || '')
      setBenefitDescription(initialData?.benefit_description || '')
    }
  }, [open, initialData])

  if (!open) return null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!label.trim()) return
    onSave({
      label: label.trim(),
      description: description.trim(),
      time_minutes: timeMinutes ? parseFloat(timeMinutes) : undefined,
      automation_level: automationLevel,
      operation_type: operationType || undefined,
      pain_description: painDescription.trim(),
      benefit_description: benefitDescription.trim(),
    })
  }

  const isCurrent = stateType === 'current'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
          <h3 className="text-[15px] font-semibold text-[#37352f]">
            {initialData ? 'Edit Step' : 'Add Step'}{' '}
            <span className={`text-[12px] font-normal ${isCurrent ? 'text-[#666666]' : 'text-brand-primary'}`}>
              ({isCurrent ? 'Current' : 'Future'})
            </span>
          </h3>
          <button onClick={onClose} className="p-1 rounded hover:bg-gray-100 text-gray-400">
            <X className="w-4 h-4" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-5 space-y-3">
          <div>
            <label className="block text-[12px] font-medium text-gray-600 mb-1">Label *</label>
            <input
              type="text"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="e.g. Manual data entry"
              className="w-full px-3 py-2 text-[13px] border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-primary/30 focus:border-brand-primary"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-[12px] font-medium text-gray-600 mb-1">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What happens in this step..."
              rows={2}
              className="w-full px-3 py-2 text-[13px] border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-primary/30 focus:border-brand-primary resize-none"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[12px] font-medium text-gray-600 mb-1">Time (minutes)</label>
              <input
                type="number"
                value={timeMinutes}
                onChange={(e) => setTimeMinutes(e.target.value)}
                placeholder="0"
                min="0"
                step="0.5"
                className="w-full px-3 py-2 text-[13px] border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-primary/30 focus:border-brand-primary"
              />
            </div>
            <div>
              <label className="block text-[12px] font-medium text-gray-600 mb-1">Automation</label>
              <select
                value={automationLevel}
                onChange={(e) => setAutomationLevel(e.target.value as AutomationLevel)}
                className="w-full px-3 py-2 text-[13px] border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-primary/30 focus:border-brand-primary bg-white"
              >
                <option value="manual">Manual</option>
                <option value="semi_automated">Semi-automated</option>
                <option value="fully_automated">Fully automated</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-[12px] font-medium text-gray-600 mb-1">Operation Type</label>
            <select
              value={operationType}
              onChange={(e) => setOperationType(e.target.value)}
              className="w-full px-3 py-2 text-[13px] border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-primary/30 focus:border-brand-primary bg-white"
            >
              {OPERATION_TYPES.map((op) => (
                <option key={op.value} value={op.value}>
                  {op.label}
                </option>
              ))}
            </select>
          </div>
          {isCurrent ? (
            <div>
              <label className="block text-[12px] font-medium text-gray-600 mb-1">Pain Description</label>
              <textarea
                value={painDescription}
                onChange={(e) => setPainDescription(e.target.value)}
                placeholder="What's painful about this step today..."
                rows={2}
                className="w-full px-3 py-2 text-[13px] border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-300/40 focus:border-gray-300 resize-none"
              />
            </div>
          ) : (
            <div>
              <label className="block text-[12px] font-medium text-gray-600 mb-1">Benefit Description</label>
              <textarea
                value={benefitDescription}
                onChange={(e) => setBenefitDescription(e.target.value)}
                placeholder="How this step improves things..."
                rows={2}
                className="w-full px-3 py-2 text-[13px] border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary resize-none"
              />
            </div>
          )}
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-[13px] font-medium text-gray-600 bg-white border border-gray-200 rounded-md hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!label.trim()}
              className="px-4 py-2 text-[13px] font-medium text-white bg-brand-primary rounded-md hover:bg-[#25785A] transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {initialData ? 'Save' : 'Add Step'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
