/**
 * WorkspaceHeader Component
 *
 * Main workspace header with:
 * - Project info
 * - Research toggle (baseline)
 * - Agent action buttons
 * - Signal/Research input
 *
 * Usage:
 *   <WorkspaceHeader
 *     projectId={projectId}
 *     baseline={baseline}
 *     onBaselineToggle={handleToggle}
 *     onRefresh={handleRefresh}
 *   />
 */

'use client'

import React, { useState } from 'react'
import {
  RefreshCw,
  Settings,
  Play,
  ChevronDown,
  Upload,
  FileText
} from 'lucide-react'
import { Button, IconButton } from '@/components/ui'

interface WorkspaceHeaderProps {
  projectId: string
  baseline: {
    baseline_ready: boolean
    client_signal_count: number
    fact_count: number
  } | null
  onBaselineToggle: () => void
  onRefresh: () => void
  onRunAgent?: (agentType: 'build' | 'reconcile' | 'redteam' | 'enrich-prd' | 'enrich-vp') => void
  onAddSignal?: () => void
  onAddResearch?: () => void
}

export function WorkspaceHeader({
  projectId,
  baseline,
  onBaselineToggle,
  onRefresh,
  onRunAgent,
  onAddSignal,
  onAddResearch
}: WorkspaceHeaderProps) {
  const [showAgentMenu, setShowAgentMenu] = useState(false)

  return (
    <header className="bg-white border-b border-ui-cardBorder">
      <div className="px-6 py-4">
        <div className="flex items-center justify-between">
          {/* Left: Project Info */}
          <div className="flex items-center gap-4">
            <div>
              <h1 className="heading-1">Requirements Workspace</h1>
              <p className="text-support text-ui-supportText mt-1">
                Project ID: <span className="font-mono text-xs">{projectId}</span>
              </p>
            </div>

            {/* Baseline Status Indicator */}
            {baseline && (
              <div className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-ui-background rounded-lg border border-ui-cardBorder">
                <div className={`w-2 h-2 rounded-full ${baseline.baseline_ready ? 'bg-green-500' : 'bg-gray-300'}`} />
                <span className="text-xs font-medium text-ui-bodyText">
                  {baseline.client_signal_count} signals • {baseline.fact_count} facts
                </span>
              </div>
            )}
          </div>

          {/* Right: Actions */}
          <div className="flex items-center gap-3">
            {/* Add Signal/Research Buttons */}
            {onAddSignal && (
              <Button
                variant="outline"
                onClick={onAddSignal}
                icon={<Upload className="h-4 w-4" />}
                className="hidden sm:inline-flex"
              >
                Add Signal
              </Button>
            )}

            {onAddResearch && (
              <Button
                variant="outline"
                onClick={onAddResearch}
                icon={<FileText className="h-4 w-4" />}
                className="hidden sm:inline-flex"
              >
                Add Research
              </Button>
            )}

            {/* Agent Actions Dropdown */}
            {onRunAgent && (
              <div className="relative">
                <Button
                  variant="secondary"
                  onClick={() => setShowAgentMenu(!showAgentMenu)}
                  icon={<Play className="h-4 w-4" />}
                  className="hidden sm:inline-flex"
                >
                  Run Agent
                  <ChevronDown className="h-4 w-4 ml-1" />
                </Button>

                {showAgentMenu && (
                  <>
                    {/* Backdrop */}
                    <div
                      className="fixed inset-0 z-30"
                      onClick={() => setShowAgentMenu(false)}
                    />

                    {/* Dropdown Menu */}
                    <div className="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-ui-cardBorder py-1 z-40">
                      <AgentMenuItem
                        label="Build State"
                        description="Extract facts and build state"
                        onClick={() => {
                          onRunAgent('build')
                          setShowAgentMenu(false)
                        }}
                      />
                      <AgentMenuItem
                        label="Reconcile"
                        description="Reconcile state with signals"
                        onClick={() => {
                          onRunAgent('reconcile')
                          setShowAgentMenu(false)
                        }}
                      />
                      <AgentMenuItem
                        label="Enrich PRD"
                        description="Enrich PRD sections"
                        onClick={() => {
                          onRunAgent('enrich-prd')
                          setShowAgentMenu(false)
                        }}
                      />
                      <AgentMenuItem
                        label="Enrich VP"
                        description="Enrich Value Path steps"
                        onClick={() => {
                          onRunAgent('enrich-vp')
                          setShowAgentMenu(false)
                        }}
                      />
                      <div className="border-t border-ui-cardBorder my-1" />
                      <AgentMenuItem
                        label="Red Team"
                        description="Run gap analysis"
                        onClick={() => {
                          onRunAgent('redteam')
                          setShowAgentMenu(false)
                        }}
                        variant="primary"
                      />
                    </div>
                  </>
                )}
              </div>
            )}

            {/* Research Toggle */}
            <div className="flex items-center gap-2">
              <Settings className="h-4 w-4 text-ui-supportText hidden sm:block" />
              <span className="text-sm text-ui-supportText hidden sm:block">Research</span>
              <button
                onClick={onBaselineToggle}
                className={`
                  relative inline-flex h-6 w-11 items-center rounded-full transition-colors
                  ${baseline?.baseline_ready ? 'bg-green-600' : 'bg-gray-300'}
                `}
                aria-label="Toggle research access"
              >
                <span
                  className={`
                    inline-block h-4 w-4 transform rounded-full bg-white transition-transform
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
 * AgentMenuItem Component
 *
 * Menu item for agent dropdown
 */

interface AgentMenuItemProps {
  label: string
  description: string
  onClick: () => void
  variant?: 'default' | 'primary'
}

function AgentMenuItem({ label, description, onClick, variant = 'default' }: AgentMenuItemProps) {
  return (
    <button
      onClick={onClick}
      className={`
        w-full px-4 py-2 text-left hover:bg-ui-background transition-colors
        ${variant === 'primary' ? 'text-brand-primary' : 'text-ui-bodyText'}
      `}
    >
      <div className="font-medium text-sm">{label}</div>
      <div className="text-xs text-ui-supportText mt-0.5">{description}</div>
    </button>
  )
}

/**
 * CompactHeader Component
 *
 * Simplified header for mobile screens
 */

interface CompactHeaderProps {
  projectId: string
  onRefresh: () => void
}

export function CompactHeader({ projectId, onRefresh }: CompactHeaderProps) {
  return (
    <header className="bg-white border-b border-ui-cardBorder lg:hidden">
      <div className="px-4 py-3 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-ui-headingDark">Workspace</h1>
          <p className="text-xs text-ui-supportText font-mono">{projectId.slice(0, 8)}...</p>
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
