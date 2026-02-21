'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Activity, Heart, AlertTriangle, Settings, ChevronRight } from 'lucide-react'
import { MetricCard } from '../components/MetricCard'
import { getAdminProjectPulses, getAdminPulseConfigs } from '@/lib/api'
import type { AdminProjectPulse, AdminPulseConfigSummary } from '@/types/api'

const DIRECTIVE_COLORS: Record<string, string> = {
  stable: 'bg-[#3FAF7A]/15 text-[#25785A]',
  grow: 'bg-[#3B82F6]/15 text-[#1D4ED8]',
  enrich: 'bg-[#F59E0B]/15 text-[#92400E]',
  confirm: 'bg-[#F97316]/15 text-[#9A3412]',
  merge_only: 'bg-[#EF4444]/15 text-[#991B1B]',
}

const STAGE_COLORS: Record<string, string> = {
  discovery: 'bg-[#3FAF7A]/15 text-[#25785A]',
  validation: 'bg-[#3FAF7A]/15 text-[#25785A]',
  prototype: 'bg-[#3FAF7A]/20 text-[#25785A]',
  specification: 'bg-[#0A1E2F]/10 text-[#0A1E2F]',
  handoff: 'bg-[#0A1E2F]/15 text-[#0A1E2F]',
}

function formatScore(val: number) {
  return val >= 100 ? '100' : val.toFixed(0)
}

