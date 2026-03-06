'use client'

import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { MessageCircle } from 'lucide-react'
import PortalSidebar from '@/components/portal/PortalSidebar'
import { StationPanel } from '@/components/portal/StationPanel'
import { getPortalDashboard } from '@/lib/api'
import { getPortalWorkflowPairs, listInfoRequests, getValidationQueue, getPortalProjectContext } from '@/lib/api/portal'
import type { PortalRole, PortalDashboard, InfoRequest, ValidationQueueResponse, ProjectContextData, StationSlug } from '@/types/portal'
import type { WorkflowPair } from '@/types/workspace'

// ============================================================================
// Chat Config — pages register their context-aware chat
// ============================================================================

export interface PortalChatConfig {
  station: StationSlug
  title: string
  greeting: string
  children?: React.ReactNode
}

const DEFAULT_CHAT_CONFIG: PortalChatConfig = {
  station: 'tribal',
  title: 'Chat with AIOS',
  greeting: "Hi! I'm here to help with anything about your project. Ask me questions, share details, or tell me what's on your mind.",
}

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
  sidebarCollapsed: boolean
  setSidebarCollapsed: (collapsed: boolean) => void
  infoRequests: InfoRequest[]
  refreshInfoRequests: () => Promise<void>
  validationQueue: ValidationQueueResponse | null
  refreshValidation: () => Promise<void>
  projectContext: ProjectContextData | null
  refreshContext: () => Promise<void>
  chatOpen: boolean
  setChatOpen: (open: boolean) => void
  setChatConfig: (config: PortalChatConfig | null) => void
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
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [workflowPairs, setWorkflowPairs] = useState<WorkflowPair[]>([])
  const [infoRequests, setInfoRequests] = useState<InfoRequest[]>([])
  const [validationQueue, setValidationQueue] = useState<ValidationQueueResponse | null>(null)
  const [projectContext, setProjectContext] = useState<ProjectContextData | null>(null)
  const [chatOpen, setChatOpen] = useState(false)
  const chatConfigRef = useRef<PortalChatConfig | null>(null)
  const [, forceUpdate] = useState(0)

  const setChatConfig = useCallback((config: PortalChatConfig | null) => {
    chatConfigRef.current = config
    forceUpdate(n => n + 1)
  }, [])

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
    sidebarCollapsed,
    setSidebarCollapsed,
    infoRequests,
    refreshInfoRequests: fetchInfoRequests,
    validationQueue,
    refreshValidation: fetchValidation,
    projectContext,
    refreshContext: fetchContext,
    chatOpen,
    setChatOpen,
    setChatConfig,
  }

  return (
    <PortalContext.Provider value={contextValue}>
      {/* Sidebar */}
      {loaded && !sidebarHidden && (
        <PortalSidebar
          projectName={projectName}
          portalRole={portalRole}
          pendingWorkflows={pendingWorkflows}
          collapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(c => !c)}
        />
      )}

      {/* Main content */}
      <main className={`h-screen overflow-hidden transition-[margin] duration-200 ${
        sidebarHidden ? '' : sidebarCollapsed ? 'ml-[64px]' : 'ml-[220px]'
      }`}>
        {children}
      </main>

      {/* Page-aware chat side panel */}
      {chatOpen && (() => {
        const cfg = chatConfigRef.current ?? DEFAULT_CHAT_CONFIG
        return (
          <StationPanel
            onClose={() => setChatOpen(false)}
            icon={MessageCircle}
            title={cfg.title}
            station={cfg.station}
            projectId={projectId}
            chatGreeting={cfg.greeting}
            onDataChanged={fetchContext}
          >
            {cfg.children}
          </StationPanel>
        )
      })()}

      {/* Chat bubble — visible on all portal pages */}
      {!chatOpen && (
        <button
          onClick={() => setChatOpen(true)}
          className="fixed bottom-6 right-6 w-14 h-14 rounded-full bg-brand-primary text-white shadow-lg flex items-center justify-center z-50 hover:bg-brand-primary-hover hover:scale-105 transition-all"
        >
          <MessageCircle className="w-6 h-6" />
        </button>
      )}
    </PortalContext.Provider>
  )
}
