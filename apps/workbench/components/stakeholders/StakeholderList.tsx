'use client'

import { useState, useEffect } from 'react'
import { Plus, Users, Filter, Search, Loader2 } from 'lucide-react'
import StakeholderCard from './StakeholderCard'

interface Stakeholder {
  id: string
  name: string
  role?: string
  email?: string
  phone?: string
  organization?: string
  stakeholder_type?: string
  influence_level?: string
  domain_expertise?: string[]
  topic_mentions?: Record<string, number>
  is_primary_contact?: boolean
  source_type?: string
  confirmation_status?: string
}

interface StakeholderListProps {
  projectId: string
  onCreateClick?: () => void
  onEditClick?: (stakeholder: Stakeholder) => void
}

export default function StakeholderList({
  projectId,
  onCreateClick,
  onEditClick,
}: StakeholderListProps) {
  const [stakeholders, setStakeholders] = useState<Stakeholder[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState<string | null>(null)
  const [filterInfluence, setFilterInfluence] = useState<string | null>(null)

  const fetchStakeholders = async () => {
    try {
      setLoading(true)
      setError(null)

      let url = `${process.env.NEXT_PUBLIC_API_BASE}/v1/projects/${projectId}/stakeholders`
      const params = new URLSearchParams()
      if (filterType) params.append('stakeholder_type', filterType)
      if (filterInfluence) params.append('influence_level', filterInfluence)
      if (params.toString()) url += `?${params.toString()}`

      const response = await fetch(url)
      if (!response.ok) throw new Error('Failed to fetch stakeholders')

      const data = await response.json()
      setStakeholders(data.stakeholders || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load stakeholders')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStakeholders()
  }, [projectId, filterType, filterInfluence])

  const handleSetPrimary = async (stakeholderId: string) => {
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE}/v1/projects/${projectId}/stakeholders/${stakeholderId}/set-primary`,
        { method: 'POST' }
      )
      if (!response.ok) throw new Error('Failed to set primary contact')
      await fetchStakeholders()
    } catch (err) {
      console.error('Error setting primary contact:', err)
    }
  }

  const handleDelete = async (stakeholderId: string) => {
    if (!confirm('Are you sure you want to delete this stakeholder?')) return

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE}/v1/projects/${projectId}/stakeholders/${stakeholderId}`,
        { method: 'DELETE' }
      )
      if (!response.ok) throw new Error('Failed to delete stakeholder')
      await fetchStakeholders()
    } catch (err) {
      console.error('Error deleting stakeholder:', err)
    }
  }

  // Filter by search query
  const filteredStakeholders = stakeholders.filter((sh) => {
    if (!searchQuery) return true
    const query = searchQuery.toLowerCase()
    return (
      sh.name.toLowerCase().includes(query) ||
      sh.role?.toLowerCase().includes(query) ||
      sh.email?.toLowerCase().includes(query) ||
      sh.organization?.toLowerCase().includes(query) ||
      sh.domain_expertise?.some((e) => e.toLowerCase().includes(query))
    )
  })

  // Group by type for display
  const groupedStakeholders = {
    primary: filteredStakeholders.filter((s) => s.is_primary_contact),
    champion: filteredStakeholders.filter((s) => s.stakeholder_type === 'champion' && !s.is_primary_contact),
    sponsor: filteredStakeholders.filter((s) => s.stakeholder_type === 'sponsor' && !s.is_primary_contact),
    influencer: filteredStakeholders.filter((s) => s.stakeholder_type === 'influencer' && !s.is_primary_contact),
    blocker: filteredStakeholders.filter((s) => s.stakeholder_type === 'blocker' && !s.is_primary_contact),
    end_user: filteredStakeholders.filter((s) => s.stakeholder_type === 'end_user' && !s.is_primary_contact),
    other: filteredStakeholders.filter(
      (s) => !s.is_primary_contact && !['champion', 'sponsor', 'influencer', 'blocker', 'end_user'].includes(s.stakeholder_type || '')
    ),
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600">{error}</p>
        <button
          onClick={fetchStakeholders}
          className="mt-2 text-blue-600 hover:text-blue-800"
        >
          Retry
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Users className="w-5 h-5 text-gray-500" />
          <h2 className="text-lg font-semibold text-gray-900">
            Stakeholders ({stakeholders.length})
          </h2>
        </div>
        {onCreateClick && (
          <button
            onClick={onCreateClick}
            className="inline-flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
          >
            <Plus className="w-4 h-4" />
            Add Stakeholder
          </button>
        )}
      </div>

      {/* Search and filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search stakeholders..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-400" />
          <select
            value={filterType || ''}
            onChange={(e) => setFilterType(e.target.value || null)}
            className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Types</option>
            <option value="champion">Champion</option>
            <option value="sponsor">Sponsor</option>
            <option value="influencer">Influencer</option>
            <option value="blocker">Blocker</option>
            <option value="end_user">End User</option>
          </select>

          <select
            value={filterInfluence || ''}
            onChange={(e) => setFilterInfluence(e.target.value || null)}
            className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Influence</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
      </div>

      {/* Empty state */}
      {stakeholders.length === 0 && (
        <div className="text-center py-12 bg-gray-50 rounded-lg border border-dashed border-gray-300">
          <Users className="w-12 h-12 mx-auto text-gray-400 mb-3" />
          <p className="text-gray-600 mb-2">No stakeholders yet</p>
          <p className="text-sm text-gray-500 mb-4">
            Stakeholders will be automatically extracted from transcripts and emails
          </p>
          {onCreateClick && (
            <button
              onClick={onCreateClick}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
            >
              <Plus className="w-4 h-4" />
              Add Manually
            </button>
          )}
        </div>
      )}

      {/* Stakeholder groups */}
      {groupedStakeholders.primary.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-500 mb-3 flex items-center gap-2">
            Primary Contact
          </h3>
          <div className="grid gap-3">
            {groupedStakeholders.primary.map((sh) => (
              <StakeholderCard
                key={sh.id}
                stakeholder={sh}
                onSetPrimary={handleSetPrimary}
                onEdit={onEditClick}
                onDelete={handleDelete}
              />
            ))}
          </div>
        </div>
      )}

      {groupedStakeholders.champion.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-500 mb-3">Champions</h3>
          <div className="grid gap-3">
            {groupedStakeholders.champion.map((sh) => (
              <StakeholderCard
                key={sh.id}
                stakeholder={sh}
                onSetPrimary={handleSetPrimary}
                onEdit={onEditClick}
                onDelete={handleDelete}
              />
            ))}
          </div>
        </div>
      )}

      {groupedStakeholders.sponsor.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-500 mb-3">Sponsors</h3>
          <div className="grid gap-3">
            {groupedStakeholders.sponsor.map((sh) => (
              <StakeholderCard
                key={sh.id}
                stakeholder={sh}
                onSetPrimary={handleSetPrimary}
                onEdit={onEditClick}
                onDelete={handleDelete}
              />
            ))}
          </div>
        </div>
      )}

      {groupedStakeholders.influencer.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-500 mb-3">Influencers</h3>
          <div className="grid gap-3">
            {groupedStakeholders.influencer.map((sh) => (
              <StakeholderCard
                key={sh.id}
                stakeholder={sh}
                onSetPrimary={handleSetPrimary}
                onEdit={onEditClick}
                onDelete={handleDelete}
              />
            ))}
          </div>
        </div>
      )}

      {groupedStakeholders.blocker.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-500 mb-3">Blockers</h3>
          <div className="grid gap-3">
            {groupedStakeholders.blocker.map((sh) => (
              <StakeholderCard
                key={sh.id}
                stakeholder={sh}
                onSetPrimary={handleSetPrimary}
                onEdit={onEditClick}
                onDelete={handleDelete}
              />
            ))}
          </div>
        </div>
      )}

      {groupedStakeholders.end_user.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-500 mb-3">End Users</h3>
          <div className="grid gap-3">
            {groupedStakeholders.end_user.map((sh) => (
              <StakeholderCard
                key={sh.id}
                stakeholder={sh}
                onSetPrimary={handleSetPrimary}
                onEdit={onEditClick}
                onDelete={handleDelete}
              />
            ))}
          </div>
        </div>
      )}

      {groupedStakeholders.other.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-500 mb-3">Other</h3>
          <div className="grid gap-3">
            {groupedStakeholders.other.map((sh) => (
              <StakeholderCard
                key={sh.id}
                stakeholder={sh}
                onSetPrimary={handleSetPrimary}
                onEdit={onEditClick}
                onDelete={handleDelete}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
