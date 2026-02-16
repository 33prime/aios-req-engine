'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { Building2, Users, FolderKanban, Brain, FileText, Loader2 } from 'lucide-react'
import { getClient, enrichClient, analyzeClient, getClientIntelligence } from '@/lib/api'
import type { ClientIntelligenceProfile } from '@/lib/api'
import type { ClientDetail } from '@/types/workspace'
import { AppSidebar } from '@/components/workspace/AppSidebar'
import { ClientHeader } from './components/ClientHeader'
import { ClientOverviewTab } from './components/ClientOverviewTab'
import { ClientProjectsTab } from './components/ClientProjectsTab'
import { ClientPeopleTab } from './components/ClientPeopleTab'
import { ClientIntelligenceTab } from './components/ClientIntelligenceTab'
import { ClientSourcesTab } from './components/ClientSourcesTab'

type TabId = 'overview' | 'people' | 'projects' | 'intelligence' | 'sources'

export default function ClientDetailPage() {
  const params = useParams()
  const router = useRouter()
  const clientId = params.id as string

  const [client, setClient] = useState<ClientDetail | null>(null)
  const [intelligence, setIntelligence] = useState<ClientIntelligenceProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [activeTab, setActiveTab] = useState<TabId>('overview')
  const [enriching, setEnriching] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const loadClient = useCallback(async () => {
    if (!clientId) return
    try {
      setLoading(true)
      const [data, intel] = await Promise.all([
        getClient(clientId),
        getClientIntelligence(clientId).catch(() => null),
      ])
      setClient(data)
      setIntelligence(intel)
      setError(null)
    } catch (err) {
      console.error('Failed to load client:', err)
      setError('Failed to load client details')
    } finally {
      setLoading(false)
    }
  }, [clientId])

  useEffect(() => {
    loadClient()
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [loadClient])

  const handleEnrich = async () => {
    if (!clientId || enriching) return
    setEnriching(true)
    try {
      await enrichClient(clientId)
      setTimeout(() => {
        loadClient()
        setEnriching(false)
      }, 5000)
    } catch (err) {
      console.error('Failed to enrich client:', err)
      setEnriching(false)
    }
  }

  const handleAnalyze = async () => {
    if (!clientId || analyzing) return
    setAnalyzing(true)
    const startedAt = intelligence?.last_analyzed_at
    try {
      await analyzeClient(clientId)
      // Poll every 3s until last_analyzed_at changes or 60s timeout
      let elapsed = 0
      pollRef.current = setInterval(async () => {
        elapsed += 3000
        if (elapsed > 60000) {
          if (pollRef.current) clearInterval(pollRef.current)
          setAnalyzing(false)
          loadClient()
          return
        }
        try {
          const intel = await getClientIntelligence(clientId)
          if (intel.last_analyzed_at && intel.last_analyzed_at !== startedAt) {
            if (pollRef.current) clearInterval(pollRef.current)
            setIntelligence(intel)
            setAnalyzing(false)
            loadClient()
          }
        } catch {
          // keep polling
        }
      }, 3000)
    } catch (err) {
      console.error('Failed to analyze client:', err)
      setAnalyzing(false)
    }
  }

  const sidebarWidth = sidebarCollapsed ? 64 : 224

  const tabs: { id: TabId; label: string; icon: React.ReactNode }[] = [
    { id: 'overview', label: 'Overview', icon: <Building2 className="w-3.5 h-3.5" /> },
    { id: 'people', label: 'People', icon: <Users className="w-3.5 h-3.5" /> },
    { id: 'projects', label: 'Projects', icon: <FolderKanban className="w-3.5 h-3.5" /> },
    { id: 'intelligence', label: 'Intelligence', icon: <Brain className="w-3.5 h-3.5" /> },
    { id: 'sources', label: 'Sources', icon: <FileText className="w-3.5 h-3.5" /> },
  ]

  if (loading) {
    return (
      <>
        <AppSidebar isCollapsed={sidebarCollapsed} onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)} />
        <div className="min-h-screen bg-[#F4F4F4] flex items-center justify-center transition-all duration-300" style={{ marginLeft: sidebarWidth }}>
          <div className="text-center">
            <Loader2 className="w-8 h-8 text-[#3FAF7A] animate-spin mx-auto mb-3" />
            <p className="text-[13px] text-[#999]">Loading client...</p>
          </div>
        </div>
      </>
    )
  }

  if (error || !client) {
    return (
      <>
        <AppSidebar isCollapsed={sidebarCollapsed} onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)} />
        <div className="min-h-screen bg-[#F4F4F4] flex items-center justify-center transition-all duration-300" style={{ marginLeft: sidebarWidth }}>
          <div className="text-center">
            <p className="text-[14px] text-[#666] mb-3">{error || 'Client not found'}</p>
            <button
              onClick={() => router.push('/clients')}
              className="px-6 py-3 text-[13px] font-medium text-white bg-[#3FAF7A] rounded-xl hover:bg-[#25785A] transition-colors"
            >
              Back to Clients
            </button>
          </div>
        </div>
      </>
    )
  }

  return (
    <>
      <AppSidebar isCollapsed={sidebarCollapsed} onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)} />
      <div className="min-h-screen bg-[#F4F4F4] transition-all duration-300" style={{ marginLeft: sidebarWidth }}>
        <div className="max-w-[1200px] mx-auto px-6 py-6">
          <ClientHeader
            client={client}
            enriching={enriching}
            analyzing={analyzing}
            intelligence={intelligence}
            onBack={() => router.push('/clients')}
            onEnrich={handleEnrich}
            onAnalyze={handleAnalyze}
          />

          {/* Tabs */}
          <div className="border-b border-[#E5E5E5] mb-6">
            <div className="flex gap-6">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`inline-flex items-center gap-1.5 pb-2.5 text-[13px] font-medium border-b-2 transition-colors ${
                    activeTab === tab.id
                      ? 'text-[#3FAF7A] border-[#3FAF7A]'
                      : 'text-[#999] border-transparent hover:text-[#666]'
                  }`}
                >
                  {tab.icon}
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {/* Tab Content */}
          {activeTab === 'overview' && <ClientOverviewTab client={client} intelligence={intelligence} />}
          {activeTab === 'people' && <ClientPeopleTab clientId={clientId} roleGaps={client.role_gaps ?? []} />}
          {activeTab === 'projects' && (
            <ClientProjectsTab client={client} onRefresh={loadClient} />
          )}
          {activeTab === 'intelligence' && (
            <ClientIntelligenceTab clientId={clientId} client={client} intelligence={intelligence} />
          )}
          {activeTab === 'sources' && (
            <ClientSourcesTab clientId={clientId} projects={client.projects} />
          )}
        </div>
      </div>
    </>
  )
}
