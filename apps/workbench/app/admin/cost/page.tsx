'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import { DollarSign, Zap, Hash, User } from 'lucide-react'
import { MetricCard } from '../components/MetricCard'
import { getAdminCostAnalytics } from '@/lib/api'
import type { AdminCostAnalytics } from '@/types/api'

function formatCost(val: number) {
  return val < 0.01 && val > 0 ? '<$0.01' : `$${val.toFixed(2)}`
}

function formatTokens(val: number) {
  if (val > 1_000_000) return `${(val / 1_000_000).toFixed(1)}M`
  if (val > 1_000) return `${(val / 1_000).toFixed(1)}K`
  return val.toString()
}

export default function AdminCostPage() {
  const [data, setData] = useState<AdminCostAnalytics | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getAdminCostAnalytics()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-5 h-5 border-2 border-[#3FAF7A] border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!data) {
    return <div className="text-[#999999] text-sm">Failed to load cost data</div>
  }

  const maxWorkflowCost = Math.max(...data.cost_by_workflow.map(w => w.cost), 0.01)
  const totalWorkflowCost = data.cost_by_workflow.reduce((sum, w) => sum + w.cost, 0)
  const maxDailyCost = Math.max(...data.daily_cost.map(d => d.cost), 0.01)

  return (
    <div className="space-y-6">
      <h1 className="text-[22px] font-bold text-[#333333]">Cost & Usage</h1>

      {/* Top stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard icon={DollarSign} value={formatCost(data.total_cost_usd)} label="Total Spend" />
        <MetricCard icon={DollarSign} value={formatCost(data.daily_cost.reduce((sum, d) => sum + d.cost, 0))} label="Last 30 Days" />
        <MetricCard icon={Zap} value={formatTokens(data.total_tokens_input + data.total_tokens_output)} label="Total Tokens" />
        <MetricCard icon={Hash} value={data.total_calls.toLocaleString()} label="LLM Calls" />
      </div>

      {/* Cost by Workflow */}
      <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] p-6">
        <h2 className="text-[15px] font-semibold text-[#333333] mb-5">Cost by Workflow</h2>
        <div className="space-y-3">
          {data.cost_by_workflow.map((item) => {
            const pct = totalWorkflowCost > 0 ? ((item.cost / totalWorkflowCost) * 100).toFixed(0) : '0'
            return (
              <div key={item.workflow} className="flex items-center gap-4">
                <span className="text-[13px] text-[#666666] w-40 truncate font-mono">{item.workflow}</span>
                <div className="flex-1 h-5 bg-[#E5E5E5] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[#3FAF7A] rounded-full transition-all"
                    style={{ width: `${(item.cost / maxWorkflowCost) * 100}%` }}
                  />
                </div>
                <span className="text-[13px] font-medium text-[#333333] w-20 text-right">{formatCost(item.cost)}</span>
                <span className="text-[12px] text-[#999999] w-10 text-right">{pct}%</span>
              </div>
            )
          })}
          {data.cost_by_workflow.length === 0 && (
            <p className="text-[13px] text-[#999999]">No usage data yet</p>
          )}
        </div>
      </div>

      {/* Two-column: Model + Top Spenders */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Cost by Model */}
        <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] p-6">
          <h2 className="text-[15px] font-semibold text-[#333333] mb-4">Cost by Model</h2>
          <div className="space-y-3">
            {data.cost_by_model.map((item) => (
              <div key={item.model} className="flex items-center justify-between p-3 rounded-xl border border-[#E5E5E5] bg-[#F8F9FB]">
                <div>
                  <div className="text-[13px] font-medium text-[#333333]">{item.model}</div>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="px-1.5 py-0.5 text-[10px] rounded bg-[#F0F0F0] text-[#666666]">{item.provider}</span>
                    <span className="text-[11px] text-[#999999]">{item.calls} calls</span>
                    <span className="text-[11px] text-[#999999]">{formatTokens(item.tokens)} tokens</span>
                  </div>
                </div>
                <span className="text-[15px] font-semibold text-[#333333]">{formatCost(item.cost)}</span>
              </div>
            ))}
            {data.cost_by_model.length === 0 && (
              <p className="text-[13px] text-[#999999]">No model data</p>
            )}
          </div>
        </div>

        {/* Top Spenders */}
        <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] p-6">
          <h2 className="text-[15px] font-semibold text-[#333333] mb-4">Top Spenders</h2>
          <div className="overflow-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[#E5E5E5]">
                  <th className="text-left text-[10px] text-[#999999] uppercase pb-2 pr-3">#</th>
                  <th className="text-left text-[10px] text-[#999999] uppercase pb-2 pr-3">User</th>
                  <th className="text-right text-[10px] text-[#999999] uppercase pb-2 pr-3">Cost</th>
                  <th className="text-right text-[10px] text-[#999999] uppercase pb-2">Calls</th>
                </tr>
              </thead>
              <tbody>
                {data.cost_by_user.map((item, i) => (
                  <tr key={item.user_id} className="border-b border-[#E5E5E5] hover:bg-[#F4F4F4] transition-colors">
                    <td className="py-2 pr-3 text-[12px] text-[#999999]">{i + 1}</td>
                    <td className="py-2 pr-3">
                      {item.user_id !== 'system' ? (
                        <Link href={`/admin/users/${item.user_id}`} className="text-[13px] text-[#3FAF7A] hover:underline">
                          {item.name || item.email}
                        </Link>
                      ) : (
                        <span className="text-[13px] text-[#666666]">System</span>
                      )}
                    </td>
                    <td className="py-2 pr-3 text-[13px] font-medium text-[#333333] text-right">{formatCost(item.cost)}</td>
                    <td className="py-2 text-[12px] text-[#999999] text-right">{item.calls}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {data.cost_by_user.length === 0 && (
            <p className="text-[13px] text-[#999999]">No user data</p>
          )}
        </div>
      </div>

      {/* Daily Spend Chart */}
      {data.daily_cost.length > 0 && (
        <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] p-6">
          <h2 className="text-[15px] font-semibold text-[#333333] mb-4">Daily Spend (30 Days)</h2>
          <div className="flex items-end gap-1 h-40">
            {data.daily_cost.map((day, i) => {
              const heightPct = (day.cost / maxDailyCost) * 100
              return (
                <div key={day.date} className="flex-1 flex flex-col items-center justify-end group relative">
                  <div
                    className="w-full bg-[#3FAF7A] rounded-t-sm min-h-[2px] transition-all hover:bg-[#25785A]"
                    style={{ height: `${Math.max(heightPct, 1)}%` }}
                    title={`${day.date}: ${formatCost(day.cost)} (${day.calls} calls)`}
                  />
                  {/* Label every 5 days */}
                  {i % 5 === 0 && (
                    <span className="text-[9px] text-[#999999] mt-1 whitespace-nowrap">
                      {day.date.slice(5)}
                    </span>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
