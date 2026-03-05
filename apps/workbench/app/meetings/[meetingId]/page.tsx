'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { useRouter, useParams } from 'next/navigation'
import {
  Calendar, Pencil, MoreHorizontal, Trash2, X, Check, Mail,
} from 'lucide-react'
import { AppSidebar } from '@/components/workspace/AppSidebar'
import { getMeeting, updateMeeting, deleteMeeting, getBotStatus, deployBot, listProjectStakeholders, generateStrategyBrief, getBriefForMeeting } from '@/lib/api'
import type { Meeting, MeetingStatus, MeetingBot } from '@/types/api'
import type { StakeholderDetail } from '@/types/workspace'
import type { CallStrategyBrief, StakeholderIntel } from '@/types/call-intelligence'
import { MeetingHeader } from './components/MeetingHeader'
import { AddParticipantPopover } from './components/AddParticipantPopover'
import { MeetingIntelligencePanel } from './components/MeetingIntelligencePanel'
import { EmailAgendaModal } from './components/EmailAgendaModal'
import { MissionThemesSection } from './components/MissionThemesSection'
import { CallGoalsSection } from './components/CallGoalsSection'
import { MissionCriticalQuestionsSection } from './components/MissionCriticalQuestionsSection'
import { CriticalRequirementsSection } from './components/CriticalRequirementsSection'
import { StakeholderIntelSection } from './components/StakeholderIntelSection'
import { FocusAreasCompact } from './components/FocusAreasCompact'
import { GenerateStrategyPrompt } from './components/GenerateStrategyPrompt'

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
  const [participants, setParticipants] = useState<StakeholderDetail[]>([])
  const [showEmailModal, setShowEmailModal] = useState(false)
  const [sidePanelOpen, setSidePanelOpen] = useState(true)
  const [brief, setBrief] = useState<CallStrategyBrief | null>(null)
  const [generatingBrief, setGeneratingBrief] = useState(false)
  const briefPollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const loadBrief = useCallback(async () => {
    try {
      const b = await getBriefForMeeting(meetingId)
      setBrief(b)
      return b
    } catch {
      setBrief(null)
      return null
    }
  }, [meetingId])

  const handleGenerateBrief = async () => {
    if (!meeting) return
    setGeneratingBrief(true)
    try {
      await generateStrategyBrief(meeting.project_id, meeting.id)
      let attempts = 0
      briefPollRef.current = setInterval(async () => {
        attempts++
        const b = await loadBrief()
        if (b || attempts >= 30) {
          if (briefPollRef.current) clearInterval(briefPollRef.current)
          briefPollRef.current = null
          setGeneratingBrief(false)
        }
      }, 3_000)
    } catch (e) {
      console.error('Failed to generate brief:', e)
      setGeneratingBrief(false)
    }
  }

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
    loadBrief()
  }, [loadMeeting, loadBot, loadBrief])

  // Cleanup brief poll on unmount
  useEffect(() => {
    return () => {
      if (briefPollRef.current) clearInterval(briefPollRef.current)
    }
  }, [])

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
    loadMeeting()
  }

  const sidebarWidth = sidebarCollapsed ? 64 : 224

  // Map live participant data → StakeholderIntel for the briefing section
  const liveStakeholderIntel: StakeholderIntel[] = participants.map(p => ({
    name: p.name,
    role: p.role ?? undefined,
    influence: p.influence_level ?? 'unknown',
    stakeholder_type: p.stakeholder_type ?? 'end_user',
    key_concerns: p.key_concerns ?? p.concerns ?? [],
    approach_notes: p.engagement_strategy ?? '',
    priorities: p.priorities ?? undefined,
    domain_expertise: p.domain_expertise ?? undefined,
    engagement_level: p.engagement_level,
    decision_authority: p.decision_authority,
    approval_required_for: p.approval_required_for ?? undefined,
    veto_power_over: p.veto_power_over ?? undefined,
    win_conditions: p.win_conditions ?? undefined,
    risk_if_disengaged: p.risk_if_disengaged,
    preferred_channel: p.preferred_channel,
    profile_completeness: p.profile_completeness ?? undefined,
    topic_mentions: p.topic_mentions ?? undefined,
  }))

  if (loading) {
    return (
      <>
        <AppSidebar
          isCollapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        />
        <div
          className="min-h-screen bg-surface-page flex items-center justify-center transition-all duration-300"
          style={{ marginLeft: sidebarWidth }}
        >
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-primary mx-auto mb-4" />
            <p className="text-sm text-text-placeholder">Loading meeting...</p>
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
          className="min-h-screen bg-surface-page flex items-center justify-center transition-all duration-300"
          style={{ marginLeft: sidebarWidth }}
        >
          <div className="text-center">
            <Calendar className="w-10 h-10 text-gray-300 mx-auto mb-3" />
            <p className="text-[14px] font-medium text-[#37352f] mb-1">Meeting not found</p>
            <button
              onClick={() => router.push('/meetings')}
              className="text-[13px] text-brand-primary hover:underline mt-2"
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
        className="min-h-screen bg-surface-page transition-all duration-300"
        style={{ marginLeft: sidebarWidth }}
      >
        <div className="flex flex-col h-screen">
          {/* Top Bar — 52px */}
          <div className="h-[52px] bg-white border-b border-border flex items-center justify-between px-6 flex-shrink-0">
            {/* Breadcrumb */}
            <div className="flex items-center gap-1.5 text-[13px]">
              <button
                onClick={() => router.push('/meetings')}
                className="text-text-muted hover:text-accent transition-colors"
              >
                Meetings
              </button>
              <span className="text-[#D0D0D0]">/</span>
              <span className="text-text-primary font-medium truncate max-w-[300px]">
                {meeting.title}
              </span>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowEmailModal(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-accent bg-white border border-[#D0D0D0] rounded-md hover:border-accent hover:bg-[#f0f7fa] transition-colors"
              >
                <Mail className="w-3.5 h-3.5" />
                Email Agenda
              </button>

              {!editing && (
                <button
                  onClick={() => setEditing(true)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-text-secondary bg-surface-subtle rounded-md hover:bg-[#E8E8E8] transition-colors"
                >
                  <Pencil className="w-3 h-3" />
                  Edit
                </button>
              )}

              {/* More menu */}
              <div className="relative">
                <button
                  onClick={() => setShowMenu(!showMenu)}
                  className="p-1.5 rounded-md text-text-muted hover:bg-[#F0F0F0] transition-colors"
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
                title={sidePanelOpen ? 'Hide intelligence panel' : 'Show intelligence panel'}
                className={`w-8 h-8 rounded-md border flex items-center justify-center transition-all ${
                  sidePanelOpen
                    ? 'bg-[#E0EFF3] text-accent border-accent'
                    : 'bg-white text-text-muted border-border hover:bg-[#F0F0F0] hover:border-[#D0D0D0]'
                }`}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <rect x="3" y="3" width="18" height="18" rx="2" />
                  <line x1="15" y1="3" x2="15" y2="21" />
                </svg>
              </button>
            </div>
          </div>

          {/* Two-panel layout */}
          <div className="flex flex-1 overflow-hidden">
            {/* Left panel — Meeting Context */}
            <div className={`${sidePanelOpen ? 'w-[55%] min-w-[400px] border-r border-border' : 'flex-1'} overflow-y-auto`}>
              <div className="px-6 py-6">
                {/* Edit mode */}
                {editing ? (
                  <div className="space-y-3 mb-6">
                    <input
                      type="text"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      className="w-full text-[22px] font-bold text-text-primary bg-transparent border-b-2 border-accent outline-none pb-1"
                    />
                    <textarea
                      value={editDescription}
                      onChange={(e) => setEditDescription(e.target.value)}
                      placeholder="Add a description..."
                      rows={2}
                      className="w-full text-[14px] text-text-secondary bg-transparent border border-gray-200 rounded-md px-3 py-2 outline-none focus:ring-1 focus:ring-accent resize-none"
                    />
                    <div className="flex gap-2">
                      <button
                        onClick={handleSaveEdit}
                        className="px-3 py-1.5 text-[12px] font-medium text-white bg-accent rounded-md hover:bg-accent-hover transition-colors"
                      >
                        Save
                      </button>
                      <button
                        onClick={() => {
                          setEditing(false)
                          setEditTitle(meeting.title)
                          setEditDescription(meeting.description || '')
                        }}
                        className="px-3 py-1.5 text-[12px] font-medium text-[#666] bg-surface-subtle rounded-md hover:bg-[#EBEBEB] transition-colors"
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
                    <div className="text-[15px] font-semibold text-text-primary flex items-center gap-2">
                      Participants
                      <span className="text-[12px] font-medium text-text-muted bg-[#F0F0F0] px-[7px] py-[1px] rounded-lg">
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
                        consultant: { bg: 'bg-[#E0EFF3]', text: 'text-accent' },
                      }
                      const initials = p.name.split(' ').map((w) => w[0]).join('').toUpperCase().slice(0, 2)
                      const roleConfig = p.stakeholder_type ? roleBadgeConfig[p.stakeholder_type] : null
                      const roleLabel = p.stakeholder_type
                        ? p.stakeholder_type.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())
                        : null

                      return (
                        <div
                          key={p.id}
                          className="flex items-center gap-2.5 px-3.5 py-2 bg-white border border-border rounded-lg min-w-[180px] hover:border-[#D0D0D0] hover:shadow-[0_2px_4px_rgba(0,0,0,0.04)] transition-all"
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
                            <div className="text-[13px] font-semibold text-text-primary truncate">{p.name}</div>
                            <div className="flex items-center gap-1 text-[11px] text-text-muted">
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
                      <div className="text-[13px] text-text-muted py-2">
                        No participants added yet
                      </div>
                    )}
                  </div>
                </div>

                {/* Strategy Playbook */}
                {brief ? (
                  <>
                    {brief.mission_themes && brief.mission_themes.length > 0 ? (
                      <MissionThemesSection themes={(brief.mission_themes || []).map(t => ({
                        ...t,
                        explores: t.explores || (t as any).validates || '',
                      }))} />
                    ) : (
                      <>
                        <CallGoalsSection goals={brief.call_goals} results={brief.goal_results} />
                        <MissionCriticalQuestionsSection questions={brief.mission_critical_questions} />
                        <CriticalRequirementsSection requirements={brief.critical_requirements || []} />
                      </>
                    )}
                    <FocusAreasCompact areas={brief.focus_areas} />
                  </>
                ) : (
                  <GenerateStrategyPrompt onGenerate={handleGenerateBrief} generating={generatingBrief} />
                )}

                {/* Stakeholder Briefing — always live from DB, not brief snapshot */}
                <StakeholderIntelSection intel={liveStakeholderIntel} />

                {/* Bottom padding */}
                <div className="h-8" />
              </div>
            </div>

            {/* Right panel — Intelligence Hub (45%) */}
            {sidePanelOpen && (
              <div className="w-[45%] min-w-[380px] overflow-hidden">
                <MeetingIntelligencePanel
                  meeting={meeting}
                  bot={bot}
                  projectId={meeting.project_id}
                  onDeployBot={handleDeployBot}
                  brief={brief}
                />
              </div>
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
