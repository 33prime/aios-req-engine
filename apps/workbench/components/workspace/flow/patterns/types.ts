import type { SolutionFlowStepDetail, SolutionFlowStepSummary } from '@/types/workspace'

export type FieldInfo = {
  name: string
  type: string
  mock_value: string
  confidence: string
}

export interface PatternRendererProps {
  fields: FieldInfo[]
  step: { title: string; actors: string[] }
  detail: SolutionFlowStepDetail
  projectName?: string
}
