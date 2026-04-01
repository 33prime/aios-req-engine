'use client'

import { useState, useEffect } from 'react'
import { X, Loader2 } from 'lucide-react'
import type { ClientDetail } from '@/types/workspace'

interface ClientEditModalProps {
  open: boolean
  onClose: () => void
  onSave: (data: Record<string, string>) => Promise<void>
  client: ClientDetail
}

const STAGES = ['startup', 'growth', 'enterprise', 'government', 'non-profit']
const SIZES = ['1-10', '11-50', '51-200', '201-1000', '1001-5000', '5000+']

export function ClientEditModal({ open, onClose, onSave, client }: ClientEditModalProps) {
  const [name, setName] = useState('')
  const [website, setWebsite] = useState('')
  const [industry, setIndustry] = useState('')
  const [stage, setStage] = useState('')
  const [size, setSize] = useState('')
  const [description, setDescription] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (open && client) {
      setName(client.name || '')
      setWebsite(client.website || '')
      setIndustry(client.industry || '')
      setStage(client.stage || '')
      setSize(client.size || '')
      setDescription(client.description || '')
    }
  }, [open, client])

  if (!open) return null

  const handleSave = async () => {
    if (!name.trim() || saving) return
    setSaving(true)
    try {
      await onSave({
        name: name.trim(),
        website: website.trim(),
        industry: industry.trim(),
        stage: stage.trim(),
        size: size.trim(),
        description: description.trim(),
      })
      onClose()
    } catch (err) {
      console.error('Failed to update client:', err)
    } finally {
      setSaving(false)
    }
  }

  const inputClass = "w-full px-3 py-2 text-[13px] border border-border rounded-xl focus:outline-none focus:border-brand-primary focus:ring-1 focus:ring-brand-primary/20 transition-colors"

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white rounded-xl shadow-xl w-full max-w-[520px] mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h2 className="text-[16px] font-semibold text-[#333]">Edit Client</h2>
          <button
            onClick={onClose}
            className="p-1.5 text-[#999] hover:text-[#666] hover:bg-[#F0F0F0] rounded-lg transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="px-6 py-4 space-y-4 max-h-[60vh] overflow-y-auto">
          <div>
            <label className="block text-[12px] font-medium text-[#666] mb-1.5">
              Company Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Acme Corp"
              className={inputClass}
              autoFocus
            />
          </div>

          <div>
            <label className="block text-[12px] font-medium text-[#666] mb-1.5">Website</label>
            <input
              type="url"
              value={website}
              onChange={(e) => setWebsite(e.target.value)}
              placeholder="https://example.com"
              className={inputClass}
            />
          </div>

          <div>
            <label className="block text-[12px] font-medium text-[#666] mb-1.5">Industry</label>
            <input
              type="text"
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              placeholder="e.g. Technology, Healthcare, Finance"
              className={inputClass}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[12px] font-medium text-[#666] mb-1.5">Stage</label>
              <select
                value={stage}
                onChange={(e) => setStage(e.target.value)}
                className={inputClass + ' appearance-none cursor-pointer'}
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
                className={inputClass + ' appearance-none cursor-pointer'}
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

          <div>
            <label className="block text-[12px] font-medium text-[#666] mb-1.5">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief description of the client organization..."
              rows={3}
              className={inputClass + ' resize-none'}
            />
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-border">
          <button
            onClick={onClose}
            className="px-4 py-2 text-[13px] font-medium text-[#666] bg-[#F0F0F0] rounded-xl hover:bg-border transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!name.trim() || saving}
            className="px-4 py-2 text-[13px] font-medium text-white bg-brand-primary rounded-xl hover:bg-brand-primary-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  )
}
