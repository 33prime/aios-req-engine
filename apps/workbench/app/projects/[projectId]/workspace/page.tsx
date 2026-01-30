/**
 * Workspace Page - New canvas-based UI
 *
 * This is the new workspace layout with:
 * - Fixed sidebar navigation
 * - Phase switcher (Discovery/Build/Live)
 * - Requirements canvas with drag & drop
 * - Collaboration panel
 */

'use client'

import { useParams } from 'next/navigation'
import { WorkspaceLayout } from '@/components/workspace'

export default function WorkspacePage() {
  const params = useParams()
  const projectId = params.projectId as string

  return <WorkspaceLayout projectId={projectId} />
}
