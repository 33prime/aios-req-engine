'use client'

import { useEffect, useState } from 'react'
import { LogOut } from 'lucide-react'
import PortalNav from '@/components/portal/PortalNav'
import { getPortalDashboard } from '@/lib/api'
import type { PortalRole } from '@/types/portal'

interface PortalShellProps {
  projectId: string
  children: React.ReactNode
}

export default function PortalShell({ projectId, children }: PortalShellProps) {
  const [portalRole, setPortalRole] = useState<PortalRole>('client_user')
  const [projectName, setProjectName] = useState<string>('')
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    getPortalDashboard(projectId)
      .then(data => {
        setPortalRole(data.portal_role)
        setProjectName(data.project_name)
      })
      .catch(() => {
        // Fall back to client_user on error
      })
      .finally(() => setLoaded(true))
  }, [projectId])

  const initial = projectName ? projectName.charAt(0).toUpperCase() : '?'

  return (
    <>
      {/* Header */}
      <header className="bg-surface-card border-b border-border">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-accent rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">{initial}</span>
            </div>
            <span className="font-semibold text-text-primary">
              {projectName || 'Project Portal'}
            </span>
          </div>
          <button
            onClick={() => {
              localStorage.removeItem('access_token')
              window.location.href = '/'
            }}
            className="flex items-center gap-1.5 text-sm text-text-muted hover:text-text-body transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Sign out
          </button>
        </div>
      </header>

      {loaded && (
        <PortalNav
          projectId={projectId}
          portalRole={portalRole}
          projectName={projectName}
        />
      )}
      <main className="max-w-5xl mx-auto px-4 py-8">
        {children}
      </main>
    </>
  )
}
