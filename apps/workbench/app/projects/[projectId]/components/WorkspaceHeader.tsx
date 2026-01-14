/**
 * WorkspaceHeader Component
 *
 * Main workspace header with:
 * - Back navigation to projects
 * - Project name and client info
 * - Stage badge
 * - Portal status
 * - Research toggle
 * - Activity/Refresh actions
 */

'use client'

import React from 'react'
import Link from 'next/link'
import {
  RefreshCw,
  Settings,
  Clock,
  ArrowLeft,
  Globe,
  Lock
} from 'lucide-react'
import { IconButton } from '@/components/ui'
import type { ProjectStage } from '@/types/api'

const stageColors: Record<ProjectStage, string> = {
  discovery: 'bg-emerald-100 text-emerald-700',
  prototype_refinement: 'bg-[#009b87] text-white',
  proposal: 'bg-[#007a6b] text-white',
}

const stageLabels: Record<ProjectStage, string> = {
  discovery: 'Discovery',
  prototype_refinement: 'Prototype Build',
  proposal: 'Proposal',
}

interface WorkspaceHeaderProps {
  projectId: string
  projectName: string
  clientName?: string
  stage?: ProjectStage
  portalEnabled?: boolean
  baseline: {
    baseline_ready: boolean
    client_signal_count?: number
    fact_count?: number
  } | null
  onBaselineToggle: () => void
  onRefresh: () => void
  onShowActivity?: () => void
}

export function WorkspaceHeader({
  projectId,
  projectName,
  clientName,
  stage = 'discovery',
  portalEnabled = false,
  baseline,
  onBaselineToggle,
  onRefresh,
  onShowActivity,
}: WorkspaceHeaderProps) {
  return (
    <header className="bg-white border-b border-gray-200">
      <div className="px-6 py-4">
        <div className="flex items-center justify-between">
          {/* Left: Back nav + Project Info */}
          <div className="flex items-center gap-4">
            {/* Back to Projects */}
            <Link
              href="/projects"
              className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900 transition-colors"
            >
              <ArrowLeft className="h-4 w-4" />
              <span className="hidden sm:inline">Projects</span>
            </Link>

            <div className="h-6 w-px bg-gray-200" />

            {/* Project Info */}
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-lg font-semibold text-gray-900">
                  {projectName}
                </h1>

                {/* Stage Badge */}
                <span className={`inline-flex px-2.5 py-0.5 text-xs font-medium rounded-full ${stageColors[stage]}`}>
                  {stageLabels[stage]}
                </span>

                {/* Portal Status */}
                <div
                  className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                    portalEnabled
                      ? 'bg-blue-100 text-blue-700'
                      : 'bg-gray-100 text-gray-500'
                  }`}
                  title={portalEnabled ? 'Client portal active' : 'Client portal inactive'}
                >
                  {portalEnabled ? (
                    <Globe className="h-3 w-3" />
                  ) : (
                    <Lock className="h-3 w-3" />
                  )}
                  <span className="hidden sm:inline">
                    {portalEnabled ? 'Portal Active' : 'Portal Off'}
                  </span>
                </div>
              </div>

              {clientName && (
                <p className="text-sm text-gray-500 mt-0.5">{clientName}</p>
              )}
            </div>
          </div>

          {/* Right: Actions */}
          <div className="flex items-center gap-3">
            {/* Activity Button */}
            {onShowActivity && (
              <IconButton
                variant="ghost"
                onClick={onShowActivity}
                icon={<Clock className="h-5 w-5" />}
                className="hidden sm:inline-flex"
                label="View activity"
              />
            )}

            {/* Research Toggle */}
            <div className="flex items-center gap-2">
              <Settings className="h-4 w-4 text-gray-400 hidden sm:block" />
              <span className="text-sm text-gray-500 hidden sm:block">Research</span>
              <button
                onClick={onBaselineToggle}
                className={`
                  relative inline-flex h-6 w-11 items-center rounded-full transition-colors
                  ${baseline?.baseline_ready ? 'bg-[#009b87]' : 'bg-gray-300'}
                `}
                aria-label="Toggle research access"
              >
                <span
                  className={`
                    inline-block h-4 w-4 transform rounded-full bg-white transition-transform shadow-sm
                    ${baseline?.baseline_ready ? 'translate-x-6' : 'translate-x-1'}
                  `}
                />
              </button>
            </div>

            {/* Refresh Button */}
            <IconButton
              icon={<RefreshCw className="h-4 w-4" />}
              label="Refresh data"
              variant="secondary"
              onClick={onRefresh}
            />
          </div>
        </div>
      </div>
    </header>
  )
}

/**
 * CompactHeader Component
 *
 * Simplified header for mobile screens
 */

interface CompactHeaderProps {
  projectId: string
  projectName: string
  onRefresh: () => void
}

export function CompactHeader({ projectId, projectName, onRefresh }: CompactHeaderProps) {
  return (
    <header className="bg-white border-b border-gray-200 lg:hidden">
      <div className="px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link
            href="/projects"
            className="text-gray-500 hover:text-gray-900 transition-colors"
          >
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-base font-semibold text-gray-900 truncate max-w-[200px]">
              {projectName}
            </h1>
          </div>
        </div>
        <IconButton
          icon={<RefreshCw className="h-4 w-4" />}
          label="Refresh"
          variant="secondary"
          size="sm"
          onClick={onRefresh}
        />
      </div>
    </header>
  )
}
