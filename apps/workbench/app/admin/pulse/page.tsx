'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Activity, Heart, AlertTriangle, Settings, ChevronRight } from 'lucide-react'
import { MetricCard } from '../components/MetricCard'
import { getAdminProjectPulses, getAdminPulseConfigs } from '@/lib/api'
import type { AdminProjectPulse, AdminPulseConfigSummary } from '@/types/api'

const STAGE_COLORS: Record<string, string> = {
  discovery: 'bg-brand-primary/15 text-[#25785A]',
  validation: 'bg-brand-primary/15 text-[#25785A]',
  prototype: 'bg-brand-primary/20 text-[#25785A]',
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
      getAdminProjectPulses().catch((e) => { console.error('Pulse projects:', e); return [] }),
      getAdminPulseConfigs().catch((e) => { console.error('Pulse configs:', e); return [] }),
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
        <div className="w-5 h-5 border-2 border-brand-primary border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  // Split projects into those with pulse data vs awaiting
  const activeProjects = projects.filter((p) => p.snapshot_count > 0)
  const pendingProjects = projects.filter((p) => p.snapshot_count === 0)

  const avgHealth =
    activeProjects.length > 0
      ? activeProjects.reduce((sum, p) => {
          const scores = Object.values(p.health_scores)
          return sum + (scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : 0)
        }, 0) / activeProjects.length
      : 0

  const totalSnapshots = projects.reduce((sum, p) => sum + p.snapshot_count, 0)
  const activeConfigs = configs.filter((c) => c.is_active).length
  const highRiskCount = activeProjects.filter((p) => p.risk_score >= 50).length

  // Collect all entity types across active projects for table headers
  const allEntityTypes = Array.from(
    new Set(activeProjects.flatMap((p) => Object.keys(p.health_scores)))
  ).sort()

  return (
    <div className="space-y-6">
      <h1 className="text-[22px] font-bold text-text-body">Pulse Engine</h1>

      {/* Top stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard icon={Heart} value={formatScore(avgHealth)} label="Avg Health" />
        <MetricCard icon={Activity} value={totalSnapshots.toLocaleString()} label="Total Snapshots" />
        <MetricCard icon={Settings} value={activeConfigs || 'Default'} label="Active Configs" />
        <MetricCard icon={AlertTriangle} value={highRiskCount} label="High Risk" />
      </div>

      {/* Active projects heatmap */}
      <div className="bg-white rounded-2xl shadow-md border border-border p-6">
        <h2 className="text-[15px] font-semibold text-text-body mb-5">Project Health</h2>

        {activeProjects.length === 0 ? (
          <div className="text-center py-8">
            <Activity className="w-8 h-8 text-border mx-auto mb-3" />
            <p className="text-[13px] text-text-placeholder mb-1">No pulse snapshots yet</p>
            <p className="text-[12px] text-[#CCCCCC]">
              Snapshots are recorded when signals are processed or entities are confirmed.
              You can also trigger one via the API: GET /projects/:id/pulse
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-[13px]">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-2 pr-3 text-text-placeholder font-medium">Project</th>
                  <th className="text-left py-2 px-3 text-text-placeholder font-medium">Stage</th>
                  {allEntityTypes.map((et) => (
                    <th key={et} className="text-center py-2 px-2 text-text-placeholder font-medium whitespace-nowrap">
                      {et.replace(/_/g, ' ')}
                    </th>
                  ))}
                  <th className="text-center py-2 px-3 text-text-placeholder font-medium">Risk</th>
                  <th className="text-left py-2 px-3 text-text-placeholder font-medium">Top Action</th>
                  <th className="text-center py-2 px-3 text-text-placeholder font-medium">Snaps</th>
                  <th className="py-2 pl-3 w-8" />
                </tr>
              </thead>
              <tbody>
                {activeProjects.map((proj) => (
                  <tr key={proj.project_id} className="border-b border-[#F4F4F4] hover:bg-surface-page transition-colors">
                    <td className="py-2.5 pr-3 font-medium text-text-body max-w-[160px] truncate">
                      {proj.project_name || proj.project_id.slice(0, 8)}
                    </td>
                    <td className="py-2.5 px-3">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-[11px] font-medium ${STAGE_COLORS[proj.stage] || 'bg-border text-[#666666]'}`}>
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
                            <span className="text-border">—</span>
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
                              : 'bg-brand-primary/15 text-[#25785A]'
                        }`}
                      >
                        {formatScore(proj.risk_score)}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-[#666666] max-w-[220px] truncate">
                      {proj.top_action || '—'}
                    </td>
                    <td className="text-center py-2.5 px-3 text-text-placeholder font-mono">
                      {proj.snapshot_count}
                    </td>
                    <td className="py-2.5 pl-3">
                      <Link href={`/admin/pulse/${proj.project_id}`} className="text-brand-primary hover:text-[#25785A]">
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

      {/* Pending projects */}
      {pendingProjects.length > 0 && (
        <div className="bg-white rounded-2xl shadow-md border border-border p-6">
          <h2 className="text-[15px] font-semibold text-text-body mb-3">
            Awaiting First Signal
            <span className="text-[12px] font-normal text-text-placeholder ml-2">{pendingProjects.length} projects</span>
          </h2>
          <div className="flex flex-wrap gap-2">
            {pendingProjects.map((proj) => (
              <span key={proj.project_id} className="px-3 py-1.5 bg-[#F4F4F4] rounded-lg text-[12px] text-[#666666]">
                {proj.project_name || proj.project_id.slice(0, 8)}
                <span className={`ml-2 px-1.5 py-0.5 rounded-full text-[10px] font-medium ${STAGE_COLORS[proj.stage] || 'bg-border text-[#666666]'}`}>
                  {proj.stage}
                </span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Configs table */}
      <div className="bg-white rounded-2xl shadow-md border border-border p-6">
        <h2 className="text-[15px] font-semibold text-text-body mb-5">Pulse Configs</h2>

        {configs.length === 0 ? (
          <p className="text-[13px] text-text-placeholder">No custom configs — all projects using default v1.0.</p>
        ) : (
          <table className="w-full text-[13px]">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-2 pr-3 text-text-placeholder font-medium">Version</th>
                <th className="text-left py-2 px-3 text-text-placeholder font-medium">Label</th>
                <th className="text-left py-2 px-3 text-text-placeholder font-medium">Scope</th>
                <th className="text-center py-2 px-3 text-text-placeholder font-medium">Active</th>
                <th className="text-left py-2 px-3 text-text-placeholder font-medium">Created</th>
              </tr>
            </thead>
            <tbody>
              {configs.map((cfg) => (
                <tr key={cfg.id} className="border-b border-[#F4F4F4]">
                  <td className="py-2.5 pr-3 font-mono text-text-body">{cfg.version}</td>
                  <td className="py-2.5 px-3 text-[#666666]">{cfg.label || '—'}</td>
                  <td className="py-2.5 px-3 text-[#666666]">
                    {cfg.project_id ? `Project ${cfg.project_id.slice(0, 8)}…` : 'Global'}
                  </td>
                  <td className="text-center py-2.5 px-3">
                    {cfg.is_active ? (
                      <span className="inline-block w-2 h-2 rounded-full bg-brand-primary" />
                    ) : (
                      <span className="inline-block w-2 h-2 rounded-full bg-border" />
                    )}
                  </td>
                  <td className="py-2.5 px-3 text-text-placeholder">
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
