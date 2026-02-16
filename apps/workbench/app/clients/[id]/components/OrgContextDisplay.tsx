'use client'

interface OrgContextDisplayProps {
  orgContext: Record<string, unknown>
  variant: 'compact' | 'full'
}

interface Assessment {
  decision_making_style?: string
  decision_making_notes?: string
  change_readiness?: string
  change_readiness_notes?: string
  risk_tolerance?: string
  communication_style?: string
  political_dynamics?: string
  key_insight?: string
  watch_out_for?: string[]
}

interface StakeholderAnalysis {
  decision_makers?: string[]
  influence_map?: Record<string, string[]>
  alignment_notes?: string
  potential_conflicts?: string[]
  cross_project_stakeholders?: string[]
  engagement_assessment?: string
}

const POSITIVE_VALUES = new Set(['eager', 'open', 'risk_taking'])

function EnumBadge({ label, value }: { label: string; value: string }) {
  const display = value.replace(/_/g, ' ')
  const isPositive = POSITIVE_VALUES.has(value)
  return (
    <div className="bg-[#F4F4F4] rounded-lg px-3 py-2">
      <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide">{label}</p>
      <span
        className={`inline-block mt-1 px-2 py-0.5 text-[11px] font-medium rounded-md capitalize ${
          isPositive
            ? 'bg-[#E8F5E9] text-[#25785A]'
            : 'bg-[#F0F0F0] text-[#666]'
        }`}
      >
        {display}
      </span>
    </div>
  )
}

