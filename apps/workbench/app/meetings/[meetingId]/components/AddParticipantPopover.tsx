'use client'

import { useState, useEffect, useCallback } from 'react'
import { Plus, Search, X, Loader2 } from 'lucide-react'
import { Popover, PopoverTrigger, PopoverContent } from '@/components/ui/popover'
import { listProjectStakeholders, createStakeholder, updateMeeting } from '@/lib/api'
import type { StakeholderDetail, StakeholderType, StakeholderCreatePayload } from '@/types/workspace'

interface AddParticipantPopoverProps {
  projectId: string
  meetingId: string
  existingIds: string[]
  onAdded: () => void
}

const STAKEHOLDER_TYPES: { value: StakeholderType; label: string }[] = [
  { value: 'champion', label: 'Champion' },
  { value: 'sponsor', label: 'Sponsor' },
  { value: 'influencer', label: 'Influencer' },
  { value: 'end_user', label: 'End User' },
  { value: 'blocker', label: 'Blocker' },
]

export function AddParticipantPopover({ projectId, meetingId, existingIds, onAdded }: AddParticipantPopoverProps) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [allStakeholders, setAllStakeholders] = useState<StakeholderDetail[]>([])
  const [loading, setLoading] = useState(false)
  const [adding, setAdding] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [newEmail, setNewEmail] = useState('')
  const [newRole, setNewRole] = useState('')
  const [newOrg, setNewOrg] = useState('')
  const [newType, setNewType] = useState<StakeholderType>('end_user')

  const loadStakeholders = useCallback(async () => {
    try {
      setLoading(true)
      const { stakeholders } = await listProjectStakeholders(projectId)
      setAllStakeholders(stakeholders)
    } catch (error) {
      console.error('Failed to load stakeholders:', error)
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    if (open) {
      loadStakeholders()
      setSearch('')
      setShowCreate(false)
    }
  }, [open, loadStakeholders])

  const available = allStakeholders.filter(
    (s) =>
      !existingIds.includes(s.id) &&
      s.name.toLowerCase().includes(search.toLowerCase())
  )

  const handleAddExisting = async (stakeholderId: string) => {
    try {
      setAdding(true)
      await updateMeeting(meetingId, {
        stakeholder_ids: [...existingIds, stakeholderId],
      })
      onAdded()
      setOpen(false)
    } catch (error) {
      console.error('Failed to add participant:', error)
    } finally {
      setAdding(false)
    }
  }

  const handleCreateAndAdd = async () => {
    if (!newName.trim()) return
    try {
      setAdding(true)
      const payload: StakeholderCreatePayload = {
        name: newName.trim(),
        stakeholder_type: newType,
      }
      if (newEmail.trim()) payload.email = newEmail.trim()
      if (newRole.trim()) payload.role = newRole.trim()
      if (newOrg.trim()) payload.organization = newOrg.trim()

      const created = await createStakeholder(projectId, payload)
      await updateMeeting(meetingId, {
        stakeholder_ids: [...existingIds, created.id],
      })
      onAdded()
      setOpen(false)
    } catch (error) {
      console.error('Failed to create stakeholder:', error)
    } finally {
      setAdding(false)
    }
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button className="w-7 h-7 rounded-md border border-dashed border-[#D0D0D0] flex items-center justify-center text-text-muted hover:border-accent hover:text-accent hover:bg-[#f0f7fa] transition-colors">
          <Plus className="w-3.5 h-3.5" />
        </button>
      </PopoverTrigger>
      <PopoverContent align="end" sideOffset={8} className="w-[320px] p-0">
        {!showCreate ? (
          <div>
            <div className="p-3 border-b border-[#F0F0F0]">
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#B0B0B0]" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search stakeholders..."
                  autoFocus
                  className="w-full pl-8 pr-3 py-1.5 text-[13px] border border-border rounded-md bg-surface-page outline-none focus:border-[#88BABF] focus:bg-white"
                />
              </div>
            </div>

            <div className="max-h-[240px] overflow-y-auto">
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-4 h-4 animate-spin text-text-muted" />
                </div>
              ) : available.length > 0 ? (
                available.map((s) => (
                  <button
                    key={s.id}
                    onClick={() => handleAddExisting(s.id)}
                    disabled={adding}
                    className="w-full flex items-center gap-2.5 px-3 py-2 text-left hover:bg-surface-page transition-colors disabled:opacity-50"
                  >
                    <div className="w-6 h-6 rounded-full bg-accent flex items-center justify-center text-[9px] font-bold text-white flex-shrink-0">
                      {s.name.split(' ').map((w) => w[0]).join('').toUpperCase().slice(0, 2)}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="text-[13px] font-medium text-text-primary truncate">{s.name}</div>
                      <div className="text-[11px] text-text-muted truncate">
                        {s.stakeholder_type?.replace('_', ' ')} {s.organization ? `· ${s.organization}` : ''}
                      </div>
                    </div>
                  </button>
                ))
              ) : (
                <div className="py-6 text-center text-[13px] text-text-muted">
                  {search ? 'No matching stakeholders' : 'All stakeholders already added'}
                </div>
              )}
            </div>

            <div className="p-2 border-t border-[#F0F0F0]">
              <button
                onClick={() => setShowCreate(true)}
                className="w-full flex items-center gap-2 px-3 py-2 text-[12px] font-medium text-accent rounded-md hover:bg-[#f0f7fa] transition-colors"
              >
                <Plus className="w-3.5 h-3.5" />
                Create new stakeholder
              </button>
            </div>
          </div>
        ) : (
          <div className="p-3">
            <div className="flex items-center justify-between mb-3">
              <span className="text-[13px] font-semibold text-text-primary">New Stakeholder</span>
              <button onClick={() => setShowCreate(false)} className="p-1 rounded hover:bg-[#F0F0F0]">
                <X className="w-3.5 h-3.5 text-text-muted" />
              </button>
            </div>

            <div className="space-y-2.5">
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="Name *"
                autoFocus
                className="w-full px-2.5 py-1.5 text-[13px] border border-border rounded-md outline-none focus:border-[#88BABF]"
              />
              <input
                type="email"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                placeholder="Email"
                className="w-full px-2.5 py-1.5 text-[13px] border border-border rounded-md outline-none focus:border-[#88BABF]"
              />
              <input
                type="text"
                value={newRole}
                onChange={(e) => setNewRole(e.target.value)}
                placeholder="Role / Title"
                className="w-full px-2.5 py-1.5 text-[13px] border border-border rounded-md outline-none focus:border-[#88BABF]"
              />
              <input
                type="text"
                value={newOrg}
                onChange={(e) => setNewOrg(e.target.value)}
                placeholder="Organization"
                className="w-full px-2.5 py-1.5 text-[13px] border border-border rounded-md outline-none focus:border-[#88BABF]"
              />
              <select
                value={newType}
                onChange={(e) => setNewType(e.target.value as StakeholderType)}
                className="w-full px-2.5 py-1.5 text-[13px] border border-border rounded-md outline-none focus:border-[#88BABF] bg-white"
              >
                {STAKEHOLDER_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>

              <button
                onClick={handleCreateAndAdd}
                disabled={!newName.trim() || adding}
                className="w-full py-1.5 text-[12px] font-medium text-white bg-accent rounded-md hover:bg-accent-hover transition-colors disabled:opacity-50"
              >
                {adding ? 'Adding...' : 'Create & Add'}
              </button>
            </div>
          </div>
        )}
      </PopoverContent>
    </Popover>
  )
}
