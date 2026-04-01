'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { Loader2 } from 'lucide-react'
import { getClient, analyzeClient, getClientIntelligence, getClientKnowledgeBase, deleteClient, updateClient } from '@/lib/api'
import type { ClientIntelligenceProfile } from '@/lib/api'
import type { ClientDetail, ClientKnowledgeBase } from '@/types/workspace'
import { AppSidebar } from '@/components/workspace/AppSidebar'
import { ClientHeader } from './components/ClientHeader'
import { ClientOverviewTab } from './components/ClientOverviewTab'
import { ClientProjectsTab } from './components/ClientProjectsTab'
import { ClientPeopleTab } from './components/ClientPeopleTab'
import { ClientEditModal } from './components/ClientEditModal'

export default function ClientDetailPage() {
  const params = useParams()
  const router = useRouter()
  const clientId = params.id as string

  const [client, setClient] = useState<ClientDetail | null>(null)
  const [intelligence, setIntelligence] = useState<ClientIntelligenceProfile | null>(null)
  const [knowledgeBase, setKnowledgeBase] = useState<ClientKnowledgeBase | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  const [analyzing, setAnalyzing] = useState(false)
  const [showEdit, setShowEdit] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const loadClient = useCallback(async () => {
    if (!clientId) return
    try {
      setLoading(true)
      const [data, intel, kb] = await Promise.all([
        getClient(clientId),
        getClientIntelligence(clientId).catch(() => null),
        getClientKnowledgeBase(clientId).catch(() => null),
      ])
      setClient(data)
      setIntelligence(intel)
      setKnowledgeBase(kb)
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

  const handleAnalyze = async () => {
    if (!clientId || analyzing) return
    setAnalyzing(true)
    const startedAt = intelligence?.last_analyzed_at
    try {
      await analyzeClient(clientId)
      let elapsed = 0
      pollRef.current = setInterval(async () => {
        elapsed += 3000
        if (elapsed > 120000) {
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

  const handleDelete = async () => {
    if (!clientId) return
    try {
      await deleteClient(clientId)
      router.push('/clients')
    } catch (err) {
      console.error('Failed to delete client:', err)
    }
  }

  const handleEdit = async (data: Record<string, string>) => {
    await updateClient(clientId, data)
    setAnalyzing(true)
    setTimeout(async () => {
      try {
        await loadClient()
      } finally {
        setAnalyzing(false)
      }
    }, 3000)
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
          className="min-h-screen bg-[#F4F4F4] flex items-center justify-center transition-all duration-300"
          style={{ marginLeft: sidebarWidth }}
        >
          <div className="text-center">
            <Loader2 className="w-8 h-8 text-brand-primary animate-spin mx-auto mb-3" />
            <p className="text-[13px] text-[#999]">Loading client...</p>
          </div>
        </div>
      </>
    )
  }

  if (error || !client) {
    return (
      <>
        <AppSidebar
          isCollapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        />
        <div
          className="min-h-screen bg-[#F4F4F4] flex items-center justify-center transition-all duration-300"
          style={{ marginLeft: sidebarWidth }}
        >
          <div className="text-center">
            <p className="text-[14px] text-[#666] mb-3">{error || 'Client not found'}</p>
            <button
              onClick={() => router.push('/clients')}
              className="px-6 py-3 text-[13px] font-medium text-white bg-brand-primary rounded-xl hover:bg-[#25785A] transition-colors"
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
      <AppSidebar
        isCollapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
      />
      <div
        className="min-h-screen bg-[#F4F4F4] transition-all duration-300"
        style={{ marginLeft: sidebarWidth }}
      >
        <div className="max-w-[1200px] mx-auto px-6 py-6">
          <ClientHeader
            client={client}
            analyzing={analyzing}
            intelligence={intelligence}
            onBack={() => router.push('/clients')}
            onAnalyze={handleAnalyze}
            onEdit={() => setShowEdit(true)}
            onDelete={handleDelete}
          />

          {/* Primary content — single scrolling page */}
          <ClientOverviewTab
            client={client}
            intelligence={intelligence}
            knowledgeBase={knowledgeBase}
            onKnowledgeBaseChange={() =>
              getClientKnowledgeBase(clientId).then(setKnowledgeBase).catch(() => {})
            }
          />

          {/* People section — inline below overview */}
          <div className="mt-8">
            <h2 className="text-[14px] font-semibold text-[#333] mb-4">People</h2>
            <ClientPeopleTab clientId={clientId} roleGaps={client.role_gaps ?? []} />
          </div>

          {/* Projects section — inline below people */}
          <div className="mt-8">
            <h2 className="text-[14px] font-semibold text-[#333] mb-4">Projects</h2>
            <ClientProjectsTab client={client} onRefresh={loadClient} />
          </div>

          <ClientEditModal
            open={showEdit}
            onClose={() => setShowEdit(false)}
            onSave={handleEdit}
            client={client}
          />
        </div>
      </div>
    </>
  )
}
