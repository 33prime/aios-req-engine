'use client'

import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import PortalSidebar from '@/components/portal/PortalSidebar'
import { getPortalDashboard } from '@/lib/api'
import { getPortalWorkflowPairs, listInfoRequests, getValidationQueue, getPortalProjectContext } from '@/lib/api/portal'
import type { PortalRole, PortalDashboard, InfoRequest, ValidationQueueResponse, ProjectContextData } from '@/types/portal'
import type { WorkflowPair } from '@/types/workspace'

// ============================================================================
// Portal Context
// ============================================================================

interface PortalContextValue {
  projectId: string
  projectName: string
  portalRole: PortalRole
  dashboard: PortalDashboard | null
  loaded: boolean
  refreshDashboard: () => Promise<void>
  workflowPairs: WorkflowPair[]
  pendingWorkflows: number
  refreshWorkflows: () => Promise<void>
  sidebarHidden: boolean
  setSidebarHidden: (hidden: boolean) => void
  infoRequests: InfoRequest[]
  refreshInfoRequests: () => Promise<void>
  validationQueue: ValidationQueueResponse | null
  refreshValidation: () => Promise<void>
  projectContext: ProjectContextData | null
  refreshContext: () => Promise<void>
}

const PortalContext = createContext<PortalContextValue | null>(null)

export function usePortal(): PortalContextValue {
  const ctx = useContext(PortalContext)
  if (!ctx) throw new Error('usePortal must be used within PortalShell')
  return ctx
}

// ============================================================================
// Shell Component
// ============================================================================

interface PortalShellProps {
  projectId: string
  children: React.ReactNode
}

export default function PortalShell({ projectId, children }: PortalShellProps) {
  const [dashboard, setDashboard] = useState<PortalDashboard | null>(null)
  const [loaded, setLoaded] = useState(false)
  const [sidebarHidden, setSidebarHidden] = useState(false)
  const [workflowPairs, setWorkflowPairs] = useState<WorkflowPair[]>([])
  const [infoRequests, setInfoRequests] = useState<InfoRequest[]>([])
  const [validationQueue, setValidationQueue] = useState<ValidationQueueResponse | null>(null)
  const [projectContext, setProjectContext] = useState<ProjectContextData | null>(null)

  const fetchDashboard = useCallback(async () => {
    try {
      const data = await getPortalDashboard(projectId)
      setDashboard(data)
    } catch {
      // Fall back gracefully — sidebar renders with defaults
    } finally {
      setLoaded(true)
    }
  }, [projectId])

  const fetchWorkflows = useCallback(async () => {
    try {
      const pairs = await getPortalWorkflowPairs(projectId)
      setWorkflowPairs(pairs)
    } catch {
      // Non-critical — page will show empty state
    }
  }, [projectId])

  const fetchInfoRequests = useCallback(async () => {
    try {
      const data = await listInfoRequests(projectId)
      setInfoRequests(data)
    } catch {
      // Non-critical
    }
  }, [projectId])

  const fetchValidation = useCallback(async () => {
    try {
      const data = await getValidationQueue(projectId)
      setValidationQueue(data)
    } catch {
      // Non-critical
    }
  }, [projectId])

  const fetchContext = useCallback(async () => {
    try {
      const data = await getPortalProjectContext(projectId)
      setProjectContext(data)
    } catch {
      // Non-critical
    }
  }, [projectId])

  useEffect(() => {
    fetchDashboard()
    fetchWorkflows()
    fetchInfoRequests()
    fetchValidation()
    fetchContext()
  }, [fetchDashboard, fetchWorkflows, fetchInfoRequests, fetchValidation, fetchContext])

  const portalRole = dashboard?.portal_role ?? 'client_user'
  const projectName = dashboard?.project_name ?? ''

  // Badge counts for sidebar
  const teamCompletionPct = dashboard?.team_summary?.completion_pct ?? null
  const pendingWorkflows = workflowPairs.filter(
    wp => wp.confirmation_status !== 'confirmed_client'
  ).length

  const contextValue: PortalContextValue = {
    projectId,
    projectName,
    portalRole,
    dashboard,
    loaded,
    refreshDashboard: fetchDashboard,
    workflowPairs,
    pendingWorkflows,
    refreshWorkflows: fetchWorkflows,
    sidebarHidden,
    setSidebarHidden,
    infoRequests,
    refreshInfoRequests: fetchInfoRequests,
    validationQueue,
    refreshValidation: fetchValidation,
    projectContext,
    refreshContext: fetchContext,
  }

  return (
    <PortalContext.Provider value={contextValue}>
      {/* Sidebar */}
      {loaded && !sidebarHidden && (
        <PortalSidebar
          projectName={projectName}
          portalRole={portalRole}
          pendingWorkflows={pendingWorkflows}
          teamCompletionPct={teamCompletionPct}
        />
      )}

      {/* Main content */}
      <main className={`min-h-screen transition-[margin] ${sidebarHidden ? '' : 'ml-[220px]'}`}>
        <div className={sidebarHidden ? '' : 'px-8 py-8'}>
          {children}
        </div>
      </main>
    </PortalContext.Provider>
  )
}
