'use client'

import { useState, useEffect } from 'react'
import { Brain, Database, BarChart3, GitBranch, Bot } from 'lucide-react'
import { SectionHeader } from '../components/SectionHeader'
import { API_V1 } from '@/lib/config'

interface IntelligenceItem {
  id: string
  name: string
  description: string
  quadrant: 'knowledge' | 'scoring' | 'decision' | 'ai'
  outcome_id: string
  confirmation_status: string
  badge: string
}

interface IntelligenceRequirementsSectionProps {
  projectId: string
}

const QUADRANT_CONFIG = {
  knowledge: { label: 'Knowledge', icon: Database, color: '#044159', bg: 'rgba(4,65,89,0.06)' },
  scoring: { label: 'Scoring', icon: BarChart3, color: '#3FAF7A', bg: 'rgba(63,175,122,0.06)' },
  decision: { label: 'Decision Logic', icon: GitBranch, color: '#C49A1A', bg: 'rgba(196,154,26,0.06)' },
  ai: { label: 'AI', icon: Bot, color: '#0A1E2F', bg: 'rgba(10,30,47,0.06)' },
}

export function IntelligenceRequirementsSection({ projectId }: IntelligenceRequirementsSectionProps) {
  const [items, setItems] = useState<IntelligenceItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`${API_V1}/projects/${projectId}/workspace/outcomes/coverage`)
        if (!res.ok) return
        const data = await res.json()

        // Extract top 2 items per quadrant across all outcomes
        const allItems: IntelligenceItem[] = []
        const coverage = data.coverage || {}

        for (const [outcomeId, cov] of Object.entries(coverage) as [string, any][]) {
          for (const quadrant of ['knowledge', 'scoring', 'decision', 'ai'] as const) {
            const quadrantItems = cov[quadrant] || []
            for (const item of quadrantItems) {
              allItems.push({ ...item, quadrant, outcome_id: outcomeId })
            }
          }
        }

        // Keep top 2 per quadrant (by most recent / most important)
        const byQuadrant: Record<string, IntelligenceItem[]> = {}
        for (const item of allItems) {
          const q = item.quadrant
          if (!byQuadrant[q]) byQuadrant[q] = []
          // Dedupe by name
          if (!byQuadrant[q].some(i => i.name === item.name)) {
            byQuadrant[q].push(item)
          }
        }

        const topItems: IntelligenceItem[] = []
        for (const q of ['knowledge', 'scoring', 'decision', 'ai'] as const) {
          const qItems = byQuadrant[q] || []
          topItems.push(...qItems.slice(0, 2))
        }

        setItems(topItems)
      } catch (e) {
        console.error('Failed to load intelligence requirements', e)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [projectId])

  if (loading) return null

  const grouped: Record<string, IntelligenceItem[]> = {}
  for (const item of items) {
    if (!grouped[item.quadrant]) grouped[item.quadrant] = []
    grouped[item.quadrant].push(item)
  }

  return (
    <section>
      <SectionHeader title="Intelligence Requirements" count={items.length} />
      <div className="grid grid-cols-2 gap-3">
        {(['knowledge', 'scoring', 'decision', 'ai'] as const).map(quadrant => {
          const config = QUADRANT_CONFIG[quadrant]
          const Icon = config.icon
          const qItems = grouped[quadrant] || []

          return (
            <div
              key={quadrant}
              className="bg-white rounded-2xl shadow-md border border-border p-4"
            >
              <div className="flex items-center gap-2 mb-3">
                <Icon className="w-4 h-4" style={{ color: config.color }} />
                <span className="text-[11px] font-bold uppercase tracking-wider" style={{ color: config.color }}>
                  {config.label}
                </span>
              </div>
              {qItems.length === 0 ? (
                <div className="text-[11px] text-[#A0AEC0] italic">No items yet</div>
              ) : (
                <div className="space-y-3">
                  {qItems.map(item => (
                    <div key={item.id || item.name}>
                      <div className="text-[13px] font-semibold text-[#1D1D1F]">{item.name}</div>
                      <div className="text-[11px] text-[#718096] leading-relaxed mt-0.5">
                        {item.description?.slice(0, 120)}
                      </div>
                      <div className="flex items-center gap-1.5 mt-1.5">
                        <span className={`text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${
                          item.confirmation_status === 'confirmed_consultant'
                            ? 'bg-green-50 text-green-700'
                            : 'bg-gray-100 text-gray-400'
                        }`}>
                          {item.confirmation_status === 'confirmed_consultant' ? 'Confirmed' : 'System Inferred'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </section>
  )
}
