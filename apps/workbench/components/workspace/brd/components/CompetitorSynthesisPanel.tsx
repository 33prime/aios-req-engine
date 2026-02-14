'use client'

import { useState, useEffect } from 'react'
import { X, Globe, Loader2, Target, Shield } from 'lucide-react'
import { synthesizeCompetitors } from '@/lib/api'
import type { CompetitorSynthesis, FeatureHeatmapRow, CompetitorThreat } from '@/types/workspace'

interface CompetitorSynthesisPanelProps {
  projectId: string
  onClose: () => void
}

const STATUS_COLORS: Record<string, { bg: string; text: string }> = {
  strong: { bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]' },
  basic: { bg: 'bg-[#F0F0F0]', text: 'text-[#666666]' },
  planned: { bg: 'bg-[#F0F0F0]', text: 'text-[#999999]' },
  missing: { bg: 'bg-white', text: 'text-[#999999]' },
}

export function CompetitorSynthesisPanel({ projectId, onClose }: CompetitorSynthesisPanelProps) {
  const [synthesis, setSynthesis] = useState<CompetitorSynthesis | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    synthesizeCompetitors(projectId)
      .then((data) => setSynthesis(data))
      .catch((err) => {
        console.error('Failed to synthesize:', err)
        setError('Failed to generate synthesis. Make sure at least one competitor has been analyzed.')
      })
      .finally(() => setLoading(false))
  }, [projectId])

  return (
    <>
      <div className="fixed inset-0 bg-black/20 z-40" onClick={onClose} />
      <div className="fixed right-0 top-0 h-screen w-[640px] max-w-[95vw] bg-white shadow-xl z-50 flex flex-col animate-slide-in-right">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#E5E5E5]">
          <div className="flex items-center gap-2.5">
            <Globe className="w-5 h-5 text-[#3FAF7A]" />
            <h2 className="text-[16px] font-semibold text-[#333333]">Market Landscape</h2>
          </div>
          <button onClick={onClose} className="p-1.5 text-[#999999] hover:text-[#333333] transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {loading && (
            <div className="text-center py-16">
              <Loader2 className="w-8 h-8 animate-spin text-[#3FAF7A] mx-auto mb-3" />
              <p className="text-[13px] text-[#999999]">Synthesizing competitor insights...</p>
              <p className="text-[11px] text-[#999999] mt-1">This may take a moment</p>
            </div>
          )}

          {error && (
            <div className="text-center py-16">
              <p className="text-[13px] text-[#666666]">{error}</p>
            </div>
          )}

          {synthesis && (
            <div className="space-y-8">
              {/* Market Landscape */}
              <div>
                <h3 className="text-[14px] font-semibold text-[#333333] mb-2">Market Overview</h3>
                <p className="text-[13px] text-[#666666] leading-relaxed">{synthesis.market_landscape}</p>
              </div>

              {/* Feature Heatmap */}
              {synthesis.feature_heatmap.length > 0 && (
                <FeatureHeatmap rows={synthesis.feature_heatmap} />
              )}

              {/* Common Themes */}
              {synthesis.common_themes.length > 0 && (
                <div>
                  <h3 className="text-[14px] font-semibold text-[#333333] mb-2">Common Themes</h3>
                  <ul className="space-y-1.5">
                    {synthesis.common_themes.map((theme, i) => (
                      <li key={i} className="flex items-start gap-2 text-[13px] text-[#666666]">
                        <span className="text-[#3FAF7A] mt-0.5">•</span>
                        {theme}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Market Gaps */}
              {synthesis.market_gaps.length > 0 && (
                <div>
                  <h3 className="text-[14px] font-semibold text-[#333333] mb-2">Market Gaps</h3>
                  <div className="space-y-2">
                    {synthesis.market_gaps.map((gap, i) => (
                      <div key={i} className="flex items-start gap-2 p-3 bg-[#E8F5E9]/50 rounded-lg border border-[#3FAF7A]/10">
                        <Target className="w-3.5 h-3.5 text-[#3FAF7A] flex-shrink-0 mt-0.5" />
                        <p className="text-[12px] text-[#333333]">{gap}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Positioning Recommendation */}
              {synthesis.positioning_recommendation && (
                <div className="p-4 bg-[#F4F4F4] rounded-xl border border-[#E5E5E5]">
                  <h3 className="text-[14px] font-semibold text-[#333333] mb-2">Positioning Recommendation</h3>
                  <p className="text-[13px] text-[#666666] leading-relaxed">{synthesis.positioning_recommendation}</p>
                </div>
              )}

              {/* Threat Summary */}
              {synthesis.threat_summary.length > 0 && (
                <div>
                  <h3 className="text-[14px] font-semibold text-[#333333] mb-2">Threat Summary</h3>
                  <div className="space-y-2">
                    {synthesis.threat_summary.map((t, i) => (
                      <ThreatCard key={i} threat={t} />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  )
}

function FeatureHeatmap({ rows }: { rows: FeatureHeatmapRow[] }) {
  // Collect all competitor names
  const competitorNames = Array.from(
    new Set(rows.flatMap((r) => Object.keys(r.competitors)))
  )

  return (
    <div>
      <h3 className="text-[14px] font-semibold text-[#333333] mb-2">Feature Heatmap</h3>
      <div className="border border-[#E5E5E5] rounded-xl overflow-hidden overflow-x-auto">
        <table className="w-full text-[11px]">
          <thead>
            <tr className="bg-[#F4F4F4]">
              <th className="text-left px-3 py-2 font-medium text-[#666666] min-w-[120px]">Feature Area</th>
              <th className="text-center px-2 py-2 font-medium text-[#25785A] min-w-[60px]">Us</th>
              {competitorNames.map((name) => (
                <th key={name} className="text-center px-2 py-2 font-medium text-[#666666] min-w-[60px]">
                  {name.length > 12 ? name.slice(0, 12) + '...' : name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className="border-t border-[#E5E5E5]">
                <td className="px-3 py-2 font-medium text-[#333333]">{row.feature_area}</td>
                <td className="px-2 py-2 text-center">
                  <StatusBadge status={row.our_status} />
                </td>
                {competitorNames.map((name) => (
                  <td key={name} className="px-2 py-2 text-center">
                    <StatusBadge status={row.competitors[name] || 'missing'} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const colors = STATUS_COLORS[status] || STATUS_COLORS.missing
  return (
    <span className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-medium ${colors.bg} ${colors.text}`}>
      {status}
    </span>
  )
}

function ThreatCard({ threat }: { threat: CompetitorThreat }) {
  return (
    <div className="flex items-start gap-3 p-3 border border-[#E5E5E5] rounded-lg">
      <Shield className="w-4 h-4 text-[#999999] flex-shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-[12px] font-medium text-[#333333]">{threat.competitor_name}</span>
          <span className="inline-flex px-1.5 py-0.5 rounded text-[10px] font-medium bg-[#F0F0F0] text-[#666666]">
            {threat.threat_level}
          </span>
        </div>
        <p className="text-[11px] text-[#666666]">{threat.key_risk}</p>
      </div>
    </div>
  )
}
