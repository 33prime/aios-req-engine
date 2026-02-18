'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Image from 'next/image'
import Link from 'next/link'
import {
  ArrowLeft,
  User,
  MapPin,
  Linkedin,
  Calendar,
  Clock,
  FileText,
  Zap,
  DollarSign,
} from 'lucide-react'
import { getAdminUserDetail, updateUserRole } from '@/lib/api'
import type { AdminUserDetail } from '@/types/api'

function formatCost(val: number) {
  return val < 0.01 ? '<$0.01' : `$${val.toFixed(2)}`
}

function formatTokens(val: number) {
  if (val > 1_000_000) return `${(val / 1_000_000).toFixed(1)}M`
  if (val > 1_000) return `${(val / 1_000).toFixed(1)}K`
  return val.toString()
}

function timeAgo(dateStr: string) {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

export default function AdminUserDetailPage() {
  const params = useParams()
  const router = useRouter()
  const userId = params.id as string

  const [data, setData] = useState<AdminUserDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [roleEditing, setRoleEditing] = useState(false)

  useEffect(() => {
    getAdminUserDetail(userId)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [userId])

  const handleRoleChange = async (newRole: string) => {
    try {
      await updateUserRole(userId, newRole)
      setData(prev => prev ? { ...prev, profile: { ...prev.profile, platform_role: newRole } } : prev)
      setRoleEditing(false)
    } catch (e) {
      console.error('Failed to update role:', e)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-5 h-5 border-2 border-[#3FAF7A] border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!data) {
    return <div className="text-[#999999] text-sm">User not found</div>
  }

  const profile = data.profile
  const displayName = [profile.first_name, profile.last_name].filter(Boolean).join(' ') || profile.email?.split('@')[0]

  const costEntries = Object.entries(data.cost_by_workflow).sort(([, a], [, b]) => b - a)
  const maxWorkflowCost = Math.max(...costEntries.map(([, v]) => v), 0.01)

  return (
    <div className="space-y-6">
      {/* Back */}
      <button
        onClick={() => router.push('/admin/users')}
        className="flex items-center gap-1.5 text-[13px] text-[#666666] hover:text-[#333333] transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Users
      </button>

      {/* Header card */}
      <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] p-6">
        <div className="flex items-start gap-5">
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-[#3FAF7A] to-[#25785A] flex items-center justify-center overflow-hidden flex-shrink-0">
            {profile.photo_url ? (
              <Image src={profile.photo_url} alt={displayName} width={64} height={64} className="w-full h-full object-cover" />
            ) : (
              <User className="w-8 h-8 text-white" />
            )}
          </div>

          <div className="flex-1">
            <div className="flex items-center gap-3">
              <h1 className="text-[22px] font-bold text-[#333333]">{displayName}</h1>
              {roleEditing ? (
                <select
                  defaultValue={profile.platform_role}
                  onChange={(e) => handleRoleChange(e.target.value)}
                  onBlur={() => setRoleEditing(false)}
                  autoFocus
                  className="px-2 py-0.5 text-[12px] border border-[#E5E5E5] rounded-lg bg-white focus:outline-none focus:border-[#3FAF7A]"
                >
                  <option value="consultant">consultant</option>
                  <option value="sales_consultant">sales_consultant</option>
                  <option value="solution_architect">solution_architect</option>
                  <option value="super_admin">super_admin</option>
                </select>
              ) : (
                <button
                  onClick={() => setRoleEditing(true)}
                  className="px-2.5 py-0.5 text-[11px] rounded-full bg-[#F0F0F0] text-[#666666] hover:bg-[#E5E5E5] transition-colors"
                >
                  {profile.platform_role}
                </button>
              )}
            </div>
            <p className="text-[14px] text-[#666666] mt-0.5">{profile.email}</p>

            <div className="flex items-center gap-4 mt-2 text-[12px] text-[#999999]">
              {(profile.city || profile.state || profile.country) && (
                <span className="flex items-center gap-1">
                  <MapPin className="w-3 h-3" />
                  {[profile.city, profile.state, profile.country].filter(Boolean).join(', ')}
                </span>
              )}
              {profile.linkedin && (
                <a href={profile.linkedin} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-[#3FAF7A] hover:underline">
                  <Linkedin className="w-3 h-3" />
                  LinkedIn
                </a>
              )}
              <span className="flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                Joined {new Date(profile.created_at).toLocaleDateString()}
              </span>
              {profile.updated_at && (
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  Active {timeAgo(profile.updated_at)}
                </span>
              )}
            </div>
          </div>

          {/* Profile completeness circle */}
          <div className="flex flex-col items-center gap-1">
            <div className="relative w-14 h-14">
              <svg className="w-14 h-14 transform -rotate-90" viewBox="0 0 36 36">
                <path
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none"
                  stroke="#E5E5E5"
                  strokeWidth="3"
                />
                <path
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none"
                  stroke="#3FAF7A"
                  strokeWidth="3"
                  strokeDasharray={`${profile.profile_completeness || 0}, 100`}
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-[12px] font-semibold text-[#333333]">{profile.profile_completeness || 0}%</span>
              </div>
            </div>
            <span className="text-[10px] text-[#999999]">Profile</span>
          </div>
        </div>
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column (1/3) */}
        <div className="space-y-6">
          {/* Identity & Expertise */}
          <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] p-6">
            <h2 className="text-[15px] font-semibold text-[#333333] mb-4">Identity & Expertise</h2>

            {profile.bio && (
              <p className="text-[13px] text-[#666666] mb-3">{profile.bio}</p>
            )}

            {profile.expertise_areas?.length > 0 && (
              <div className="mb-3">
                <span className="text-[11px] text-[#999999] uppercase tracking-wide">Expertise</span>
                <div className="flex flex-wrap gap-1.5 mt-1">
                  {profile.expertise_areas.map((area: string) => (
                    <span key={area} className="px-2 py-0.5 text-[11px] rounded-full bg-[#F0F0F0] text-[#666666]">
                      {area}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {!profile.bio && !profile.expertise_areas?.length && (
              <p className="text-[13px] text-[#999999]">No profile data yet</p>
            )}
          </div>

          {/* AI Enrichment */}
          {data.enriched_profile && (
            <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] p-6">
              <h2 className="text-[15px] font-semibold text-[#333333] mb-4">AI Enrichment</h2>

              <span className={`px-2 py-0.5 text-[11px] rounded-full mb-3 inline-block ${
                profile.enrichment_status === 'completed'
                  ? 'bg-[#E8F5E9] text-[#25785A]'
                  : 'bg-[#F0F0F0] text-[#666666]'
              }`}>
                {profile.enrichment_status === 'completed' ? 'Enriched' : profile.enrichment_status || 'Pending'}
              </span>

              {data.enriched_profile.consultant_summary && (
                <p className="text-[13px] text-[#666666] mt-2 mb-3">{data.enriched_profile.consultant_summary}</p>
              )}

              {data.enriched_profile.industry_expertise?.length ? (
                <div className="mb-2">
                  <span className="text-[11px] text-[#999999] uppercase tracking-wide">Industry</span>
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    {data.enriched_profile.industry_expertise.map((item: string) => (
                      <span key={item} className="px-2 py-0.5 text-[11px] rounded-full bg-[#E8F5E9] text-[#25785A]">{item}</span>
                    ))}
                  </div>
                </div>
              ) : null}

              {data.enriched_profile.methodology_expertise?.length ? (
                <div>
                  <span className="text-[11px] text-[#999999] uppercase tracking-wide">Methodology</span>
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    {data.enriched_profile.methodology_expertise.map((item: string) => (
                      <span key={item} className="px-2 py-0.5 text-[11px] rounded-full bg-[#F0F0F0] text-[#666666]">{item}</span>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          )}

          {/* ICP Fit Scores */}
          {data.icp_scores.length > 0 && (
            <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] p-6">
              <h2 className="text-[15px] font-semibold text-[#333333] mb-4">ICP Fit Scores</h2>
              <div className="space-y-3">
                {data.icp_scores.map((score, i) => (
                  <div key={i}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[13px] text-[#666666]">{score.profile_name}</span>
                      <span className="text-[13px] font-medium text-[#333333]">{score.score}/100</span>
                    </div>
                    <div className="w-full h-2 bg-[#E5E5E5] rounded-full overflow-hidden">
                      <div
                        className="h-full bg-[#3FAF7A] rounded-full"
                        style={{ width: `${Math.min(100, score.score)}%` }}
                      />
                    </div>
                    <span className="text-[11px] text-[#999999]">{score.signal_count} signals</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right column (2/3) */}
        <div className="lg:col-span-2 space-y-6">
          {/* Projects */}
          <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] p-6">
            <h2 className="text-[15px] font-semibold text-[#333333] mb-4">Projects</h2>
            {data.projects.length > 0 ? (
              <div className="overflow-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-[#E5E5E5]">
                      <th className="text-left text-[11px] text-[#999999] uppercase tracking-wide pb-2 pr-4">Name</th>
                      <th className="text-left text-[11px] text-[#999999] uppercase tracking-wide pb-2 pr-4">Client</th>
                      <th className="text-left text-[11px] text-[#999999] uppercase tracking-wide pb-2 pr-4">Stage</th>
                      <th className="text-left text-[11px] text-[#999999] uppercase tracking-wide pb-2 pr-4">Status</th>
                      <th className="text-left text-[11px] text-[#999999] uppercase tracking-wide pb-2">Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.projects.map((project) => (
                      <tr key={project.id} className="border-b border-[#E5E5E5] hover:bg-[#F4F4F4] transition-colors">
                        <td className="py-2.5 pr-4">
                          <Link href={`/projects/${project.id}`} className="text-[13px] text-[#3FAF7A] hover:underline">
                            {project.name}
                          </Link>
                        </td>
                        <td className="py-2.5 pr-4 text-[13px] text-[#666666]">{project.client_name || '-'}</td>
                        <td className="py-2.5 pr-4 text-[13px] text-[#666666]">{project.stage || '-'}</td>
                        <td className="py-2.5 pr-4">
                          <span className="px-2 py-0.5 text-[11px] rounded-full bg-[#F0F0F0] text-[#666666]">
                            {project.status || 'active'}
                          </span>
                        </td>
                        <td className="py-2.5 text-[12px] text-[#999999]">{new Date(project.created_at).toLocaleDateString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-[13px] text-[#999999]">No projects yet</p>
            )}
          </div>

          {/* Signal Breakdown */}
          <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] p-6">
            <h2 className="text-[15px] font-semibold text-[#333333] mb-4">Signal Breakdown</h2>
            <div className="flex items-center gap-4 mb-4">
              <span className="text-[13px] text-[#666666]">
                Total: <span className="font-semibold text-[#333333]">{data.total_signals_submitted}</span> signals
              </span>
              <span className="text-[13px] text-[#666666]">
                Entities generated: <span className="font-semibold text-[#333333]">{data.total_entities_generated}</span>
              </span>
            </div>
            {Object.entries(data.signals_by_type).length > 0 ? (
              <div className="space-y-2">
                {Object.entries(data.signals_by_type).sort(([, a], [, b]) => b - a).map(([type, count]) => (
                  <div key={type} className="flex items-center gap-3">
                    <span className="text-[13px] text-[#666666] w-24 truncate">{type}</span>
                    <div className="flex-1 h-4 bg-[#E5E5E5] rounded-full overflow-hidden">
                      <div
                        className="h-full bg-[#3FAF7A] rounded-full"
                        style={{ width: `${(count / Math.max(...Object.values(data.signals_by_type), 1)) * 100}%` }}
                      />
                    </div>
                    <span className="text-[13px] font-medium text-[#333333] w-8 text-right">{count}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-[13px] text-[#999999]">No signals yet</p>
            )}
          </div>

          {/* LLM Cost & Usage */}
          <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] p-6">
            <h2 className="text-[15px] font-semibold text-[#333333] mb-4">LLM Cost & Usage</h2>

            {/* Summary stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div>
                <div className="text-[22px] font-bold text-[#333333]">{formatCost(data.total_cost_usd)}</div>
                <div className="text-[11px] text-[#999999] uppercase">Total Spend</div>
              </div>
              <div>
                <div className="text-[22px] font-bold text-[#333333]">{formatCost(data.cost_30d_usd)}</div>
                <div className="text-[11px] text-[#999999] uppercase">30-Day Spend</div>
              </div>
              <div>
                <div className="text-[22px] font-bold text-[#333333]">{formatTokens(data.total_tokens_input)}</div>
                <div className="text-[11px] text-[#999999] uppercase">Input Tokens</div>
              </div>
              <div>
                <div className="text-[22px] font-bold text-[#333333]">{formatTokens(data.total_tokens_output)}</div>
                <div className="text-[11px] text-[#999999] uppercase">Output Tokens</div>
              </div>
            </div>

            {/* Cost by workflow */}
            {costEntries.length > 0 && (
              <>
                <h3 className="text-[13px] font-medium text-[#666666] mb-3">Cost by Workflow</h3>
                <div className="space-y-2 mb-6">
                  {costEntries.map(([workflow, cost]) => (
                    <div key={workflow} className="flex items-center gap-3">
                      <span className="text-[12px] text-[#666666] w-36 truncate font-mono">{workflow}</span>
                      <div className="flex-1 h-4 bg-[#E5E5E5] rounded-full overflow-hidden">
                        <div
                          className="h-full bg-[#3FAF7A] rounded-full"
                          style={{ width: `${(cost / maxWorkflowCost) * 100}%` }}
                        />
                      </div>
                      <span className="text-[12px] font-medium text-[#333333] w-16 text-right">{formatCost(cost)}</span>
                    </div>
                  ))}
                </div>
              </>
            )}

            {/* Cost by model */}
            {Object.keys(data.cost_by_model).length > 0 && (
              <>
                <h3 className="text-[13px] font-medium text-[#666666] mb-3">Cost by Model</h3>
                <div className="flex flex-wrap gap-2 mb-6">
                  {Object.entries(data.cost_by_model).sort(([, a], [, b]) => b - a).map(([model, cost]) => (
                    <span key={model} className="px-2.5 py-1 text-[11px] rounded-full bg-[#F0F0F0] text-[#666666]">
                      {model.replace(/^claude-/, 'c-').replace(/^gpt-/, 'g-')}: {formatCost(cost)}
                    </span>
                  ))}
                </div>
              </>
            )}

            {/* Recent LLM calls */}
            {data.recent_llm_calls.length > 0 && (
              <>
                <h3 className="text-[13px] font-medium text-[#666666] mb-3">Recent LLM Calls</h3>
                <div className="overflow-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-[#E5E5E5]">
                        <th className="text-left text-[10px] text-[#999999] uppercase pb-2 pr-3">Workflow</th>
                        <th className="text-left text-[10px] text-[#999999] uppercase pb-2 pr-3">Model</th>
                        <th className="text-right text-[10px] text-[#999999] uppercase pb-2 pr-3">Tokens</th>
                        <th className="text-right text-[10px] text-[#999999] uppercase pb-2 pr-3">Cost</th>
                        <th className="text-right text-[10px] text-[#999999] uppercase pb-2">Time</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.recent_llm_calls.slice(0, 10).map((call, i) => (
                        <tr key={i} className="border-b border-[#E5E5E5]">
                          <td className="py-1.5 pr-3 text-[12px] text-[#333333] font-mono">{call.workflow}</td>
                          <td className="py-1.5 pr-3 text-[11px] text-[#666666]">{(call.model || '').slice(0, 20)}</td>
                          <td className="py-1.5 pr-3 text-[11px] text-[#999999] text-right">{formatTokens((call.tokens_input || 0) + (call.tokens_output || 0))}</td>
                          <td className="py-1.5 pr-3 text-[11px] text-[#333333] text-right">{formatCost(call.estimated_cost_usd || 0)}</td>
                          <td className="py-1.5 text-[11px] text-[#999999] text-right">{call.created_at ? timeAgo(call.created_at) : '-'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}

            {costEntries.length === 0 && data.recent_llm_calls.length === 0 && (
              <p className="text-[13px] text-[#999999]">No LLM usage recorded yet</p>
            )}
          </div>

          {/* Recent Activity */}
          <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] p-6">
            <h2 className="text-[15px] font-semibold text-[#333333] mb-4">Recent Signals</h2>
            {data.recent_signals.length > 0 ? (
              <div className="space-y-3">
                {data.recent_signals.map((signal) => (
                  <div key={signal.id} className="flex items-center gap-3">
                    <div className="p-1.5 rounded-lg bg-[#F0F0F0]">
                      <FileText className="w-3.5 h-3.5 text-[#666666]" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <span className="text-[13px] text-[#333333]">{signal.source_type || 'signal'}</span>
                      <span className="text-[12px] text-[#999999] ml-2">{signal.project_id?.slice(0, 8)}</span>
                    </div>
                    <span className="text-[11px] text-[#999999]">{signal.created_at ? timeAgo(signal.created_at) : '-'}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-[13px] text-[#999999]">No recent signals</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
