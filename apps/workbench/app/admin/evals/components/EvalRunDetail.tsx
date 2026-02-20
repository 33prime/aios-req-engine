'use client'

import { useEffect, useState } from 'react'
import { getEvalRunDetail } from '@/lib/api'
import type { EvalRunDetail as EvalRunDetailType } from '@/types/api'
import { DimensionRadar } from './DimensionRadar'
import { ScoreBreakdownBar, ActionBadge } from './ScoreBreakdownBar'
import { PromptDiffViewer } from './PromptDiffViewer'

interface Props {
  runId: string
}

export function EvalRunDetail({ runId }: Props) {
  const [run, setRun] = useState<EvalRunDetailType | null>(null)
  const [loading, setLoading] = useState(true)
  const [showDiff, setShowDiff] = useState(false)

  useEffect(() => {
    setLoading(true)
    getEvalRunDetail(runId)
      .then(setRun)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [runId])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-32">
        <div className="w-4 h-4 border-2 border-[#3FAF7A] border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!run) {
    return <p className="text-[13px] text-[#999999]">Failed to load run detail</p>
  }

  return (
    <div className="space-y-4 p-4 bg-[#FAFAFA] rounded-xl border border-[#E5E5E5]">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-[15px] font-semibold text-[#333333]">
            Iteration {run.iteration_number}
          </span>
          <ActionBadge action={run.action} />
          <span className="text-[13px] text-[#999999]">
            Overall: {(run.overall_score * 100).toFixed(1)}%
          </span>
        </div>
        <div className="flex items-center gap-4 text-[11px] text-[#999999]">
          <span>Det: {run.deterministic_duration_ms}ms</span>
          <span>LLM: {run.llm_duration_ms}ms</span>
          <span>${run.estimated_cost_usd.toFixed(4)}</span>
          {run.tokens_cache_read > 0 && (
            <span className="text-[#3FAF7A]">
              {((run.tokens_cache_read / Math.max(run.tokens_input, 1)) * 100).toFixed(0)}% cached
            </span>
          )}
        </div>
      </div>

      {/* Radar + Scores */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <DimensionRadar
          detScores={{
            feature_id_coverage: run.det_feature_id_coverage,
            file_structure: run.det_file_structure,
            route_count: run.det_route_count,
            jsdoc_coverage: run.det_jsdoc_coverage,
          }}
          llmScores={{
            feature_coverage: run.llm_feature_coverage,
            structure: run.llm_structure,
            mock_data: run.llm_mock_data,
            flow: run.llm_flow,
            feature_id: run.llm_feature_id,
          }}
        />

        <div className="space-y-3">
          <h3 className="text-[13px] font-semibold text-[#333333]">Deterministic</h3>
          <ScoreBreakdownBar score={run.det_feature_id_coverage} label="Feature IDs" />
          <ScoreBreakdownBar score={run.det_file_structure} label="File Structure" />
          <ScoreBreakdownBar score={run.det_route_count} label="Routes" />
          <ScoreBreakdownBar score={run.det_jsdoc_coverage} label="JSDoc" />
          <div className="flex items-center gap-2 text-[11px] text-[#666666]">
            <span>HANDOFF.md:</span>
            <span className={run.det_handoff_present ? 'text-[#3FAF7A]' : 'text-[#ef4444]'}>
              {run.det_handoff_present ? 'Present' : 'Missing'}
            </span>
          </div>

          <h3 className="text-[13px] font-semibold text-[#333333] mt-4">LLM-Judged</h3>
          <ScoreBreakdownBar score={run.llm_feature_coverage} label="Coverage" />
          <ScoreBreakdownBar score={run.llm_structure} label="Structure" />
          <ScoreBreakdownBar score={run.llm_mock_data} label="Mock Data" />
          <ScoreBreakdownBar score={run.llm_flow} label="Flow" />
          <ScoreBreakdownBar score={run.llm_feature_id} label="Feature IDs" />
        </div>
      </div>

      {/* Gaps */}
      {run.gaps.length > 0 && (
        <div>
          <h3 className="text-[13px] font-semibold text-[#333333] mb-2">
            Gaps ({run.gaps.length})
          </h3>
          <div className="space-y-1.5">
            {run.gaps.map((gap) => (
              <div
                key={gap.id}
                className="flex items-start gap-2 text-[12px] bg-white rounded-lg px-3 py-2 border border-[#E5E5E5]"
              >
                <span
                  className={`
                    px-1.5 py-0.5 rounded text-[10px] font-medium flex-shrink-0
                    ${gap.severity === 'high' ? 'bg-[#FEE2E2] text-[#991b1b]' :
                      gap.severity === 'medium' ? 'bg-[#FEF3C7] text-[#92400e]' :
                      'bg-[#F0F0F0] text-[#666666]'}
                  `}
                >
                  {gap.severity}
                </span>
                <span className="text-[#666666] w-24 flex-shrink-0">{gap.dimension}</span>
                <span className="text-[#333333]">{gap.description}</span>
                {gap.resolved_in_run_id && (
                  <span className="text-[#3FAF7A] text-[10px] flex-shrink-0">resolved</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {run.recommendations.length > 0 && (
        <div>
          <h3 className="text-[13px] font-semibold text-[#333333] mb-2">Recommendations</h3>
          <ul className="space-y-1">
            {run.recommendations.map((rec, i) => (
              <li key={i} className="text-[12px] text-[#666666]">
                • {rec}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Prompt diff toggle */}
      <div>
        <button
          onClick={() => setShowDiff(!showDiff)}
          className="text-[12px] text-[#3FAF7A] hover:underline"
        >
          {showDiff ? 'Hide' : 'Show'} Prompt Diff
        </button>
        {showDiff && (
          <div className="mt-2">
            <PromptDiffViewer versionId={run.prompt_version_id} />
          </div>
        )}
      </div>
    </div>
  )
}
