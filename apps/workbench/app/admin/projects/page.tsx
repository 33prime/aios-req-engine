'use client'

import { useEffect, useState, useMemo } from 'react'
import Image from 'next/image'
import Link from 'next/link'
import { Search, User } from 'lucide-react'
import { listAdminProjects } from '@/lib/api'
import type { AdminProjectSummary } from '@/types/api'

export default function AdminProjectsPage() {
  const [projects, setProjects] = useState<AdminProjectSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [stageFilter, setStageFilter] = useState('')

  useEffect(() => {
    listAdminProjects()
      .then(setProjects)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => {
    let result = projects
    if (search) {
      const s = search.toLowerCase()
      result = result.filter(p =>
        p.name.toLowerCase().includes(s) ||
        (p.client_name || '').toLowerCase().includes(s) ||
        (p.owner_name || '').toLowerCase().includes(s)
      )
    }
    if (stageFilter) {
      result = result.filter(p => p.stage === stageFilter)
    }
    return result
  }, [projects, search, stageFilter])

  const stages = useMemo(() => {
    const set = new Set(projects.map(p => p.stage).filter(Boolean) as string[])
    return Array.from(set).sort()
  }, [projects])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-5 h-5 border-2 border-[#3FAF7A] border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-[22px] font-bold text-[#333333]">Projects</h1>
        <span className="px-3 py-1 text-[13px] rounded-full bg-[#F0F0F0] text-[#666666]">
          {filtered.length} project{filtered.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#999999]" />
          <input
            type="text"
            placeholder="Search projects..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 text-[13px] border border-[#E5E5E5] rounded-xl bg-white focus:outline-none focus:border-[#3FAF7A] transition-colors"
          />
        </div>
        <select
          value={stageFilter}
          onChange={(e) => setStageFilter(e.target.value)}
          className="px-3 py-2 text-[13px] border border-[#E5E5E5] rounded-xl bg-white focus:outline-none focus:border-[#3FAF7A]"
        >
          <option value="">All Stages</option>
          {stages.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] overflow-hidden">
        <div className="overflow-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#E5E5E5] bg-[#F8F9FB]">
                <th className="text-left text-[11px] text-[#999999] uppercase tracking-wide px-4 py-3">Name</th>
                <th className="text-left text-[11px] text-[#999999] uppercase tracking-wide px-4 py-3">Client</th>
                <th className="text-left text-[11px] text-[#999999] uppercase tracking-wide px-4 py-3">Owner</th>
                <th className="text-left text-[11px] text-[#999999] uppercase tracking-wide px-4 py-3">Stage</th>
                <th className="text-right text-[11px] text-[#999999] uppercase tracking-wide px-4 py-3">Signals</th>
                <th className="text-right text-[11px] text-[#999999] uppercase tracking-wide px-4 py-3">Features</th>
                <th className="text-left text-[11px] text-[#999999] uppercase tracking-wide px-4 py-3">Created</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((project) => (
                <tr key={project.id} className="border-b border-[#E5E5E5] hover:bg-[#F4F4F4] transition-colors">
                  <td className="px-4 py-3">
                    <Link href={`/projects/${project.id}`} className="text-[13px] text-[#3FAF7A] hover:underline font-medium">
                      {project.name}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-[13px] text-[#666666]">{project.client_name || '-'}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded-full bg-gradient-to-br from-[#3FAF7A] to-[#25785A] flex items-center justify-center overflow-hidden flex-shrink-0">
                        {project.owner_photo_url ? (
                          <Image src={project.owner_photo_url} alt="" width={24} height={24} className="w-full h-full object-cover" />
                        ) : (
                          <User className="w-3 h-3 text-white" />
                        )}
                      </div>
                      <span className="text-[13px] text-[#666666]">{project.owner_name || '-'}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 text-[11px] rounded-full bg-[#F0F0F0] text-[#666666]">
                      {project.stage || '-'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-[13px] text-[#333333] text-right">{project.signal_count}</td>
                  <td className="px-4 py-3 text-[13px] text-[#333333] text-right">{project.feature_count}</td>
                  <td className="px-4 py-3 text-[12px] text-[#999999]">{new Date(project.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {filtered.length === 0 && (
          <div className="text-center py-12 text-[#999999] text-sm">No projects found</div>
        )}
      </div>
    </div>
  )
}
