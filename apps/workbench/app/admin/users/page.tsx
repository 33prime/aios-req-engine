'use client'

import { useEffect, useState, useMemo } from 'react'
import { Search } from 'lucide-react'
import { listAdminUsers } from '@/lib/api'
import { UserCard } from '../components/UserCard'
import type { AdminUserSummary } from '@/types/api'

export default function AdminUsersPage() {
  const [users, setUsers] = useState<AdminUserSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState('')

  useEffect(() => {
    listAdminUsers()
      .then(setUsers)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => {
    let result = users
    if (search) {
      const s = search.toLowerCase()
      result = result.filter(u =>
        u.email.toLowerCase().includes(s) ||
        (u.first_name || '').toLowerCase().includes(s) ||
        (u.last_name || '').toLowerCase().includes(s)
      )
    }
    if (roleFilter) {
      result = result.filter(u => u.platform_role === roleFilter)
    }
    return result
  }, [users, search, roleFilter])

  const roles = useMemo(() => {
    const set = new Set(users.map(u => u.platform_role))
    return Array.from(set).sort()
  }, [users])

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
        <h1 className="text-[22px] font-bold text-text-body">Users</h1>
        <span className="px-3 py-1 text-[13px] rounded-full bg-[#F0F0F0] text-[#666666]">
          {filtered.length} user{filtered.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-placeholder" />
          <input
            type="text"
            placeholder="Search users..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 text-[13px] border border-border rounded-xl bg-white focus:outline-none focus:border-brand-primary transition-colors"
          />
        </div>
        <select
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value)}
          className="px-3 py-2 text-[13px] border border-border rounded-xl bg-white focus:outline-none focus:border-brand-primary"
        >
          <option value="">All Roles</option>
          {roles.map(r => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
      </div>

      {/* User grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filtered.map((user) => (
          <UserCard key={user.user_id} user={user} />
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="text-center py-12 text-text-placeholder text-sm">
          No users found
        </div>
      )}
    </div>
  )
}
