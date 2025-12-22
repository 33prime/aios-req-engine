'use client'

import { useParams } from 'next/navigation'
import { InsightsDashboard } from '@/components/InsightsDashboard'

export default function InsightsPage() {
  const params = useParams()
  const projectId = params.projectId as string

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Insights Dashboard</h1>
        <p className="text-gray-600 mt-1">Red team analysis results and recommendations</p>
      </div>

      <InsightsDashboard projectId={projectId} />
    </div>
  )
}
