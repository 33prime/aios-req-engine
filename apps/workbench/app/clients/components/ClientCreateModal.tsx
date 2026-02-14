'use client'

import { useState } from 'react'
import { X } from 'lucide-react'
import type { ClientCreatePayload } from '@/types/workspace'

interface ClientCreateModalProps {
  open: boolean
  onClose: () => void
  onSave: (data: ClientCreatePayload) => void
}

const STAGES = ['startup', 'growth', 'enterprise', 'government', 'non-profit']
const SIZES = ['1-10', '11-50', '51-200', '201-1000', '1001-5000', '5000+']

export function ClientCreateModal({ open, onClose, onSave }: ClientCreateModalProps) {
  const [name, setName] = useState('')
  const [website, setWebsite] = useState('')
  const [industry, setIndustry] = useState('')
  const [stage, setStage] = useState('')
  const [size, setSize] = useState('')
  const [description, setDescription] = useState('')
  const [saving, setSaving] = useState(false)

  if (!open) return null

  const handleSave = async () => {
    if (!name.trim()) return
    setSaving(true)
    try {
      const payload: ClientCreatePayload = { name: name.trim() }
      if (website.trim()) payload.website = website.trim()
      if (industry.trim()) payload.industry = industry.trim()
      if (stage) payload.stage = stage
      if (size) payload.size = size
      if (description.trim()) payload.description = description.trim()
      onSave(payload)
      // Reset
      setName('')
      setWebsite('')
      setIndustry('')
      setStage('')
      setSize('')
      setDescription('')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Overlay */}
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-[520px] mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#E5E5E5]">
          <h2 className="text-[16px] font-semibold text-[#333]">Add Client</h2>
          <button
            onClick={onClose}
            className="p-1.5 text-[#999] hover:text-[#666] hover:bg-[#F0F0F0] rounded-lg transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-4 space-y-4 max-h-[60vh] overflow-y-auto">
          {/* Name */}
          <div>
            <label className="block text-[12px] font-medium text-[#666] mb-1.5">
              Company Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Acme Corp"
              className="w-full px-3 py-2 text-[13px] border border-[#E5E5E5] rounded-xl focus:outline-none focus:border-[#3FAF7A] focus:ring-1 focus:ring-[#3FAF7A]/20 transition-colors"
              autoFocus
            />
          </div>

          {/* Website */}
          <div>
            <label className="block text-[12px] font-medium text-[#666] mb-1.5">Website</label>
            <input
              type="url"
              value={website}
              onChange={(e) => setWebsite(e.target.value)}
              placeholder="https://example.com"
              className="w-full px-3 py-2 text-[13px] border border-[#E5E5E5] rounded-xl focus:outline-none focus:border-[#3FAF7A] focus:ring-1 focus:ring-[#3FAF7A]/20 transition-colors"
            />
          </div>

          {/* Industry */}
          <div>
            <label className="block text-[12px] font-medium text-[#666] mb-1.5">Industry</label>
            <input
              type="text"
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              placeholder="e.g. Technology, Healthcare, Finance"
              className="w-full px-3 py-2 text-[13px] border border-[#E5E5E5] rounded-xl focus:outline-none focus:border-[#3FAF7A] focus:ring-1 focus:ring-[#3FAF7A]/20 transition-colors"
            />
          </div>

          {/* Stage + Size row */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[12px] font-medium text-[#666] mb-1.5">Stage</label>
              <select
                value={stage}
                onChange={(e) => setStage(e.target.value)}
                className="w-full px-3 py-2 text-[13px] border border-[#E5E5E5] rounded-xl focus:outline-none focus:border-[#3FAF7A] transition-colors appearance-none cursor-pointer"
              >
                <option value="">Select...</option>
                {STAGES.map((s) => (
                  <option key={s} value={s}>
                    {s.charAt(0).toUpperCase() + s.slice(1).replace('-', ' ')}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-[12px] font-medium text-[#666] mb-1.5">Size</label>
              <select
                value={size}
                onChange={(e) => setSize(e.target.value)}
                className="w-full px-3 py-2 text-[13px] border border-[#E5E5E5] rounded-xl focus:outline-none focus:border-[#3FAF7A] transition-colors appearance-none cursor-pointer"
              >
                <option value="">Select...</option>
                {SIZES.map((s) => (
                  <option key={s} value={s}>
                    {s} employees
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="block text-[12px] font-medium text-[#666] mb-1.5">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief description of the client organization..."
              rows={3}
              className="w-full px-3 py-2 text-[13px] border border-[#E5E5E5] rounded-xl focus:outline-none focus:border-[#3FAF7A] focus:ring-1 focus:ring-[#3FAF7A]/20 transition-colors resize-none"
            />
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-[#E5E5E5]">
          <button
            onClick={onClose}
            className="px-4 py-2 text-[13px] font-medium text-[#666] bg-[#F0F0F0] rounded-xl hover:bg-[#E5E5E5] transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!name.trim() || saving}
            className="px-4 py-2 text-[13px] font-medium text-white bg-[#3FAF7A] rounded-xl hover:bg-[#25785A] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? 'Creating...' : 'Create Client'}
          </button>
        </div>
      </div>
    </div>
  )
}
