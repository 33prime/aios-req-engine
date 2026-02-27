'use client'

import { useEffect, useState } from 'react'
import Image from 'next/image'
import Link from 'next/link'
import { Users, FolderOpen, Building2, Activity, DollarSign, User } from 'lucide-react'
import { MetricCard } from './components/MetricCard'
import { getAdminDashboard } from '@/lib/api'
import type { AdminDashboardStats } from '@/types/api'

export default function AdminDashboard() {
  const [stats, setStats] = useState<AdminDashboardStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getAdminDashboard()
      .then(setStats)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-5 h-5 border-2 border-brand-primary border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!stats) {
    return <div className="text-text-placeholder text-sm">Failed to load dashboard</div>
  }

  const stageEntries = Object.entries(stats.projects_by_stage).sort((a, b) => b[1] - a[1])
  const maxStage = Math.max(...stageEntries.map(([, v]) => v), 1)

  const roleEntries = Object.entries(stats.users_by_role).sort((a, b) => b[1] - a[1])
  const maxRole = Math.max(...roleEntries.map(([, v]) => v), 1)

  return (
    <div className="space-y-6">
      <h1 className="text-[22px] font-bold text-text-body">Dashboard</h1>

      {/* Metric cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-4">
        <MetricCard icon={Users} value={stats.total_users} label="Total Users" />
        <MetricCard icon={FolderOpen} value={stats.active_projects} label="Active Projects" />
        <MetricCard icon={Building2} value={stats.total_clients} label="Total Clients" />
        <MetricCard icon={Activity} value={stats.total_icp_signals} label="ICP Signals" />
        <MetricCard icon={DollarSign} value={`$${stats.total_cost_usd.toFixed(2)}`} label="LLM Spend" trend={`$${stats.cost_7d_usd.toFixed(2)} / 7d`} />
      </div>

      {/* Bottom row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Projects by Stage */}
        <div className="bg-white rounded-2xl shadow-md border border-border p-6">
          <h2 className="text-[15px] font-semibold text-text-body mb-4">Projects by Stage</h2>
          <div className="space-y-3">
            {stageEntries.map(([stage, count]) => (
              <div key={stage} className="flex items-center gap-3">
                <span className="text-[13px] text-[#666666] w-28 truncate">{stage}</span>
                <div className="flex-1 h-5 bg-border rounded-full overflow-hidden">
                  <div
                    className="h-full bg-brand-primary rounded-full transition-all"
                    style={{ width: `${(count / maxStage) * 100}%` }}
                  />
                </div>
                <span className="text-[13px] font-medium text-text-body w-8 text-right">{count}</span>
              </div>
            ))}
            {stageEntries.length === 0 && (
              <p className="text-[13px] text-text-placeholder">No projects yet</p>
            )}
          </div>
        </div>

        {/* Users by Role */}
        <div className="bg-white rounded-2xl shadow-md border border-border p-6">
          <h2 className="text-[15px] font-semibold text-text-body mb-4">Users by Role</h2>
          <div className="space-y-3">
            {roleEntries.map(([role, count]) => (
              <div key={role} className="flex items-center gap-3">
                <span className="text-[13px] text-[#666666] w-28 truncate">{role}</span>
                <div className="flex-1 h-5 bg-border rounded-full overflow-hidden">
                  <div
                    className="h-full bg-brand-primary rounded-full transition-all"
                    style={{ width: `${(count / maxRole) * 100}%` }}
                  />
                </div>
                <span className="text-[13px] font-medium text-text-body w-8 text-right">{count}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Signups */}
        <div className="bg-white rounded-2xl shadow-md border border-border p-6">
          <h2 className="text-[15px] font-semibold text-text-body mb-4">Recent Signups</h2>
          <div className="space-y-3">
            {stats.recent_signups.map((signup: any) => (
              <Link key={signup.user_id} href={`/admin/users/${signup.user_id}`} className="flex items-center justify-between hover:bg-[#F4F4F4] -mx-2 px-2 py-1 rounded-lg transition-colors">
                <div className="flex items-center gap-2.5">
                  <div className="w-7 h-7 rounded-full bg-gradient-to-br from-brand-primary to-[#25785A] flex items-center justify-center overflow-hidden flex-shrink-0">
                    {signup.photo_url ? (
                      <Image src={signup.photo_url} alt="" width={28} height={28} className="w-full h-full object-cover" />
                    ) : (
                      <User className="w-3 h-3 text-white" />
                    )}
                  </div>
                  <div>
                    <span className="text-[13px] text-text-body font-medium">{signup.name || signup.email?.split('@')[0]}</span>
                    {signup.email && <span className="text-[11px] text-text-placeholder ml-2">{signup.email}</span>}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 text-[11px] rounded-full bg-[#F0F0F0] text-[#666666]">
                    {signup.platform_role}
                  </span>
                  <span className="text-[11px] text-text-placeholder">
                    {new Date(signup.created_at).toLocaleDateString()}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* Quick Stats */}
        <div className="bg-white rounded-2xl shadow-md border border-border p-6">
          <h2 className="text-[15px] font-semibold text-text-body mb-4">Platform Summary</h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-[13px] text-[#666666]">Total Signals Processed</span>
              <span className="text-[15px] font-semibold text-text-body">{stats.total_signals.toLocaleString()}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[13px] text-[#666666]">Active Users (7d)</span>
              <span className="text-[15px] font-semibold text-text-body">{stats.active_users_7d}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[13px] text-[#666666]">Total Tokens Used</span>
              <span className="text-[15px] font-semibold text-text-body">{(stats.total_tokens / 1_000_000).toFixed(2)}M</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[13px] text-[#666666]">7-Day LLM Cost</span>
              <span className="text-[15px] font-semibold text-brand-primary">${stats.cost_7d_usd.toFixed(2)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
