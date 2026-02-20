'use client'

import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Legend,
} from 'recharts'

interface DimensionData {
  dimension: string
  det: number
  llm: number
}

interface Props {
  detScores: {
    feature_id_coverage: number
    file_structure: number
    route_count: number
    jsdoc_coverage: number
  }
  llmScores: {
    feature_coverage: number
    structure: number
    mock_data: number
    flow: number
    feature_id: number
  }
}

export function DimensionRadar({ detScores, llmScores }: Props) {
  const data: DimensionData[] = [
    { dimension: 'Feature Coverage', det: detScores.feature_id_coverage, llm: llmScores.feature_coverage },
    { dimension: 'Structure', det: detScores.file_structure, llm: llmScores.structure },
    { dimension: 'Mock Data', det: 0, llm: llmScores.mock_data },
    { dimension: 'Flow', det: detScores.route_count, llm: llmScores.flow },
    { dimension: 'Feature IDs', det: detScores.jsdoc_coverage, llm: llmScores.feature_id },
  ]

  return (
    <ResponsiveContainer width="100%" height={280}>
      <RadarChart data={data} cx="50%" cy="50%" outerRadius="70%">
        <PolarGrid stroke="#E5E5E5" />
        <PolarAngleAxis dataKey="dimension" tick={{ fontSize: 11, fill: '#666666' }} />
        <PolarRadiusAxis domain={[0, 1]} tick={{ fontSize: 10, fill: '#999999' }} tickCount={5} />
        <Radar
          name="Deterministic"
          dataKey="det"
          stroke="#0A1E2F"
          fill="#0A1E2F"
          fillOpacity={0.15}
          strokeWidth={2}
        />
        <Radar
          name="LLM"
          dataKey="llm"
          stroke="#3FAF7A"
          fill="#3FAF7A"
          fillOpacity={0.15}
          strokeWidth={2}
        />
        <Legend iconSize={8} wrapperStyle={{ fontSize: 12 }} />
      </RadarChart>
    </ResponsiveContainer>
  )
}
