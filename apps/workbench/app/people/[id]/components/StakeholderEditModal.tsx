'use client'

import { useState, useEffect } from 'react'
import { X, Loader2 } from 'lucide-react'
import type { StakeholderDetail } from '@/types/workspace'

interface StakeholderEditModalProps {
  open: boolean
  onClose: () => void
  onSave: (data: Record<string, string>) => Promise<void>
  stakeholder: StakeholderDetail
}

export function StakeholderEditModal({ open, onClose, onSave, stakeholder }: StakeholderEditModalProps) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [role, setRole] = useState('')
  const [organization, setOrganization] = useState('')
  const [stakeholderType, setStakeholderType] = useState('')
  const [influenceLevel, setInfluenceLevel] = useState('')
  const [linkedinProfile, setLinkedinProfile] = useState('')
  const [notes, setNotes] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (open && stakeholder) {
      setName(stakeholder.name || '')
      setEmail(stakeholder.email || '')
      setRole(stakeholder.role || '')
      setOrganization(stakeholder.organization || '')
      setStakeholderType(stakeholder.stakeholder_type || 'champion')
      setInfluenceLevel(stakeholder.influence_level || 'medium')
      setLinkedinProfile(stakeholder.linkedin_profile || '')
      setNotes(stakeholder.notes || '')
    }
  }, [open, stakeholder])

  if (!open) return null

  const handleSave = async () => {
    if (!name.trim() || saving) return
    setSaving(true)
    try {
      await onSave({
        name: name.trim(),
        email: email.trim(),
        role: role.trim(),
        organization: organization.trim(),
        stakeholder_type: stakeholderType,
        influence_level: influenceLevel,
        linkedin_profile: linkedinProfile.trim(),
        notes: notes.trim(),
      })
      onClose()
    } catch (err) {
      console.error('Failed to update stakeholder:', err)
    } finally {
      setSaving(false)
    }
  }

  const inputClass = "w-full px-3 py-1.5 text-[13px] border border-gray-200 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-primary/20 transition-colors"

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white rounded-lg shadow-xl w-full max-w-md mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <h2 className="text-[16px] font-semibold text-[#37352f]">Edit Stakeholder</h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-gray-100 transition-colors">
            <X className="w-4 h-4 text-gray-400" />
          </button>
        </div>

        <div className="px-5 py-4 space-y-3">
          <div>
            <label className="block text-[12px] font-medium text-[#666666] mb-1">
              Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Full name"
              className={inputClass}
              autoFocus
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[12px] font-medium text-[#666666] mb-1">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="email@example.com"
                className={inputClass}
              />
            </div>
            <div>
              <label className="block text-[12px] font-medium text-[#666666] mb-1">Role</label>
              <input
                type="text"
                value={role}
                onChange={(e) => setRole(e.target.value)}
                placeholder="CTO, PM, etc."
                className={inputClass}
              />
            </div>
          </div>

          <div>
            <label className="block text-[12px] font-medium text-[#666666] mb-1">Organization</label>
            <input
              type="text"
              value={organization}
              onChange={(e) => setOrganization(e.target.value)}
              placeholder="Company or department"
              className={inputClass}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[12px] font-medium text-[#666666] mb-1">Type</label>
              <select
                value={stakeholderType}
                onChange={(e) => setStakeholderType(e.target.value)}
                className={inputClass + ' bg-white cursor-pointer'}
              >
                <option value="champion">Champion</option>
                <option value="sponsor">Sponsor</option>
                <option value="blocker">Blocker</option>
                <option value="influencer">Influencer</option>
                <option value="end_user">End User</option>
              </select>
            </div>
            <div>
              <label className="block text-[12px] font-medium text-[#666666] mb-1">Influence</label>
              <select
                value={influenceLevel}
                onChange={(e) => setInfluenceLevel(e.target.value)}
                className={inputClass + ' bg-white cursor-pointer'}
              >
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-[12px] font-medium text-[#666666] mb-1">LinkedIn Profile</label>
            <input
              type="url"
              value={linkedinProfile}
              onChange={(e) => setLinkedinProfile(e.target.value)}
              placeholder="https://linkedin.com/in/..."
              className={inputClass}
            />
          </div>

          <div>
            <label className="block text-[12px] font-medium text-[#666666] mb-1">Notes</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              placeholder="Additional context..."
              className={inputClass + ' resize-none'}
            />
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-gray-100">
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-[13px] font-medium text-gray-600 bg-white border border-gray-200 rounded-md hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!name.trim() || saving}
            className="px-3 py-1.5 text-[13px] font-medium text-white bg-[#009b87] rounded-md hover:bg-[#008474] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  )
}
