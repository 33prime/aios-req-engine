'use client'

import { useEffect, useState } from 'react'
import { Activity, CheckCircle, BarChart3, DollarSign, RefreshCw } from 'lucide-react'
import { MetricCard } from '../../components/MetricCard'
import { ScoreTrendChart } from './ScoreTrendChart'
import { TopGapsChart } from './TopGapsChart'
import { VersionDistributionChart } from './VersionDistributionChart'
import { getEvalDashboard } from '@/lib/api'
import type { EvalDashboardStats } from '@/types/api'

export function EvalDashboard() {
  const [stats, setStats] = useState<EvalDashboardStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getEvalDashboard()
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
    return <div className="text-text-placeholder text-sm">Failed to load eval dashboard</div>
  }

  return (
    <div className="space-y-6">
      {/* KPI cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-4">
        <MetricCard icon={Activity} value={stats.total_runs} label="Total Runs" />
        <MetricCard
          icon={BarChart3}
          value={`${(stats.avg_score * 100).toFixed(1)}%`}
          label="Avg Score"
        />
        <MetricCard
          icon={CheckCircle}
          value={`${(stats.first_pass_rate * 100).toFixed(0)}%`}
          label="First Pass Rate"
        />
        <MetricCard
          icon={RefreshCw}
          value={stats.avg_iterations.toFixed(1)}
          label="Avg Iterations"
        />
        <MetricCard
          icon={DollarSign}
          value={`$${stats.total_cost_usd.toFixed(2)}`}
          label="Eval Cost"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-2xl shadow-md border border-border p-6">
          <h2 className="text-[15px] font-semibold text-text-body mb-4">Score Trend</h2>
          <ScoreTrendChart data={stats.score_trend} />
        </div>

        <div className="bg-white rounded-2xl shadow-md border border-border p-6">
          <h2 className="text-[15px] font-semibold text-text-body mb-4">Top Unresolved Gaps</h2>
          <TopGapsChart data={stats.top_gaps} />
        </div>

        <div className="bg-white rounded-2xl shadow-md border border-border p-6">
          <h2 className="text-[15px] font-semibold text-text-body mb-4">
            Outcome Distribution
          </h2>
          <VersionDistributionChart data={stats.version_distribution} />
        </div>
      </div>
    </div>
  )
}
