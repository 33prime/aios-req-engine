'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Users, AlertTriangle, Search, Loader2 } from 'lucide-react'
import { getClientStakeholders } from '@/lib/api'

interface RoleGap {
  role: string
  why_needed: string
  urgency: string
  which_areas?: string[]
}

interface Stakeholder {
  id: string
  name: string
  first_name?: string | null
  last_name?: string | null
  role?: string | null
  stakeholder_type?: string | null
  influence_level?: string | null
  email?: string | null
  project_id?: string | null
  project_name?: string | null
  reports_to_id?: string | null
  allies?: string[] | null
}

interface ClientPeopleTabProps {
  clientId: string
  roleGaps: RoleGap[]
}

const TYPE_OPTIONS = ['all', 'champion', 'sponsor', 'blocker', 'influencer', 'end_user'] as const

function getInitials(s: Stakeholder): string {
  if (s.first_name && s.last_name) return `${s.first_name[0]}${s.last_name[0]}`.toUpperCase()
  return (s.name || '?').slice(0, 2).toUpperCase()
}

function getDisplayName(s: Stakeholder): string {
  if (s.first_name && s.last_name) return `${s.first_name} ${s.last_name}`
  return s.name || 'Unknown'
}

export function ClientPeopleTab({ clientId, roleGaps }: ClientPeopleTabProps) {
  const router = useRouter()
  const [stakeholders, setStakeholders] = useState<Stakeholder[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [search, setSearch] = useState('')

  useEffect(() => {
    loadStakeholders()
  }, [clientId, typeFilter])

  const loadStakeholders = async () => {
    setLoading(true)
    try {
      const params: { stakeholder_type?: string; limit?: number } = { limit: 200 }
      if (typeFilter !== 'all') params.stakeholder_type = typeFilter
      const result = await getClientStakeholders(clientId, params)
      setStakeholders(result.stakeholders as unknown as Stakeholder[])
      setTotal(result.total)
    } catch (err) {
      console.error('Failed to load stakeholders:', err)
    } finally {
      setLoading(false)
    }
  }

  // Count by type
  const typeCounts = stakeholders.reduce<Record<string, number>>((acc, s) => {
    const t = s.stakeholder_type || 'unknown'
    acc[t] = (acc[t] || 0) + 1
    return acc
  }, {})

  // Filter by search
  const filtered = search
    ? stakeholders.filter((s) => {
        const name = getDisplayName(s).toLowerCase()
        const role = (s.role || '').toLowerCase()
        return name.includes(search.toLowerCase()) || role.includes(search.toLowerCase())
      })
    : stakeholders

  // Build org chart data — keyed by parent stakeholder ID
  const topLevel = stakeholders.filter((s) => !s.reports_to_id)
  const byReportsTo = stakeholders.reduce<Record<string, Stakeholder[]>>((acc, s) => {
    if (s.reports_to_id) {
      if (!acc[s.reports_to_id]) acc[s.reports_to_id] = []
      acc[s.reports_to_id].push(s)
    }
    return acc
  }, {})
  const hasOrgData = Object.keys(byReportsTo).length > 0

  return (
    <div className="space-y-6">
      {/* Summary bar */}
      <div className="flex flex-wrap items-center gap-2">
        {['champion', 'sponsor', 'blocker', 'influencer', 'end_user'].map((type) => {
          const count = typeCounts[type] || 0
          if (count === 0) return null
          return (
            <span
              key={type}
              className={`px-2.5 py-1 rounded-lg text-[12px] font-medium ${
                type === 'champion'
                  ? 'bg-[#E8F5E9] text-[#25785A]'
                  : 'bg-[#F0F0F0] text-[#666]'
              }`}
            >
              {type.replace('_', ' ')}: {count}
            </span>
          )
        })}
        <span className="text-[12px] text-[#999] ml-1">{total} total</span>
      </div>

      {/* Role Gaps */}
      {roleGaps.length > 0 && (
        <div className="bg-white rounded-2xl border border-[#E5E5E5] shadow-md p-5">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-4 h-4 text-[#666]" />
            <h3 className="text-[14px] font-semibold text-[#333]">Role Gaps</h3>
          </div>
          <div className="space-y-2">
            {roleGaps.map((gap, i) => (
              <div key={i} className="bg-[#F4F4F4] rounded-xl p-3">
                <div className="flex items-center gap-2">
                  <span className="text-[13px] font-semibold text-[#333]">Missing: {gap.role}</span>
                  <span className="px-1.5 py-0.5 text-[10px] font-medium text-[#666] bg-[#E5E5E5] rounded">
                    {gap.urgency}
                  </span>
                </div>
                <p className="text-[12px] text-[#666] mt-1">{gap.why_needed}</p>
                {gap.which_areas && gap.which_areas.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {gap.which_areas.map((area, j) => (
                      <span key={j} className="px-1.5 py-0.5 text-[10px] text-[#999] bg-white rounded border border-[#E5E5E5]">
                        {area}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Stakeholder Table */}
      <div className="bg-white rounded-2xl border border-[#E5E5E5] shadow-md overflow-hidden">
        {/* Filter bar */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-[#E5E5E5]">
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="px-2 py-1.5 text-[12px] text-[#666] bg-[#F4F4F4] rounded-lg border-0 outline-none"
          >
            {TYPE_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {opt === 'all' ? 'All Types' : opt.replace('_', ' ')}
              </option>
            ))}
          </select>
          <div className="flex-1 relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#999]" />
            <input
              type="text"
              placeholder="Search people..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-[12px] text-[#333] bg-[#F4F4F4] rounded-lg border-0 outline-none placeholder:text-[#999]"
            />
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-5 h-5 text-[#3FAF7A] animate-spin" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-12">
            <Users className="w-8 h-8 text-[#CCC] mx-auto mb-2" />
            <p className="text-[13px] text-[#666]">No stakeholders found</p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#E5E5E5]">
                <th className="text-left px-4 py-2.5 text-[11px] font-medium text-[#999] uppercase tracking-wide">Name</th>
                <th className="text-left px-4 py-2.5 text-[11px] font-medium text-[#999] uppercase tracking-wide">Role</th>
                <th className="text-left px-4 py-2.5 text-[11px] font-medium text-[#999] uppercase tracking-wide">Type</th>
                <th className="text-left px-4 py-2.5 text-[11px] font-medium text-[#999] uppercase tracking-wide">Influence</th>
                <th className="text-left px-4 py-2.5 text-[11px] font-medium text-[#999] uppercase tracking-wide">Project</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s) => (
                <tr
                  key={s.id}
                  className="border-b border-[#F0F0F0] last:border-0 hover:bg-[#FAFAFA] transition-colors cursor-pointer"
                  onClick={() => router.push(`/people/${s.id}${s.project_id ? `?project_id=${s.project_id}` : ''}`)}
                >
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#3FAF7A] to-[#25785A] flex items-center justify-center flex-shrink-0">
                        <span className="text-[10px] font-bold text-white">{getInitials(s)}</span>
                      </div>
                      <span className="text-[13px] font-medium text-[#333]">{getDisplayName(s)}</span>
                    </div>
                  </td>
                  <td className="px-4 py-2.5 text-[12px] text-[#666]">{s.role || '-'}</td>
                  <td className="px-4 py-2.5">
                    {s.stakeholder_type && (
                      <span className={`px-2 py-0.5 text-[11px] font-medium rounded-md ${
                        s.stakeholder_type === 'champion'
                          ? 'bg-[#E8F5E9] text-[#25785A]'
                          : 'bg-[#F0F0F0] text-[#666]'
                      }`}>
                        {s.stakeholder_type.replace('_', ' ')}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2.5">
                    {s.influence_level && (
                      <span className="px-2 py-0.5 text-[11px] font-medium text-[#666] bg-[#F0F0F0] rounded-md">
                        {s.influence_level}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-[12px] text-[#999]">{s.project_name || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Org Chart */}
      <div className="bg-white rounded-2xl border border-[#E5E5E5] shadow-md p-5">
        <h3 className="text-[14px] font-semibold text-[#333] mb-3">Organization Map</h3>
        {!hasOrgData ? (
          <div className="bg-[#F4F4F4] rounded-lg px-4 py-6 text-center">
            <p className="text-[13px] text-[#666]">Relationship data builds as signals mention stakeholder connections</p>
          </div>
        ) : (
          <div className="space-y-1">
            {topLevel.map((person) => (
              <OrgNode key={person.id} person={person} children={byReportsTo[person.id] || []} byReportsTo={byReportsTo} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function OrgNode({ person, children: childNodes, byReportsTo }: { person: Stakeholder; children: Stakeholder[]; byReportsTo: Record<string, Stakeholder[]> }) {
  return (
    <div>
      <div className="flex items-center gap-2 py-1.5 px-2 rounded-lg hover:bg-[#F4F4F4]">
        <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#3FAF7A] to-[#25785A] flex items-center justify-center flex-shrink-0">
          <span className="text-[10px] font-bold text-white">{getInitials(person)}</span>
        </div>
        <span className="text-[13px] font-medium text-[#333]">{getDisplayName(person)}</span>
        {person.role && <span className="text-[11px] text-[#999]">{person.role}</span>}
        {person.stakeholder_type && (
          <span className={`px-1.5 py-0.5 text-[10px] font-medium rounded ${
            person.stakeholder_type === 'champion'
              ? 'bg-[#E8F5E9] text-[#25785A]'
              : 'bg-[#F0F0F0] text-[#666]'
          }`}>
            {person.stakeholder_type.replace('_', ' ')}
          </span>
        )}
      </div>
      {childNodes.length > 0 && (
        <div className="ml-5 border-l-2 border-[#E5E5E5] pl-3">
          {childNodes.map((child) => (
            <OrgNode key={child.id} person={child} children={byReportsTo[child.id] || []} byReportsTo={byReportsTo} />
          ))}
        </div>
      )}
    </div>
  )
}
