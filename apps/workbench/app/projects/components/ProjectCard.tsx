'use client'

import { CheckCircle, FileText } from 'lucide-react'
import type { ProjectDetailWithDashboard, ProjectTask } from '@/types/api'

interface ProjectCardProps {
  project: ProjectDetailWithDashboard
  tasks?: ProjectTask[]
  gaps?: string[]
  readinessScore?: number
  onClick: () => void
}

const stageColors: Record<string, string> = {
  discovery: 'bg-emerald-100 text-emerald-700',
  prototype_refinement: 'bg-[#009b87] text-white',
  proposal: 'bg-[#007a6b] text-white',
}

const stageLabels: Record<string, string> = {
  discovery: 'Discovery',
  prototype_refinement: 'Prototype Build',
  proposal: 'Proposal',
}

export function ProjectCard({ project, tasks = [], gaps = [], readinessScore, onClick }: ProjectCardProps) {
  const readiness = readinessScore ?? 0
  const stage = project.stage || 'discovery'

  // Get next steps from tasks (limit to 4)
  const nextSteps = tasks.slice(0, 4).map(t => t.title)

  // Generate requirement gaps from counts (simplified - in real app this would come from API)
  const requirementGaps = gaps.length > 0 ? gaps : []

  return (
    <button
      onClick={onClick}
      className="bg-white rounded-xl border border-gray-200 p-6 text-left hover:shadow-lg transition-all cursor-pointer w-full"
    >
      {/* Header Row */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="text-xl font-semibold text-gray-900 truncate">
            {project.name}
          </h3>
          {project.description && (
            <p className="text-sm text-gray-600 mt-1 line-clamp-1">
              {project.description}
            </p>
          )}
        </div>

        {/* Readiness Score */}
        <div className="flex items-center gap-3 ml-4 flex-shrink-0">
          <div className="text-right">
            <span className="text-sm text-gray-500">Readiness Score: </span>
            <span className="text-sm font-semibold text-gray-900">{Math.round(readiness)}%</span>
          </div>
          <div className="w-20 h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${
                readiness >= 80 ? 'bg-[#009b87]' : readiness >= 50 ? 'bg-emerald-400' : 'bg-emerald-200'
              }`}
              style={{ width: `${readiness}%` }}
            />
          </div>
          <div className="w-8 h-8 rounded-full bg-[#009b87] flex items-center justify-center">
            <svg className="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M7 17L17 7M17 7H7M17 7V17" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
        </div>
      </div>

      {/* Stage Badge */}
      <div className="mb-4">
        <span className={`inline-flex px-3 py-1 text-sm font-medium rounded-full ${stageColors[stage] || stageColors.discovery}`}>
          {stageLabels[stage] || 'Discovery'}
        </span>
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-2 gap-6">
        {/* Next Steps */}
        <div>
          <h4 className="text-sm font-semibold text-gray-900 mb-3">Next Steps</h4>
          {nextSteps.length > 0 ? (
            <ul className="space-y-2">
              {nextSteps.map((step, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                  <CheckCircle className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
                  <span className="line-clamp-1">{step}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-500 italic">No pending tasks</p>
          )}
        </div>

        {/* Requirement Gaps */}
        <div>
          <h4 className="text-sm font-semibold text-gray-900 mb-3">Requirement Gaps</h4>
          {requirementGaps.length > 0 ? (
            <ul className="space-y-2">
              {requirementGaps.slice(0, 4).map((gap, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                  <FileText className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
                  <span className="line-clamp-1">{gap}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-500 italic">No gaps identified</p>
          )}
        </div>
      </div>
    </button>
  )
}
