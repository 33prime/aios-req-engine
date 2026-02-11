'use client'

import { useState } from 'react'
import { X } from 'lucide-react'

interface StakeholderCreateModalProps {
  open: boolean
  projects: { id: string; name: string }[]
  onClose: () => void
  onSave: (projectId: string, data: {
    name: string
    role?: string
    email?: string
    organization?: string
    stakeholder_type?: string
    influence_level?: string
    notes?: string
  }) => void
}

export function StakeholderCreateModal({ open, projects, onClose, onSave }: StakeholderCreateModalProps) {
  const [name, setName] = useState('')
  const [role, setRole] = useState('')
  const [email, setEmail] = useState('')
  const [organization, setOrganization] = useState('')
  const [stakeholderType, setStakeholderType] = useState('influencer')
  const [influenceLevel, setInfluenceLevel] = useState('medium')
  const [notes, setNotes] = useState('')
  const [projectId, setProjectId] = useState(projects[0]?.id || '')
  const [saving, setSaving] = useState(false)

  if (!open) return null

  const handleSave = async () => {
    if (!name.trim() || !projectId) return
    setSaving(true)
    try {
      await onSave(projectId, {
        name: name.trim(),
        role: role.trim() || undefined,
        email: email.trim() || undefined,
        organization: organization.trim() || undefined,
        stakeholder_type: stakeholderType,
        influence_level: influenceLevel,
        notes: notes.trim() || undefined,
      })
      // Reset form
      setName(''); setRole(''); setEmail(''); setOrganization('')
      setStakeholderType('influencer'); setInfluenceLevel('medium'); setNotes('')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <div className="relative bg-white rounded-lg shadow-xl w-full max-w-md mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <h2 className="text-[16px] font-semibold text-[#37352f]">Add Person</h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-gray-100 transition-colors">
            <X className="w-4 h-4 text-gray-400" />
          </button>
        </div>

        <div className="px-5 py-4 space-y-3">
          {/* Project */}
          <div>
            <label className="block text-[12px] font-medium text-[rgba(55,53,47,0.65)] mb-1">Project *</label>
            <select
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              className="w-full px-3 py-1.5 text-[13px] bg-white border border-gray-200 rounded-md focus:outline-none focus:ring-1 focus:ring-[#009b87]"
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>

          {/* Name */}
          <div>
            <label className="block text-[12px] font-medium text-[rgba(55,53,47,0.65)] mb-1">Name *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Full name"
              className="w-full px-3 py-1.5 text-[13px] border border-gray-200 rounded-md focus:outline-none focus:ring-1 focus:ring-[#009b87]"
            />
          </div>

          {/* Email + Role */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[12px] font-medium text-[rgba(55,53,47,0.65)] mb-1">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="email@example.com"
                className="w-full px-3 py-1.5 text-[13px] border border-gray-200 rounded-md focus:outline-none focus:ring-1 focus:ring-[#009b87]"
              />
            </div>
            <div>
              <label className="block text-[12px] font-medium text-[rgba(55,53,47,0.65)] mb-1">Role</label>
              <input
                type="text"
                value={role}
                onChange={(e) => setRole(e.target.value)}
                placeholder="CTO, PM, etc."
                className="w-full px-3 py-1.5 text-[13px] border border-gray-200 rounded-md focus:outline-none focus:ring-1 focus:ring-[#009b87]"
              />
            </div>
          </div>

          {/* Organization */}
          <div>
            <label className="block text-[12px] font-medium text-[rgba(55,53,47,0.65)] mb-1">Organization</label>
            <input
              type="text"
              value={organization}
              onChange={(e) => setOrganization(e.target.value)}
              placeholder="Company or department"
              className="w-full px-3 py-1.5 text-[13px] border border-gray-200 rounded-md focus:outline-none focus:ring-1 focus:ring-[#009b87]"
            />
          </div>

          {/* Type + Influence */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[12px] font-medium text-[rgba(55,53,47,0.65)] mb-1">Type</label>
              <select
                value={stakeholderType}
                onChange={(e) => setStakeholderType(e.target.value)}
                className="w-full px-3 py-1.5 text-[13px] bg-white border border-gray-200 rounded-md focus:outline-none focus:ring-1 focus:ring-[#009b87]"
              >
                <option value="champion">Champion</option>
                <option value="sponsor">Sponsor</option>
                <option value="blocker">Blocker</option>
                <option value="influencer">Influencer</option>
                <option value="end_user">End User</option>
              </select>
            </div>
            <div>
              <label className="block text-[12px] font-medium text-[rgba(55,53,47,0.65)] mb-1">Influence</label>
              <select
                value={influenceLevel}
                onChange={(e) => setInfluenceLevel(e.target.value)}
                className="w-full px-3 py-1.5 text-[13px] bg-white border border-gray-200 rounded-md focus:outline-none focus:ring-1 focus:ring-[#009b87]"
              >
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="block text-[12px] font-medium text-[rgba(55,53,47,0.65)] mb-1">Notes</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              placeholder="Additional context..."
              className="w-full px-3 py-1.5 text-[13px] border border-gray-200 rounded-md focus:outline-none focus:ring-1 focus:ring-[#009b87] resize-none"
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
            disabled={!name.trim() || !projectId || saving}
            className="px-3 py-1.5 text-[13px] font-medium text-white bg-[#009b87] rounded-md hover:bg-[#008474] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? 'Saving...' : 'Add Person'}
          </button>
        </div>
      </div>
    </div>
  )
}