export default function AdminPulsePage() {
  const [projects, setProjects] = useState<AdminProjectPulse[]>([])
  const [configs, setConfigs] = useState<AdminPulseConfigSummary[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      getAdminProjectPulses().catch(() => []),
      getAdminPulseConfigs().catch(() => []),
    ])
      .then(([p, c]) => {
        setProjects(p)
        setConfigs(c)
      })
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-5 h-5 border-2 border-[#3FAF7A] border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  const avgHealth =
    projects.length > 0
      ? projects.reduce((sum, p) => {
          const scores = Object.values(p.health_scores)
          return sum + (scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : 0)
        }, 0) / projects.length
      : 0

  const totalSnapshots = projects.reduce((sum, p) => sum + p.snapshot_count, 0)
  const activeConfigs = configs.filter((c) => c.is_active).length
  const highRiskCount = projects.filter((p) => p.risk_score >= 50).length

  // Collect all entity types across projects for table headers
  const allEntityTypes = Array.from(
    new Set(projects.flatMap((p) => Object.keys(p.health_scores)))
  ).sort()

  return (
    <div className="space-y-6">
      <h1 className="text-[22px] font-bold text-[#333333]">Pulse Engine</h1>

      {/* Top stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard icon={Heart} value={formatScore(avgHealth)} label="Avg Health" />
        <MetricCard icon={Activity} value={totalSnapshots.toLocaleString()} label="Total Snapshots" />
        <MetricCard icon={Settings} value={activeConfigs} label="Active Configs" />
        <MetricCard
          icon={AlertTriangle}
          value={highRiskCount}
          label="High Risk"
        />
      </div>

      {/* Project heatmap table */}
      <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] p-6">
        <h2 className="text-[15px] font-semibold text-[#333333] mb-5">Project Health</h2>

        {projects.length === 0 ? (
          <p className="text-[13px] text-[#999999]">No projects with pulse data yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-[13px]">
              <thead>
                <tr className="border-b border-[#E5E5E5]">
                  <th className="text-left py-2 pr-3 text-[#999999] font-medium">Project</th>
                  <th className="text-left py-2 px-3 text-[#999999] font-medium">Stage</th>
                  {allEntityTypes.map((et) => (
                    <th key={et} className="text-center py-2 px-2 text-[#999999] font-medium whitespace-nowrap">
                      {et.replace('_', ' ')}
                    </th>
                  ))}
                  <th className="text-center py-2 px-3 text-[#999999] font-medium">Risk</th>
                  <th className="text-left py-2 px-3 text-[#999999] font-medium">Top Action</th>
                  <th className="text-center py-2 px-3 text-[#999999] font-medium">Snaps</th>
                  <th className="py-2 pl-3 w-8" />
                </tr>
              </thead>
              <tbody>
                {projects.map((proj) => (
                  <tr key={proj.project_id} className="border-b border-[#F4F4F4] hover:bg-[#FAFAFA] transition-colors">
                    <td className="py-2.5 pr-3 font-medium text-[#333333] max-w-[160px] truncate">
                      {proj.project_name || proj.project_id.slice(0, 8)}
                    </td>
                    <td className="py-2.5 px-3">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-[11px] font-medium ${STAGE_COLORS[proj.stage] || 'bg-[#E5E5E5] text-[#666666]'}`}>
                        {proj.stage}
                      </span>
                    </td>
                    {allEntityTypes.map((et) => {
                      const score = proj.health_scores[et]
                      return (
                        <td key={et} className="text-center py-2.5 px-2">
                          {score !== undefined ? (
                            <span
                              className="inline-block w-8 text-center font-mono text-[12px]"
                              style={{
                                color: score >= 70 ? '#25785A' : score >= 40 ? '#92400E' : '#991B1B',
                              }}
                            >
                              {formatScore(score)}
                            </span>
                          ) : (
                            <span className="text-[#E5E5E5]">—</span>
                          )}
                        </td>
                      )
                    })}
                    <td className="text-center py-2.5 px-3">
                      <span
                        className={`inline-block px-2 py-0.5 rounded-full text-[11px] font-medium ${
                          proj.risk_score >= 50
                            ? 'bg-[#EF4444]/15 text-[#991B1B]'
                            : proj.risk_score >= 20
                              ? 'bg-[#F59E0B]/15 text-[#92400E]'
                              : 'bg-[#3FAF7A]/15 text-[#25785A]'
                        }`}
                      >
                        {formatScore(proj.risk_score)}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-[#666666] max-w-[220px] truncate">
                      {proj.top_action || '—'}
                    </td>
                    <td className="text-center py-2.5 px-3 text-[#999999] font-mono">
                      {proj.snapshot_count}
                    </td>
                    <td className="py-2.5 pl-3">
                      <Link href={`/admin/pulse/${proj.project_id}`} className="text-[#3FAF7A] hover:text-[#25785A]">
                        <ChevronRight className="w-4 h-4" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Configs table */}
      <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] p-6">
        <h2 className="text-[15px] font-semibold text-[#333333] mb-5">Pulse Configs</h2>

        {configs.length === 0 ? (
          <p className="text-[13px] text-[#999999]">No custom configs — all projects using default v1.0.</p>
        ) : (
          <table className="w-full text-[13px]">
            <thead>
              <tr className="border-b border-[#E5E5E5]">
                <th className="text-left py-2 pr-3 text-[#999999] font-medium">Version</th>
                <th className="text-left py-2 px-3 text-[#999999] font-medium">Label</th>
                <th className="text-left py-2 px-3 text-[#999999] font-medium">Scope</th>
                <th className="text-center py-2 px-3 text-[#999999] font-medium">Active</th>
                <th className="text-left py-2 px-3 text-[#999999] font-medium">Created</th>
              </tr>
            </thead>
            <tbody>
              {configs.map((cfg) => (
                <tr key={cfg.id} className="border-b border-[#F4F4F4]">
                  <td className="py-2.5 pr-3 font-mono text-[#333333]">{cfg.version}</td>
                  <td className="py-2.5 px-3 text-[#666666]">{cfg.label || '—'}</td>
                  <td className="py-2.5 px-3 text-[#666666]">
                    {cfg.project_id ? `Project ${cfg.project_id.slice(0, 8)}…` : 'Global'}
                  </td>
                  <td className="text-center py-2.5 px-3">
                    {cfg.is_active ? (
                      <span className="inline-block w-2 h-2 rounded-full bg-[#3FAF7A]" />
                    ) : (
                      <span className="inline-block w-2 h-2 rounded-full bg-[#E5E5E5]" />
                    )}
                  </td>
                  <td className="py-2.5 px-3 text-[#999999]">
                    {cfg.created_at ? new Date(cfg.created_at).toLocaleDateString() : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