export function OrgContextDisplay({ orgContext, variant }: OrgContextDisplayProps) {
  const assessment = (orgContext?.assessment ?? {}) as Assessment
  const stakeholderAnalysis = (orgContext?.stakeholder_analysis ?? {}) as StakeholderAnalysis

  const hasAssessment = assessment && (
    assessment.decision_making_style ||
    assessment.change_readiness ||
    assessment.risk_tolerance ||
    assessment.key_insight
  )

  if (!hasAssessment && variant === 'compact') {
    return (
      <div className="bg-[#F4F4F4] rounded-lg px-4 py-3">
        <p className="text-[12px] text-[#999]">No organizational context assessed yet</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Assessment badges */}
      {hasAssessment && (
        <div className="grid grid-cols-2 gap-2">
          {assessment.decision_making_style && assessment.decision_making_style !== 'unknown' && (
            <EnumBadge label="Decision Style" value={assessment.decision_making_style} />
          )}
          {assessment.change_readiness && assessment.change_readiness !== 'unknown' && (
            <EnumBadge label="Change Readiness" value={assessment.change_readiness} />
          )}
          {assessment.risk_tolerance && assessment.risk_tolerance !== 'unknown' && (
            <EnumBadge label="Risk Tolerance" value={assessment.risk_tolerance} />
          )}
          {assessment.communication_style && assessment.communication_style !== 'unknown' && (
            <EnumBadge label="Communication" value={assessment.communication_style} />
          )}
        </div>
      )}

      {/* Key Insight */}
      {assessment.key_insight && (
        <div className="border-l-2 border-[#3FAF7A] pl-3 bg-[#F4F4F4] rounded-lg p-3">
          <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide mb-1">Key Insight</p>
          <p className="text-[13px] text-[#333] leading-relaxed">{assessment.key_insight}</p>
        </div>
      )}

      {/* Compact variant stops here */}
      {variant === 'compact' && null}

      {/* Full variant: additional details */}
      {variant === 'full' && (
        <>
          {/* Political Dynamics */}
          {assessment.political_dynamics && (
            <div>
              <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide mb-1">Political Dynamics</p>
              <p className="text-[13px] text-[#666] leading-relaxed">{assessment.political_dynamics}</p>
            </div>
          )}

          {/* Watch Out For */}
          {assessment.watch_out_for && assessment.watch_out_for.length > 0 && (
            <div>
              <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide mb-1.5">Watch Out For</p>
              <div className="space-y-1.5">
                {assessment.watch_out_for.map((item, i) => (
                  <div key={i} className="bg-[#F4F4F4] rounded-lg px-3 py-2">
                    <p className="text-[12px] text-[#333]">{item}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Stakeholder Analysis */}
          {stakeholderAnalysis && Object.keys(stakeholderAnalysis).length > 0 && (
            <div className="pt-3 border-t border-[#E5E5E5]">
              <p className="text-[12px] font-semibold text-[#333] mb-2">Stakeholder Analysis</p>

              {/* Decision Makers */}
              {stakeholderAnalysis.decision_makers && stakeholderAnalysis.decision_makers.length > 0 && (
                <div className="mb-2">
                  <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide mb-1">Decision Makers</p>
                  <div className="flex flex-wrap gap-1">
                    {stakeholderAnalysis.decision_makers.map((name, i) => (
                      <span key={i} className="px-2 py-0.5 text-[11px] text-[#666] bg-[#F0F0F0] rounded-md">
                        {name}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Influence Map */}
              {stakeholderAnalysis.influence_map && Object.keys(stakeholderAnalysis.influence_map).length > 0 && (
                <div className="mb-2">
                  <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide mb-1">Influence Map</p>
                  <div className="space-y-1">
                    {Object.entries(stakeholderAnalysis.influence_map).map(([level, names]) => (
                      <div key={level} className="flex items-start gap-2">
                        <span className="text-[11px] text-[#999] font-medium uppercase w-14 flex-shrink-0 pt-0.5">{level}</span>
                        <div className="flex flex-wrap gap-1">
                          {(names as string[]).map((name, i) => (
                            <span key={i} className="px-2 py-0.5 text-[11px] text-[#666] bg-[#F0F0F0] rounded-md">
                              {name}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Alignment Notes */}
              {stakeholderAnalysis.alignment_notes && (
                <div className="mb-2">
                  <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide mb-1">Alignment</p>
                  <p className="text-[12px] text-[#666]">{stakeholderAnalysis.alignment_notes}</p>
                </div>
              )}

              {/* Potential Conflicts */}
              {stakeholderAnalysis.potential_conflicts && stakeholderAnalysis.potential_conflicts.length > 0 && (
                <div className="mb-2">
                  <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide mb-1">Potential Conflicts</p>
                  <div className="space-y-1">
                    {stakeholderAnalysis.potential_conflicts.map((conflict, i) => (
                      <div key={i} className="bg-[#F4F4F4] rounded-lg px-3 py-1.5">
                        <p className="text-[12px] text-[#666]">{conflict}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Cross-project stakeholders */}
              {stakeholderAnalysis.cross_project_stakeholders && stakeholderAnalysis.cross_project_stakeholders.length > 0 && (
                <div>
                  <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide mb-1">Cross-Project</p>
                  <div className="flex flex-wrap gap-1">
                    {stakeholderAnalysis.cross_project_stakeholders.map((name, i) => (
                      <span key={i} className="px-2 py-0.5 text-[11px] text-[#25785A] bg-[#E8F5E9] rounded-md">
                        {name}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Fallback for unknown nested keys */}
          {Object.entries(orgContext).map(([key, val]) => {
            if (key === 'assessment' || key === 'stakeholder_analysis') return null
            if (typeof val === 'string') {
              return (
                <div key={key} className="bg-[#F4F4F4] rounded-lg px-3 py-2">
                  <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide">{key.replace(/_/g, ' ')}</p>
                  <p className="text-[13px] text-[#333] mt-0.5">{val}</p>
                </div>
              )
            }
            if (typeof val === 'object' && val !== null) {
              return (
                <div key={key} className="bg-[#F4F4F4] rounded-lg px-3 py-2">
                  <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide">{key.replace(/_/g, ' ')}</p>
                  <pre className="text-[11px] text-[#666] mt-1 whitespace-pre-wrap overflow-auto max-h-40">
                    {JSON.stringify(val, null, 2)}
                  </pre>
                </div>
              )
            }
            return null
          })}
        </>
      )}
    </div>
  )
}
