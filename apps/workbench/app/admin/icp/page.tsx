'use client'

import { useEffect, useState, useCallback } from 'react'
import { Target, RefreshCw } from 'lucide-react'
import { ICPProfileCard } from '../components/ICPProfileCard'
import { ICPSignalReviewRow } from '../components/ICPSignalReviewRow'
import { getICPLeaderboard } from '@/lib/api'
import { getAccessToken } from '@/lib/api'
import { API_BASE } from '@/lib/config'
import type { LeaderboardEntry } from '@/types/api'

type Tab = 'profiles' | 'signals' | 'leaderboard'

interface ICPProfile {
  id: string
  name: string
  description?: string | null
  is_active: boolean
  signal_patterns?: any
  scoring_criteria?: any
}

interface ICPSignal {
  id: string
  user_id: string
  event_name: string
  event_properties?: any
  confidence_score?: number
  routing_status?: string
}

async function fetchICP<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const token = getAccessToken()
  const res = await fetch(`${API_BASE}/v1/icp${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
    ...options,
  })
  if (!res.ok) throw new Error(`ICP API error: ${res.status}`)
  return res.json()
}

export default function AdminICPPage() {
  const [tab, setTab] = useState<Tab>('profiles')
  const [profiles, setProfiles] = useState<ICPProfile[]>([])
  const [signals, setSignals] = useState<ICPSignal[]>([])
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([])
  const [selectedProfile, setSelectedProfile] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [computing, setComputing] = useState(false)

  // Load profiles on mount
  useEffect(() => {
    fetchICP<ICPProfile[]>('/profiles?active_only=false')
      .then((data) => {
        setProfiles(data)
        if (data.length > 0) setSelectedProfile(data[0].id)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  // Load signals when on signals tab
  useEffect(() => {
    if (tab === 'signals') {
      fetchICP<ICPSignal[]>('/signals/review')
        .then(setSignals)
        .catch(console.error)
    }
  }, [tab])

  // Load leaderboard when profile selected
  useEffect(() => {
    if (tab === 'leaderboard' && selectedProfile) {
      getICPLeaderboard(selectedProfile)
        .then(setLeaderboard)
        .catch(console.error)
    }
  }, [tab, selectedProfile])

  const handleToggleActive = useCallback(async (id: string, active: boolean) => {
    try {
      await fetchICP(`/profiles/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({ is_active: active }),
      })
      setProfiles(prev => prev.map(p => p.id === id ? { ...p, is_active: active } : p))
    } catch (e) {
      console.error('Failed to toggle profile:', e)
    }
  }, [])

  const handleApproveSignal = useCallback(async (id: string) => {
    try {
      await fetchICP(`/signals/${id}/review`, {
        method: 'PATCH',
        body: JSON.stringify({ routing_status: 'approved' }),
      })
      setSignals(prev => prev.filter(s => s.id !== id))
    } catch (e) {
      console.error('Failed to approve signal:', e)
    }
  }, [])

  const handleDismissSignal = useCallback(async (id: string) => {
    try {
      await fetchICP(`/signals/${id}/review`, {
        method: 'PATCH',
        body: JSON.stringify({ routing_status: 'dismissed' }),
      })
      setSignals(prev => prev.filter(s => s.id !== id))
    } catch (e) {
      console.error('Failed to dismiss signal:', e)
    }
  }, [])

  const handleRecompute = useCallback(async () => {
    setComputing(true)
    try {
      await fetchICP('/scores/compute', { method: 'POST' })
      // Reload leaderboard
      if (selectedProfile) {
        const data = await getICPLeaderboard(selectedProfile)
        setLeaderboard(data)
      }
    } catch (e) {
      console.error('Failed to compute scores:', e)
    } finally {
      setComputing(false)
    }
  }, [selectedProfile])

  const tabs: { key: Tab; label: string }[] = [
    { key: 'profiles', label: 'Profiles' },
    { key: 'signals', label: 'Signal Queue' },
    { key: 'leaderboard', label: 'Leaderboard' },
  ]

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-5 h-5 border-2 border-[#3FAF7A] border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-[22px] font-bold text-[#333333]">ICP Management</h1>
      </div>

      {/* Tab bar */}
      <div className="flex items-center gap-1 border-b border-[#E5E5E5]">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2.5 text-[13px] transition-colors border-b-2 -mb-px ${
              tab === t.key
                ? 'text-[#3FAF7A] border-[#3FAF7A] font-medium'
                : 'text-[#666666] border-transparent hover:text-[#333333]'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'profiles' && (
        <div className="space-y-4">
          {profiles.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {profiles.map(p => (
                <ICPProfileCard key={p.id} profile={p} onToggleActive={handleToggleActive} />
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <Target className="w-10 h-10 text-[#E5E5E5] mx-auto mb-3" />
              <p className="text-[14px] text-[#666666]">No ICP profiles yet</p>
              <p className="text-[12px] text-[#999999] mt-1">Create one via the /icp/profiles API</p>
            </div>
          )}
        </div>
      )}

      {tab === 'signals' && (
        <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] overflow-hidden">
          {signals.length > 0 ? (
            <table className="w-full">
              <thead>
                <tr className="border-b border-[#E5E5E5] bg-[#F8F9FB]">
                  <th className="text-left text-[11px] text-[#999999] uppercase tracking-wide px-4 py-3">User</th>
                  <th className="text-left text-[11px] text-[#999999] uppercase tracking-wide px-4 py-3">Event</th>
                  <th className="text-left text-[11px] text-[#999999] uppercase tracking-wide px-4 py-3">Properties</th>
                  <th className="text-left text-[11px] text-[#999999] uppercase tracking-wide px-4 py-3">Confidence</th>
                  <th className="text-left text-[11px] text-[#999999] uppercase tracking-wide px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {signals.map(s => (
                  <ICPSignalReviewRow
                    key={s.id}
                    signal={s}
                    onApprove={handleApproveSignal}
                    onDismiss={handleDismissSignal}
                  />
                ))}
              </tbody>
            </table>
          ) : (
            <div className="text-center py-12 text-[#999999] text-sm">No signals pending review</div>
          )}
        </div>
      )}

      {tab === 'leaderboard' && (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <select
              value={selectedProfile}
              onChange={(e) => setSelectedProfile(e.target.value)}
              className="px-3 py-2 text-[13px] border border-[#E5E5E5] rounded-xl bg-white focus:outline-none focus:border-[#3FAF7A]"
            >
              {profiles.map(p => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
            <button
              onClick={handleRecompute}
              disabled={computing}
              className="flex items-center gap-2 px-4 py-2 text-[13px] bg-[#3FAF7A] text-white rounded-xl hover:bg-[#25785A] transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${computing ? 'animate-spin' : ''}`} />
              Recompute All
            </button>
          </div>

          <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] overflow-hidden">
            {leaderboard.length > 0 ? (
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[#E5E5E5] bg-[#F8F9FB]">
                    <th className="text-left text-[11px] text-[#999999] uppercase tracking-wide px-4 py-3 w-12">Rank</th>
                    <th className="text-left text-[11px] text-[#999999] uppercase tracking-wide px-4 py-3">User</th>
                    <th className="text-right text-[11px] text-[#999999] uppercase tracking-wide px-4 py-3">Score</th>
                    <th className="text-right text-[11px] text-[#999999] uppercase tracking-wide px-4 py-3">Signals</th>
                    <th className="text-left text-[11px] text-[#999999] uppercase tracking-wide px-4 py-3">Computed</th>
                  </tr>
                </thead>
                <tbody>
                  {leaderboard.map((entry) => (
                    <tr key={entry.user_id} className="border-b border-[#E5E5E5] hover:bg-[#F4F4F4] transition-colors">
                      <td className="px-4 py-3 text-[14px] font-semibold text-[#333333]">{entry.rank}</td>
                      <td className="px-4 py-3">
                        <a href={`/admin/users/${entry.user_id}`} className="text-[13px] text-[#3FAF7A] hover:underline">
                          {entry.name}
                        </a>
                        <div className="text-[11px] text-[#999999]">{entry.email}</div>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <div className="w-20 h-2 bg-[#E5E5E5] rounded-full overflow-hidden">
                            <div
                              className="h-full bg-[#3FAF7A] rounded-full"
                              style={{ width: `${Math.min(100, entry.score)}%` }}
                            />
                          </div>
                          <span className="text-[13px] font-medium text-[#333333] w-8">{entry.score}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-[13px] text-[#666666] text-right">{entry.signal_count}</td>
                      <td className="px-4 py-3 text-[12px] text-[#999999]">
                        {entry.computed_at ? new Date(entry.computed_at).toLocaleDateString() : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="text-center py-12 text-[#999999] text-sm">
                {selectedProfile ? 'No scores computed yet' : 'Select a profile'}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
