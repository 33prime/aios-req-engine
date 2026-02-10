'use client'

import { useState } from 'react'
import { X } from 'lucide-react'

interface DataEntityCreateModalProps {
  open: boolean
  onClose: () => void
  onSave: (data: {
    name: string
    description: string
    entity_category: 'domain' | 'reference' | 'transactional' | 'system'
  }) => void
}

const CATEGORIES = [
  { value: 'domain', label: 'Domain', description: 'Core business objects' },
  { value: 'reference', label: 'Reference', description: 'Lookup/config data' },
  { value: 'transactional', label: 'Transactional', description: 'Event/transaction records' },
  { value: 'system', label: 'System', description: 'Internal system data' },
] as const

export function DataEntityCreateModal({ open, onClose, onSave }: DataEntityCreateModalProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState<'domain' | 'reference' | 'transactional' | 'system'>('domain')

  if (!open) return null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    onSave({
      name: name.trim(),
      description: description.trim(),
      entity_category: category,
    })
    setName('')
    setDescription('')
    setCategory('domain')
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
          <h3 className="text-[15px] font-semibold text-[#37352f]">Create Data Entity</h3>
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
              placeholder="e.g. Patient Record, Invoice, Work Order"
              className="w-full px-3 py-2 text-[13px] border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-400"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-[12px] font-medium text-gray-600 mb-1">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What this data entity represents..."
              rows={2}
              className="w-full px-3 py-2 text-[13px] border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-400 resize-none"
            />
          </div>
          <div>
            <label className="block text-[12px] font-medium text-gray-600 mb-2">Category</label>
            <div className="grid grid-cols-2 gap-2">
              {CATEGORIES.map((cat) => (
                <button
                  key={cat.value}
                  type="button"
                  onClick={() => setCategory(cat.value)}
                  className={`px-3 py-2 text-left rounded-md border transition-colors ${
                    category === cat.value
                      ? 'bg-teal-50 border-teal-300 text-teal-700'
                      : 'bg-white border-gray-200 text-gray-500 hover:bg-gray-50'
                  }`}
                >
                  <span className="block text-[12px] font-medium">{cat.label}</span>
                  <span className="block text-[10px] opacity-70">{cat.description}</span>
                </button>
              ))}
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
