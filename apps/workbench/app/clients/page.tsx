'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { Building2 } from 'lucide-react'
import { listClients, createClient } from '@/lib/api'
import type { ClientSummary, ClientCreatePayload } from '@/types/workspace'
import { AppSidebar } from '@/components/workspace/AppSidebar'
import { ClientsTopNav } from './components/ClientsTopNav'
import { ClientCard } from './components/ClientCard'
import { ClientRow } from './components/ClientRow'
import { ClientCreateModal } from './components/ClientCreateModal'

export default function ClientsPage() {
  const router = useRouter()
  const [clients, setClients] = useState<ClientSummary[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [industryFilter, setIndustryFilter] = useState('all')
  const [showCreate, setShowCreate] = useState(false)
  const [viewMode, setViewMode] = useState<'cards' | 'table'>('cards')
  const [sortField, setSortField] = useState('name')

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      const params: Record<string, string | number> = { limit: 100 }
      if (searchQuery) params.search = searchQuery
      if (industryFilter !== 'all') params.search = industryFilter

      const result = await listClients(params as any)
      setClients(result.clients)
      setTotal(result.total)
    } catch (error) {
      console.error('Failed to load clients:', error)
    } finally {
      setLoading(false)
    }
  }, [searchQuery, industryFilter])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleCreateClient = async (data: ClientCreatePayload) => {
    try {
      await createClient(data)
      setShowCreate(false)
      loadData()
    } catch (error) {
      console.error('Failed to create client:', error)
    }
  }

  // Sort clients
  const sortedClients = useMemo(() => {
    return [...clients].sort((a, b) => {
      if (sortField === 'name') {
        return a.name.localeCompare(b.name)
      }
      if (sortField === 'project_count') {
        return (b.project_count ?? 0) - (a.project_count ?? 0)
      }
      if (sortField === 'stakeholder_count') {
        return (b.stakeholder_count ?? 0) - (a.stakeholder_count ?? 0)
      }
      if (sortField === 'profile_completeness') {
        return (b.profile_completeness ?? -1) - (a.profile_completeness ?? -1)
      }
      return 0
    })
  }, [clients, sortField])

  const sidebarWidth = sidebarCollapsed ? 64 : 224

  if (loading && clients.length === 0) {
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
            <p className="text-sm text-text-muted">Loading clients...</p>
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
          {/* Page header */}
          <div className="flex items-center gap-2 mb-4">
            <Building2 className="w-5 h-5 text-[#333]" />
            <h1 className="text-[18px] font-semibold text-[#333]">Clients</h1>
          </div>

          <ClientsTopNav
            searchQuery={searchQuery}
            industryFilter={industryFilter}
            viewMode={viewMode}
            sortField={sortField}
            onSearchChange={setSearchQuery}
            onIndustryFilterChange={setIndustryFilter}
            onRefresh={loadData}
            onCreateClient={() => setShowCreate(true)}
            onViewModeChange={setViewMode}
            onSortChange={setSortField}
          />

          <div className="mb-3 text-[12px] text-[#999]">
            {total} {total === 1 ? 'client' : 'clients'} found
          </div>

          {sortedClients.length === 0 ? (
            <div className="text-center py-16">
              <Building2 className="w-12 h-12 text-[#CCC] mx-auto mb-3" />
              <p className="text-[14px] text-[#666] mb-2">No clients yet</p>
              <p className="text-[12px] text-[#999] mb-4">
                Add your first client organization to start tracking
              </p>
              <button
                onClick={() => setShowCreate(true)}
                className="px-6 py-3 text-[13px] font-medium text-white bg-brand-primary rounded-xl hover:bg-[#25785A] transition-colors"
              >
                Add Client
              </button>
            </div>
          ) : viewMode === 'table' ? (
            <div className="bg-white rounded-xl border border-border shadow-sm overflow-hidden">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="px-3 py-2.5 text-left text-[11px] font-semibold text-text-muted uppercase tracking-wider">Client</th>
                    <th className="px-3 py-2.5 text-left text-[11px] font-semibold text-text-muted uppercase tracking-wider">Industry</th>
                    <th className="px-3 py-2.5 text-center text-[11px] font-semibold text-text-muted uppercase tracking-wider">Projects</th>
                    <th className="px-3 py-2.5 text-center text-[11px] font-semibold text-text-muted uppercase tracking-wider">People</th>
                    <th className="px-3 py-2.5 text-left text-[11px] font-semibold text-text-muted uppercase tracking-wider">Completeness</th>
                    <th className="px-3 py-2.5 text-left text-[11px] font-semibold text-text-muted uppercase tracking-wider">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {sortedClients.map((client) => (
                    <ClientRow
                      key={client.id}
                      client={client}
                      onClick={() => router.push(`/clients/${client.id}`)}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {sortedClients.map((client) => (
                <ClientCard
                  key={client.id}
                  client={client}
                  onClick={() => router.push(`/clients/${client.id}`)}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      <ClientCreateModal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        onSave={handleCreateClient}
      />
    </>
  )
}
