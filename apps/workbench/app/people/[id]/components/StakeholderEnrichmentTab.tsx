'use client'

import { Brain, Shield, Target, AlertTriangle, Trophy, MessageSquare } from 'lucide-react'
import type { StakeholderDetail } from '@/types/workspace'

interface StakeholderEnrichmentTabProps {
  stakeholder: StakeholderDetail
}

export function StakeholderEnrichmentTab({ stakeholder }: StakeholderEnrichmentTabProps) {
  const s = stakeholder
  const hasEnrichment = s.engagement_level || s.decision_authority || s.engagement_strategy ||
    s.risk_if_disengaged || (s.win_conditions && s.win_conditions.length > 0) ||
    (s.key_concerns && s.key_concerns.length > 0)

  if (!hasEnrichment) {
    return (
      <div className="text-center py-8">
        <Brain className="w-8 h-8 text-gray-300 mx-auto mb-2" />
        <p className="text-[13px] text-[rgba(55,53,47,0.45)]">
          No enrichment data available yet.
        </p>
        <p className="text-[12px] text-[rgba(55,53,47,0.35)] mt-1">
          Enrichment data is generated when the AI analyzes signals mentioning this stakeholder.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-5">
      {/* Engagement Level */}
      {s.engagement_level && (
        <div className="flex items-start gap-3">
          <MessageSquare className="w-4 h-4 text-teal-500 mt-0.5 flex-shrink-0" />
          <div>
            <h4 className="text-[12px] font-semibold text-[rgba(55,53,47,0.45)] uppercase tracking-wider mb-0.5">Engagement Level</h4>
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[12px] font-medium bg-teal-50 text-teal-700">
              {s.engagement_level}
            </span>
          </div>
        </div>
      )}

      {/* Decision Authority */}
      {s.decision_authority && (
        <div className="flex items-start gap-3">
          <Shield className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
          <div>
            <h4 className="text-[12px] font-semibold text-[rgba(55,53,47,0.45)] uppercase tracking-wider mb-0.5">Decision Authority</h4>
            <p className="text-[13px] text-[rgba(55,53,47,0.65)]">{s.decision_authority}</p>
          </div>
        </div>
      )}

      {/* Engagement Strategy */}
      {s.engagement_strategy && (
        <div className="flex items-start gap-3">
          <Target className="w-4 h-4 text-purple-500 mt-0.5 flex-shrink-0" />
          <div>
            <h4 className="text-[12px] font-semibold text-[rgba(55,53,47,0.45)] uppercase tracking-wider mb-0.5">Engagement Strategy</h4>
            <p className="text-[13px] text-[rgba(55,53,47,0.65)] leading-relaxed">{s.engagement_strategy}</p>
          </div>
        </div>
      )}

      {/* Risk if Disengaged */}
      {s.risk_if_disengaged && (
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-4 h-4 text-orange-500 mt-0.5 flex-shrink-0" />
          <div>
            <h4 className="text-[12px] font-semibold text-[rgba(55,53,47,0.45)] uppercase tracking-wider mb-0.5">Risk if Disengaged</h4>
            <p className="text-[13px] text-[rgba(55,53,47,0.65)] leading-relaxed">{s.risk_if_disengaged}</p>
          </div>
        </div>
      )}

      {/* Win Conditions */}
      {s.win_conditions && s.win_conditions.length > 0 && (
        <div className="flex items-start gap-3">
          <Trophy className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
          <div>
            <h4 className="text-[12px] font-semibold text-[rgba(55,53,47,0.45)] uppercase tracking-wider mb-1">Win Conditions</h4>
            <ul className="space-y-1">
              {s.win_conditions.map((wc, i) => (
                <li key={i} className="text-[13px] text-[rgba(55,53,47,0.65)] flex items-start gap-2">
                  <span className="text-amber-500 mt-1">•</span>
                  <span>{wc}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Key Concerns */}
      {s.key_concerns && s.key_concerns.length > 0 && (
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
          <div>
            <h4 className="text-[12px] font-semibold text-[rgba(55,53,47,0.45)] uppercase tracking-wider mb-1">Key Concerns</h4>
            <ul className="space-y-1">
              {s.key_concerns.map((kc, i) => (
                <li key={i} className="text-[13px] text-[rgba(55,53,47,0.65)] flex items-start gap-2">
                  <span className="text-red-400 mt-1">•</span>
                  <span>{kc}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}
