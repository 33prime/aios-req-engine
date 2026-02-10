'use client'

import { useState } from 'react'
import { X } from 'lucide-react'

interface WorkflowCreateModalProps {
  open: boolean
  onClose: () => void
  onSave: (data: {
    name: string
    description: string
    owner: string
    state_type: 'current' | 'future'
    frequency_per_week: number
    hourly_rate: number
  }) => void
}

export function WorkflowCreateModal({ open, onClose, onSave }: WorkflowCreateModalProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [owner, setOwner] = useState('')
  const [stateType, setStateType] = useState<'current' | 'future'>('future')
  const [frequency, setFrequency] = useState('')
  const [hourlyRate, setHourlyRate] = useState('')

  if (!open) return null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    onSave({
      name: name.trim(),
      description: description.trim(),
      owner: owner.trim() || '',
      state_type: stateType,
      frequency_per_week: parseFloat(frequency) || 0,
      hourly_rate: parseFloat(hourlyRate) || 0,
    })
    // Reset
    setName('')
    setDescription('')
    setOwner('')
    setStateType('future')
    setFrequency('')
    setHourlyRate('')
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
          <h3 className="text-[15px] font-semibold text-[#37352f]">Create Workflow</h3>
          <button onClick={onClose} className="p-1 rounded hover:bg-gray-100 text-gray-400">
            <X className="w-4 h-4" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div>
            <label className="block text-[12px] font-medium text-gray-600 mb-1">Name *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Client Onboarding"
              className="w-full px-3 py-2 text-[13px] border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-400"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-[12px] font-medium text-gray-600 mb-1">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief description of this workflow..."
              rows={2}
              className="w-full px-3 py-2 text-[13px] border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-400 resize-none"
            />
          </div>
          <div>
            <label className="block text-[12px] font-medium text-gray-600 mb-1">Owner</label>
            <input
              type="text"
              value={owner}
              onChange={(e) => setOwner(e.target.value)}
              placeholder="e.g. Account Manager"
              className="w-full px-3 py-2 text-[13px] border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-400"
            />
          </div>
          <div>
            <label className="block text-[12px] font-medium text-gray-600 mb-2">State Type</label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setStateType('future')}
                className={`flex-1 px-3 py-2 text-[12px] font-medium rounded-md border transition-colors ${
                  stateType === 'future'
                    ? 'bg-teal-50 border-teal-300 text-teal-700'
                    : 'bg-white border-gray-200 text-gray-500 hover:bg-gray-50'
                }`}
              >
                Future State
              </button>
              <button
                type="button"
                onClick={() => setStateType('current')}
                className={`flex-1 px-3 py-2 text-[12px] font-medium rounded-md border transition-colors ${
                  stateType === 'current'
                    ? 'bg-red-50 border-red-300 text-red-700'
                    : 'bg-white border-gray-200 text-gray-500 hover:bg-gray-50'
                }`}
              >
                Current State
              </button>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[12px] font-medium text-gray-600 mb-1">Runs per week</label>
              <input
                type="number"
                value={frequency}
                onChange={(e) => setFrequency(e.target.value)}
                placeholder="0"
                min="0"
                step="0.5"
                className="w-full px-3 py-2 text-[13px] border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-400"
              />
            </div>
            <div>
              <label className="block text-[12px] font-medium text-gray-600 mb-1">Hourly rate ($)</label>
              <input
                type="number"
                value={hourlyRate}
                onChange={(e) => setHourlyRate(e.target.value)}
                placeholder="0"
                min="0"
                step="5"
                className="w-full px-3 py-2 text-[13px] border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-400"
              />
            </div>
          </div>
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
              disabled={!name.trim()}
              className="px-4 py-2 text-[13px] font-medium text-white bg-[#009b87] rounded-md hover:bg-[#008474] transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Create
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
