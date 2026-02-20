'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter, useParams } from 'next/navigation'
import {
  Calendar, Pencil, MoreHorizontal, Trash2, X, Check, Mail,
} from 'lucide-react'
import { AppSidebar } from '@/components/workspace/AppSidebar'
import { getMeeting, updateMeeting, deleteMeeting, getBotStatus, deployBot, listProjectStakeholders } from '@/lib/api'
import type { Meeting, MeetingStatus, MeetingBot } from '@/types/api'
import type { StakeholderDetail } from '@/types/workspace'
import { MeetingHeader } from './components/MeetingHeader'
import { MeetingParticipants } from './components/MeetingParticipants'
import { AddParticipantPopover } from './components/AddParticipantPopover'
import { MeetingAgenda } from './components/MeetingAgenda'
import { MeetingNotes } from './components/MeetingNotes'
import { MeetingSidePanel } from './components/MeetingSidePanel'
import { EmailAgendaModal } from './components/EmailAgendaModal'

export default function MeetingDetailPage() {
  const router = useRouter()
  const params = useParams()
  const meetingId = params.meetingId as string

  const [meeting, setMeeting] = useState<Meeting | null>(null)
  const [bot, setBot] = useState<MeetingBot | null>(null)
  const [loading, setLoading] = useState(true)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [showMenu, setShowMenu] = useState(false)
  const [editing, setEditing] = useState(false)
  const [editTitle, setEditTitle] = useState('')
  const [editDescription, setEditDescription] = useState('')
  const [sidePanelOpen, setSidePanelOpen] = useState(true)
  const [participants, setParticipants] = useState<StakeholderDetail[]>([])
  const [showEmailModal, setShowEmailModal] = useState(false)

  const loadMeeting = useCallback(async () => {
    try {
      setLoading(true)
      const data = await getMeeting(meetingId)
      setMeeting(data)
      setEditTitle(data.title)
      setEditDescription(data.description || '')
    } catch (error) {
      console.error('Failed to load meeting:', error)
    } finally {
      setLoading(false)
    }
  }, [meetingId])

  const loadBot = useCallback(async () => {
    try {
      const data = await getBotStatus(meetingId)
      setBot(data)
    } catch {
      // No bot deployed — that's fine
    }
  }, [meetingId])

  const loadParticipants = useCallback(async (projectId: string, stakeholderIds: string[]) => {
    if (!stakeholderIds.length) {
      setParticipants([])
      return
    }
    try {
      const { stakeholders: all } = await listProjectStakeholders(projectId)
      const filtered = all.filter((s: StakeholderDetail) => stakeholderIds.includes(s.id))
      setParticipants(filtered)
    } catch (error) {
      console.error('Failed to load participants:', error)
    }
  }, [])

  useEffect(() => {
    loadMeeting()
    loadBot()
  }, [loadMeeting, loadBot])

  useEffect(() => {
    if (meeting) {
      loadParticipants(meeting.project_id, meeting.stakeholder_ids || [])
    }
  }, [meeting?.project_id, meeting?.stakeholder_ids, loadParticipants])

  const handleSaveEdit = async () => {
    if (!meeting) return
    try {
      const updated = await updateMeeting(meeting.id, {
        title: editTitle.trim(),
        description: editDescription.trim() || undefined,
      })
      setMeeting(updated)
      setEditing(false)
    } catch (error) {
      console.error('Failed to update meeting:', error)
    }
  }

  const handleDelete = async () => {
    if (!meeting || !confirm('Delete this meeting? This cannot be undone.')) return
    try {
      await deleteMeeting(meeting.id)
      router.push('/meetings')
    } catch (error) {
      console.error('Failed to delete meeting:', error)
    }
  }

  const handleStatusChange = async (status: MeetingStatus) => {
    if (!meeting) return
    try {
      const updated = await updateMeeting(meeting.id, { status })
      setMeeting(updated)
      setShowMenu(false)
    } catch (error) {
      console.error('Failed to update status:', error)
    }
  }

  const handleDeployBot = async () => {
    if (!meeting) return
    try {
      const result = await deployBot(meeting.id)
      setBot(result)
    } catch (error) {
      console.error('Failed to deploy bot:', error)
    }
  }

  const handleParticipantAdded = () => {
    // Reload the meeting to get updated stakeholder_ids, which triggers participant reload
    loadMeeting()
  }

  const sidebarWidth = sidebarCollapsed ? 64 : 224

  if (loading) {
    return (
      <>
        <AppSidebar
          isCollapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        />
        <div
          className="min-h-screen bg-[#FAFAFA] flex items-center justify-center transition-all duration-300"
          style={{ marginLeft: sidebarWidth }}
        >
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#3FAF7A] mx-auto mb-4" />
            <p className="text-sm text-[rgba(55,53,47,0.45)]">Loading meeting...</p>
          </div>
        </div>
      </>
    )
  }

  if (!meeting) {
    return (
      <>
        <AppSidebar
          isCollapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        />
        <div
          className="min-h-screen bg-[#FAFAFA] flex items-center justify-center transition-all duration-300"
          style={{ marginLeft: sidebarWidth }}
        >
          <div className="text-center">
            <Calendar className="w-10 h-10 text-gray-300 mx-auto mb-3" />
            <p className="text-[14px] font-medium text-[#37352f] mb-1">Meeting not found</p>
            <button
              onClick={() => router.push('/meetings')}
              className="text-[13px] text-[#3FAF7A] hover:underline mt-2"
            >
              Back to meetings
            </button>
          </div>
        </div>
      </>
    )
  }

  const isUpcoming = meeting.status === 'scheduled'

  return (
    <>
      <AppSidebar
        isCollapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
      />
      <div
        className="min-h-screen bg-[#FAFAFA] transition-all duration-300"
        style={{ marginLeft: sidebarWidth }}
      >
        <div className="flex flex-col h-screen">
          {/* Top Bar — 52px */}
          <div className="h-[52px] bg-white border-b border-[#E5E5E5] flex items-center justify-between px-6 flex-shrink-0">
            {/* Breadcrumb */}
            <div className="flex items-center gap-1.5 text-[13px]">
              <button
                onClick={() => router.push('/meetings')}
                className="text-[#7B7B7B] hover:text-[#044159] transition-colors"
              >
                Meetings
              </button>
              <span className="text-[#D0D0D0]">/</span>
              <span className="text-[#1D1D1F] font-medium truncate max-w-[300px]">
                {meeting.title}
              </span>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowEmailModal(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-[#044159] bg-white border border-[#D0D0D0] rounded-md hover:border-[#044159] hover:bg-[#f0f7fa] transition-colors"
              >
                <Mail className="w-3.5 h-3.5" />
                Email Agenda
              </button>

              {!editing && (
                <button
                  onClick={() => setEditing(true)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-[#4B4B4B] bg-[#F5F5F5] rounded-md hover:bg-[#E8E8E8] transition-colors"
                >
                  <Pencil className="w-3 h-3" />
                  Edit
                </button>
              )}

              {/* More menu */}
              <div className="relative">
                <button
                  onClick={() => setShowMenu(!showMenu)}
                  className="p-1.5 rounded-md text-[#7B7B7B] hover:bg-[#F0F0F0] transition-colors"
                >
                  <MoreHorizontal className="w-4 h-4" />
                </button>
                {showMenu && (
                  <>
                    <div className="fixed inset-0 z-10" onClick={() => setShowMenu(false)} />
                    <div className="absolute right-0 top-full mt-1 z-20 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1">
                      {isUpcoming && (
                        <button
                          onClick={() => handleStatusChange('completed')}
                          className="w-full px-3 py-2 text-left text-[13px] text-[#37352f] hover:bg-gray-50 flex items-center gap-2"
                        >
                          <Check className="w-3.5 h-3.5" />
                          Mark Completed
                        </button>
                      )}
                      {isUpcoming && (
                        <button
                          onClick={() => handleStatusChange('cancelled')}
                          className="w-full px-3 py-2 text-left text-[13px] text-[#999] hover:bg-gray-50 flex items-center gap-2"
                        >
                          <X className="w-3.5 h-3.5" />
                          Cancel Meeting
                        </button>
                      )}
                      <button
                        onClick={handleDelete}
                        className="w-full px-3 py-2 text-left text-[13px] text-red-500 hover:bg-gray-50 flex items-center gap-2"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        Delete Meeting
                      </button>
                    </div>
                  </>
                )}
              </div>

              {/* Panel toggle icon */}
              <button
                onClick={() => setSidePanelOpen(!sidePanelOpen)}
                title="Toggle side panel"
                className={`w-8 h-8 rounded-md border flex items-center justify-center transition-all ${
                  sidePanelOpen
                    ? 'bg-[#E0EFF3] text-[#044159] border-[#044159]'
                    : 'bg-white text-[#7B7B7B] border-[#E5E5E5] hover:bg-[#F0F0F0] hover:border-[#D0D0D0]'
                }`}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <rect x="3" y="3" width="18" height="18" rx="2" />
                  <line x1="15" y1="3" x2="15" y2="21" />
                </svg>
              </button>
            </div>
          </div>

          {/* Content row */}
          <div className="flex flex-1 overflow-hidden">
            {/* Main panel */}
            <div className="flex-1 overflow-y-auto">
              <div className="px-8 py-6 max-w-full">
                {/* Edit mode */}
                {editing ? (
                  <div className="space-y-3 mb-6">
                    <input
                      type="text"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      className="w-full text-[22px] font-bold text-[#1D1D1F] bg-transparent border-b-2 border-[#044159] outline-none pb-1"
                    />
                    <textarea
                      value={editDescription}
                      onChange={(e) => setEditDescription(e.target.value)}
                      placeholder="Add a description..."
                      rows={2}
                      className="w-full text-[14px] text-[#4B4B4B] bg-transparent border border-gray-200 rounded-md px-3 py-2 outline-none focus:ring-1 focus:ring-[#044159] resize-none"
                    />
                    <div className="flex gap-2">
                      <button
                        onClick={handleSaveEdit}
                        className="px-3 py-1.5 text-[12px] font-medium text-white bg-[#044159] rounded-md hover:bg-[#033344] transition-colors"
                      >
                        Save
                      </button>
                      <button
                        onClick={() => {
                          setEditing(false)
                          setEditTitle(meeting.title)
                          setEditDescription(meeting.description || '')
                        }}
                        className="px-3 py-1.5 text-[12px] font-medium text-[#666] bg-[#F5F5F5] rounded-md hover:bg-[#EBEBEB] transition-colors"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <MeetingHeader meeting={meeting} />
                )}

                {/* Participants */}
                <div className="mt-7">
                  <div className="flex items-center justify-between mb-3.5">
                    <div className="text-[15px] font-semibold text-[#1D1D1F] flex items-center gap-2">
                      Participants
                      <span className="text-[12px] font-medium text-[#7B7B7B] bg-[#F0F0F0] px-[7px] py-[1px] rounded-lg">
                        {participants.length}
                      </span>
                    </div>
                    <AddParticipantPopover
                      projectId={meeting.project_id}
                      meetingId={meeting.id}
                      existingIds={meeting.stakeholder_ids || []}
                      onAdded={handleParticipantAdded}
                    />
                  </div>

                  <div className="flex gap-2.5 flex-wrap">
                    {participants.map((p, i) => {
                      const colors = ['#044159', '#25785A', '#3FAF7A', '#88BABF', '#0A1E2F']
                      const roleBadgeConfig: Record<string, { bg: string; text: string }> = {
                        champion: { bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]' },
                        sponsor: { bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]' },
                        blocker: { bg: 'bg-[#0A1E2F]', text: 'text-white' },
                        influencer: { bg: 'bg-[#F0F0F0]', text: 'text-[#666]' },
                        end_user: { bg: 'bg-[#F0F0F0]', text: 'text-[#666]' },
                        consultant: { bg: 'bg-[#E0EFF3]', text: 'text-[#044159]' },
                      }
                      const initials = p.name.split(' ').map((w) => w[0]).join('').toUpperCase().slice(0, 2)
                      const roleConfig = p.stakeholder_type ? roleBadgeConfig[p.stakeholder_type] : null
                      const roleLabel = p.stakeholder_type
                        ? p.stakeholder_type.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())
                        : null

                      return (
                        <div
                          key={p.id}
                          className="flex items-center gap-2.5 px-3.5 py-2 bg-white border border-[#E5E5E5] rounded-lg min-w-[180px] hover:border-[#D0D0D0] hover:shadow-[0_2px_4px_rgba(0,0,0,0.04)] transition-all"
                        >
                          <div
                            className="w-8 h-8 rounded-full flex items-center justify-center text-[11px] font-bold text-white flex-shrink-0"
                            style={{
                              background: `linear-gradient(135deg, ${colors[i % colors.length]}, ${colors[(i + 2) % colors.length]})`,
                            }}
                          >
                            {initials}
                          </div>
                          <div className="min-w-0">
                            <div className="text-[13px] font-semibold text-[#1D1D1F] truncate">{p.name}</div>
                            <div className="flex items-center gap-1 text-[11px] text-[#7B7B7B]">
                              {roleConfig && roleLabel && (
                                <span className={`text-[10px] font-semibold px-1.5 py-[1px] rounded ${roleConfig.bg} ${roleConfig.text}`}>
                                  {roleLabel}
                                </span>
                              )}
                              {p.organization && <span className="truncate">{p.organization}</span>}
                            </div>
                          </div>
                        </div>
                      )
                    })}

                    {participants.length === 0 && (
                      <div className="text-[13px] text-[#7B7B7B] py-2">
                        No participants added yet
                      </div>
                    )}
                  </div>
                </div>

                {/* Agenda */}
                <MeetingAgenda
                  agenda={meeting.agenda || null}
                  isUpcoming={isUpcoming}
                />

                {/* Notes */}
                <MeetingNotes
                  summary={meeting.summary || null}
                  isUpcoming={isUpcoming}
                />

                {/* Bottom padding */}
                <div className="h-12" />
              </div>
            </div>

            {/* Side Panel */}
            {sidePanelOpen && (
              <MeetingSidePanel
                meeting={meeting}
                bot={bot}
                participants={participants}
                onDeployBot={handleDeployBot}
              />
            )}
          </div>
        </div>
      </div>

      {/* Email Agenda Modal */}
      <EmailAgendaModal
        open={showEmailModal}
        meeting={meeting}
        participants={participants}
        onClose={() => setShowEmailModal(false)}
      />
    </>
  )
}
