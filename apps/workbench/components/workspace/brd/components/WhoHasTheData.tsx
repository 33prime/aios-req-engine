'use client'

import { useMemo } from 'react'
import { Check, Clock, AlertTriangle, FileText, Users } from 'lucide-react'
import { TOPIC_ROLE_MAP, ARTIFACT_SUGGESTIONS } from '@/lib/topic-role-map'
import type { StakeholderBRDSummary, BRDEvidence } from '@/types/workspace'

interface WhoHasTheDataProps {
  topics: string[]
  stakeholders: StakeholderBRDSummary[]
  evidence: BRDEvidence[]
}

interface KnowledgeArea {
  topic: string
  suggestedRoles: string[]
  matchedStakeholders: { stakeholder: StakeholderBRDSummary; role: string }[]
  status: 'confirmed' | 'pending' | 'not_consulted'
  artifacts: string[]
}

function fuzzyRoleMatch(stakeholderRole: string, suggestedRole: string): boolean {
  const sLower = stakeholderRole.toLowerCase()
  const rLower = suggestedRole.toLowerCase()
  return sLower.includes(rLower) || rLower.includes(sLower)
}

export function WhoHasTheData({ topics, stakeholders, evidence }: WhoHasTheDataProps) {
  const knowledgeAreas = useMemo(() => {
    const areas: KnowledgeArea[] = []
    const seenTopics = new Set<string>()

    for (const topic of topics) {
      if (seenTopics.has(topic)) continue
      seenTopics.add(topic)

      const suggestedRoles = TOPIC_ROLE_MAP[topic] || ['Subject Matter Expert']
      const artifacts = ARTIFACT_SUGGESTIONS[topic] || []

      // Find matched stakeholders
      const matched: { stakeholder: StakeholderBRDSummary; role: string }[] = []
      for (const role of suggestedRoles) {
        for (const s of stakeholders) {
          if (s.role && fuzzyRoleMatch(s.role, role)) {
            if (!matched.some(m => m.stakeholder.id === s.id)) {
              matched.push({ stakeholder: s, role })
            }
          }
        }
      }

      // Determine status
      let status: 'confirmed' | 'pending' | 'not_consulted' = 'not_consulted'
      if (matched.length > 0) {
        // Check if any matched stakeholder has confirmed status
        const hasConfirmed = matched.some(
          m => m.stakeholder.confirmation_status === 'confirmed_consultant' ||
               m.stakeholder.confirmation_status === 'confirmed_client'
        )
        status = hasConfirmed ? 'confirmed' : 'pending'
      }

      areas.push({
        topic,
        suggestedRoles,
        matchedStakeholders: matched,
        status,
        artifacts,
      })
    }

    return areas
  }, [topics, stakeholders])

  const confirmedCount = knowledgeAreas.filter(a => a.status === 'confirmed').length
  const totalCount = knowledgeAreas.length

  if (totalCount === 0) {
    return (
      <div className="text-center py-8">
        <Users className="w-8 h-8 text-[#E5E5E5] mx-auto mb-3" />
        <p className="text-[13px] text-[#666666]">No knowledge areas to analyze</p>
      </div>
    )
  }

  return (
    <div className="space-y-5">
      {/* Summary */}
      <div className="border border-[#E5E5E5] rounded-xl px-4 py-3 bg-[#F4F4F4]">
        <div className="flex items-center justify-between">
          <span className="text-[12px] font-medium text-[#333333]">
            Knowledge Coverage
          </span>
          <span className="text-[12px] font-semibold text-[#333333]">
            {confirmedCount} of {totalCount} areas covered
          </span>
        </div>
        <div className="mt-2 h-2 bg-[#E5E5E5] rounded-full overflow-hidden">
          <div
            className="h-full bg-[#3FAF7A] rounded-full transition-all duration-300"
            style={{ width: `${totalCount > 0 ? (confirmedCount / totalCount) * 100 : 0}%` }}
          />
        </div>
      </div>

      {/* Knowledge areas */}
      <div className="space-y-3">
        {knowledgeAreas.map((area) => (
          <KnowledgeAreaCard key={area.topic} area={area} />
        ))}
      </div>

      {/* Artifact suggestions */}
      {knowledgeAreas.some(a => a.artifacts.length > 0 && a.status !== 'confirmed') && (
        <div className="border border-[#E5E5E5] rounded-xl px-4 py-3">
          <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2 flex items-center gap-1.5">
            <FileText className="w-3.5 h-3.5" />
            Suggested Artifacts to Request
          </h4>
          <div className="flex flex-wrap gap-1.5">
            {Array.from(new Set(
              knowledgeAreas
                .filter(a => a.status !== 'confirmed')
                .flatMap(a => a.artifacts)
            )).slice(0, 8).map((artifact) => (
              <span
                key={artifact}
                className="px-2 py-1 text-[11px] bg-[#F0F0F0] text-[#666666] rounded-lg"
              >
                {artifact}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function KnowledgeAreaCard({ area }: { area: KnowledgeArea }) {
  const statusConfig = {
    confirmed: {
      icon: Check,
      color: 'text-[#3FAF7A]',
      bg: 'bg-[#E8F5E9]',
      label: 'Covered',
    },
    pending: {
      icon: Clock,
      color: 'text-[#666666]',
      bg: 'bg-[#F0F0F0]',
      label: 'Pending',
    },
    not_consulted: {
      icon: AlertTriangle,
      color: 'text-[#999999]',
      bg: 'bg-[#F0F0F0]',
      label: 'Not consulted',
    },
  }

  const config = statusConfig[area.status]
  const StatusIcon = config.icon

  return (
    <div className="border border-[#E5E5E5] rounded-xl px-4 py-3">
      <div className="flex items-center gap-2 mb-2">
        <StatusIcon className={`w-4 h-4 ${config.color}`} />
        <span className="text-[13px] font-medium text-[#333333] capitalize flex-1">
          {area.topic}
        </span>
        <span className={`px-2 py-0.5 text-[10px] font-medium rounded-full ${config.bg} ${config.color}`}>
          {config.label}
        </span>
      </div>

      {area.matchedStakeholders.length > 0 ? (
        <div className="space-y-1.5 ml-6">
          {area.matchedStakeholders.map(({ stakeholder }) => (
            <div key={stakeholder.id} className="flex items-center gap-2 text-[12px]">
              <span className={`w-1.5 h-1.5 rounded-full ${
                stakeholder.confirmation_status === 'confirmed_consultant' ||
                stakeholder.confirmation_status === 'confirmed_client'
                  ? 'bg-[#3FAF7A]' : 'bg-[#E5E5E5]'
              }`} />
              <span className="text-[#333333] font-medium">{stakeholder.name}</span>
              {stakeholder.role && (
                <span className="text-[#999999]">({stakeholder.role})</span>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="ml-6">
          <p className="text-[12px] text-[#999999] mb-1.5">
            Suggested roles to consult:
          </p>
          <div className="flex flex-wrap gap-1">
            {area.suggestedRoles.slice(0, 3).map((role) => (
              <span
                key={role}
                className="px-2 py-0.5 text-[10px] bg-[#F0F0F0] text-[#666666] rounded-full"
              >
                {role}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
