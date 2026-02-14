'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Building2 } from 'lucide-react'
import { listClients, createClient } from '@/lib/api'
import type { ClientSummary, ClientCreatePayload } from '@/types/workspace'
import { AppSidebar } from '@/components/workspace/AppSidebar'
import { ClientsTopNav } from './components/ClientsTopNav'
import { ClientCard } from './components/ClientCard'
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

  const sidebarWidth = sidebarCollapsed ? 64 : 224

  if (loading && clients.length === 0) {
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
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#3FAF7A] mx-auto mb-4" />
            <p className="text-sm text-[#999]">Loading clients...</p>
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
        <div className="max-w-[1400px] mx-auto px-4 py-4">
          {/* Page header */}
          <div className="flex items-center gap-2 mb-4">
            <Building2 className="w-5 h-5 text-[#333]" />
            <h1 className="text-[18px] font-semibold text-[#333]">Clients</h1>
          </div>

          <ClientsTopNav
            searchQuery={searchQuery}
            industryFilter={industryFilter}
            onSearchChange={setSearchQuery}
            onIndustryFilterChange={setIndustryFilter}
            onRefresh={loadData}
            onCreateClient={() => setShowCreate(true)}
          />

          <div className="mb-3 text-[12px] text-[#999]">
            {total} {total === 1 ? 'client' : 'clients'} found
          </div>

          {clients.length === 0 ? (
            <div className="text-center py-16">
              <Building2 className="w-12 h-12 text-[#CCC] mx-auto mb-3" />
              <p className="text-[14px] text-[#666] mb-2">No clients yet</p>
              <p className="text-[12px] text-[#999] mb-4">
                Add your first client organization to start tracking
              </p>
              <button
                onClick={() => setShowCreate(true)}
                className="px-6 py-3 text-[13px] font-medium text-white bg-[#3FAF7A] rounded-xl hover:bg-[#25785A] transition-colors"
              >
                Add Client
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {clients.map((client) => (
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
