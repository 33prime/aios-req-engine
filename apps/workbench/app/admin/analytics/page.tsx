'use client'

import { useEffect, useState } from 'react'
import { BarChart3, Users, Activity } from 'lucide-react'
import { MetricCard } from '../components/MetricCard'
import { getAdminDashboard } from '@/lib/api'
import type { AdminDashboardStats } from '@/types/api'

const POSTHOG_DASHBOARD_URL = process.env.NEXT_PUBLIC_POSTHOG_DASHBOARD_URL

export default function AdminAnalyticsPage() {
  const [stats, setStats] = useState<AdminDashboardStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getAdminDashboard()
      .then(setStats)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-6">
      <h1 className="text-[22px] font-bold text-[#333333]">Analytics</h1>

      {/* Platform metrics */}
      {!loading && stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <MetricCard icon={Users} value={stats.active_users_7d} label="Active Users (7d)" />
          <MetricCard icon={Activity} value={stats.total_icp_signals} label="ICP Signals" />
          <MetricCard icon={BarChart3} value={stats.total_signals} label="Total Events" />
        </div>
      )}

      {/* PostHog Dashboard */}
      <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] overflow-hidden">
        <div className="px-6 py-4 border-b border-[#E5E5E5]">
          <h2 className="text-[15px] font-semibold text-[#333333]">PostHog Dashboard</h2>
        </div>

        {POSTHOG_DASHBOARD_URL ? (
          <iframe
            src={POSTHOG_DASHBOARD_URL}
            className="w-full border-0"
            style={{ height: 800 }}
            title="PostHog Analytics Dashboard"
          />
        ) : (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <BarChart3 className="w-10 h-10 text-[#E5E5E5] mb-4" />
            <p className="text-[14px] text-[#666666] mb-1">PostHog dashboard not configured</p>
            <p className="text-[12px] text-[#999999]">
              Set <code className="px-1.5 py-0.5 bg-[#F0F0F0] rounded text-[11px]">NEXT_PUBLIC_POSTHOG_DASHBOARD_URL</code> to embed your PostHog dashboard here
            </p>
          </div>
        )}
      </div>

      {/* ICP Signal Pipeline */}
      {!loading && stats && (
        <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] p-6">
          <h2 className="text-[15px] font-semibold text-[#333333] mb-4">Signal Pipeline</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div>
              <div className="text-[22px] font-bold text-[#333333]">{stats.total_signals.toLocaleString()}</div>
              <div className="text-[11px] text-[#999999] uppercase">Total Signals</div>
            </div>
            <div>
              <div className="text-[22px] font-bold text-[#333333]">{stats.total_icp_signals.toLocaleString()}</div>
              <div className="text-[11px] text-[#999999] uppercase">ICP Signals</div>
            </div>
            <div>
              <div className="text-[22px] font-bold text-[#333333]">{stats.total_users}</div>
              <div className="text-[11px] text-[#999999] uppercase">Total Users</div>
            </div>
            <div>
              <div className="text-[22px] font-bold text-[#333333]">{stats.active_users_7d}</div>
              <div className="text-[11px] text-[#999999] uppercase">Active (7d)</div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
