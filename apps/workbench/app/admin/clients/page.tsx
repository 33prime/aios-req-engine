'use client'

import { useEffect, useState, useMemo } from 'react'
import Link from 'next/link'
import { Search, Building2 } from 'lucide-react'
import { listClients } from '@/lib/api'

interface ClientItem {
  id: string
  name: string
  industry?: string | null
  company_size?: string | null
  profile_completeness?: number
  last_analyzed_at?: string | null
  created_at: string
}

export default function AdminClientsPage() {
  const [clients, setClients] = useState<ClientItem[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  useEffect(() => {
    listClients()
      .then((data: any) => setClients(Array.isArray(data) ? data : data?.clients || []))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => {
    if (!search) return clients
    const s = search.toLowerCase()
    return clients.filter(c =>
      c.name.toLowerCase().includes(s) ||
      (c.industry || '').toLowerCase().includes(s)
    )
  }, [clients, search])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-5 h-5 border-2 border-brand-primary border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-[22px] font-bold text-text-body">Clients</h1>
        <span className="px-3 py-1 text-[13px] rounded-full bg-[#F0F0F0] text-[#666666]">
          {filtered.length} client{filtered.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-placeholder" />
        <input
          type="text"
          placeholder="Search clients..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-10 pr-4 py-2 text-[13px] border border-border rounded-xl bg-white focus:outline-none focus:border-brand-primary transition-colors"
        />
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filtered.map((client) => (
          <Link
            key={client.id}
            href={`/clients/${client.id}`}
            className="bg-white rounded-2xl shadow-md border border-border p-5 hover:shadow-lg transition-shadow block"
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2.5 rounded-xl bg-brand-primary-light">
                <Building2 className="w-5 h-5 text-brand-primary" />
              </div>
              <div className="min-w-0 flex-1">
                <h3 className="text-[14px] font-medium text-text-body truncate">{client.name}</h3>
                {client.industry && (
                  <p className="text-[12px] text-text-placeholder">{client.industry}</p>
                )}
              </div>
            </div>

            <div className="flex items-center justify-between text-[12px]">
              {client.company_size && (
                <span className="px-2 py-0.5 rounded-full bg-[#F0F0F0] text-[#666666]">{client.company_size}</span>
              )}
              {client.profile_completeness != null && (
                <span className="text-text-placeholder">{client.profile_completeness}% complete</span>
              )}
            </div>

            {client.last_analyzed_at && (
              <p className="text-[11px] text-text-placeholder mt-2">
                Analyzed {new Date(client.last_analyzed_at).toLocaleDateString()}
              </p>
            )}
          </Link>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="text-center py-12 text-text-placeholder text-sm">No clients found</div>
      )}
    </div>
  )
}
