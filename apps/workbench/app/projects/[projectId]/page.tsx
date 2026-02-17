/**
 * Project Workspace - Canvas-based UI
 *
 * This is the main workspace layout with:
 * - Fixed sidebar navigation
 * - Phase switcher (Overview/Discovery/Build/Live)
 * - Requirements canvas with drag & drop
 * - Collaboration panel
 * - Launch progress banner (when arriving from ProjectLaunchWizard)
 *
 * Previous tab-based version removed 2026-01-30
 */

'use client'

import { useState, useCallback } from 'react'
import { useParams, useSearchParams, useRouter } from 'next/navigation'
import { WorkspaceLayout } from '@/components/workspace'
import { LaunchProgress } from '../components/LaunchProgress'

export default function ProjectWorkspacePage() {
  const params = useParams()
  const searchParams = useSearchParams()
  const router = useRouter()
  const projectId = params.projectId as string
  const launchId = searchParams.get('launch')
  const [showLaunch, setShowLaunch] = useState(!!launchId)

  const handleDismissLaunch = useCallback(() => {
    setShowLaunch(false)
    router.replace(`/projects/${projectId}`)
  }, [router, projectId])

  return (
    <>
      {showLaunch && launchId && (
        <LaunchProgress
          projectId={projectId}
          launchId={launchId}
          projectName="Your Project"
          onDismiss={handleDismissLaunch}
        />
      )}
      <WorkspaceLayout projectId={projectId} />
    </>
  )
}
