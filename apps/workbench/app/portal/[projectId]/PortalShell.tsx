'use client'

import { useEffect, useState } from 'react'
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

  return (
    <>
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
