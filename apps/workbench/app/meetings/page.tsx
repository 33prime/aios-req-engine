'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { Calendar } from 'lucide-react'
import { isAfter, isBefore, startOfToday } from 'date-fns'
import { AppSidebar } from '@/components/workspace/AppSidebar'
import { listMeetings, createMeeting, listProjects, getGoogleStatus } from '@/lib/api'
import type { Meeting } from '@/types/api'
import { MeetingsTopNav, type MeetingTab } from './components/MeetingsTopNav'
import { MeetingsTable } from './components/MeetingsTable'
import { MeetingCards } from './components/MeetingCards'
import { MeetingCreateModal } from './components/MeetingCreateModal'

export default function MeetingsPage() {
  const router = useRouter()
  const [meetings, setMeetings] = useState<Meeting[]>([])
  const [loading, setLoading] = useState(true)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [activeTab, setActiveTab] = useState<MeetingTab>('upcoming')
  const [searchQuery, setSearchQuery] = useState('')
  const [typeFilter, setTypeFilter] = useState('all')
  const [projectFilter, setProjectFilter] = useState('all')
  const [viewMode, setViewMode] = useState<'table' | 'cards'>('table')
  const [projects, setProjects] = useState<{ id: string; name: string }[]>([])
  const [showCreate, setShowCreate] = useState(false)
  const [googleConnected, setGoogleConnected] = useState(false)

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      const result = await listMeetings(
        projectFilter !== 'all' ? projectFilter : undefined,
      )
      setMeetings(result)
    } catch (error) {
      console.error('Failed to load meetings:', error)
    } finally {
      setLoading(false)
    }
  }, [projectFilter])

  useEffect(() => {
    loadData()
  }, [loadData])

  useEffect(() => {
    listProjects('active')
      .then((res) => setProjects(res.projects.map((p) => ({ id: p.id, name: p.name }))))
      .catch(() => {})
    getGoogleStatus()
      .then((res) => setGoogleConnected(res.connected))
      .catch(() => {})
  }, [])

  // Filter meetings by tab + search + type
  const filtered = useMemo(() => {
    const today = startOfToday()

    return meetings.filter((m) => {
      const meetingDate = new Date(m.meeting_date)

      // Tab filter
      if (activeTab === 'upcoming') {
        if (m.status === 'cancelled') return false
        if (isBefore(meetingDate, today) && m.status === 'completed') return false
      }
      if (activeTab === 'past') {
        if (m.status === 'scheduled' && isAfter(meetingDate, today)) return false
      }
      if (activeTab === 'recorded') {
        if (!m.google_meet_link || m.status !== 'completed') return false
      }

      // Search filter
      if (searchQuery) {
        const q = searchQuery.toLowerCase()
        if (
          !m.title.toLowerCase().includes(q) &&
          !(m.project_name || '').toLowerCase().includes(q) &&
          !(m.description || '').toLowerCase().includes(q)
        ) return false
      }

      // Type filter
      if (typeFilter !== 'all' && m.meeting_type !== typeFilter) return false

      return true
    })
  }, [meetings, activeTab, searchQuery, typeFilter])

  // Tab counts
  const counts = useMemo(() => {
    const today = startOfToday()
    let upcoming = 0
    let past = 0
    let recorded = 0
    for (const m of meetings) {
      const meetingDate = new Date(m.meeting_date)
      if (m.status !== 'cancelled' && !(isBefore(meetingDate, today) && m.status === 'completed')) {
        upcoming++
      }
      if (!(m.status === 'scheduled' && isAfter(meetingDate, today))) {
        past++
      }
      if (m.google_meet_link && m.status === 'completed') {
        recorded++
      }
    }
    return { upcoming, past, recorded }
  }, [meetings])

  const handleRowClick = (meeting: Meeting) => {
    router.push(`/meetings/${meeting.id}`)
  }

  const handleCreateMeeting = async (data: Parameters<typeof createMeeting>[0]) => {
    try {
      await createMeeting(data)
      setShowCreate(false)
      loadData()
    } catch (error) {
      console.error('Failed to create meeting:', error)
    }
  }

  const sidebarWidth = sidebarCollapsed ? 64 : 224

  if (loading && meetings.length === 0) {
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
            <p className="text-sm text-text-placeholder">Loading meetings...</p>
          </div>
        </div>
      </>
    )
  }

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
        <div className="max-w-[1400px] mx-auto px-4 py-4">
          <MeetingsTopNav
            activeTab={activeTab}
            counts={counts}
            searchQuery={searchQuery}
            typeFilter={typeFilter}
            projectFilter={projectFilter}
            projects={projects}
            viewMode={viewMode}
            onTabChange={setActiveTab}
            onSearchChange={setSearchQuery}
            onTypeFilterChange={setTypeFilter}
            onProjectFilterChange={setProjectFilter}
            onViewModeChange={setViewMode}
            onRefresh={loadData}
            onCreateMeeting={() => setShowCreate(true)}
          />

          <div className="mb-3 text-[12px] text-text-placeholder">
            {filtered.length} {filtered.length === 1 ? 'meeting' : 'meetings'} found
          </div>

          {viewMode === 'table' ? (
            <MeetingsTable meetings={filtered} onRowClick={handleRowClick} />
          ) : (
            <MeetingCards meetings={filtered} onCardClick={handleRowClick} />
          )}
        </div>
      </div>

      <MeetingCreateModal
        open={showCreate}
        projects={projects}
        googleConnected={googleConnected}
        onClose={() => setShowCreate(false)}
        onSave={handleCreateMeeting}
      />
    </>
  )
}
