/**
 * Project Workspace - Canvas-based UI
 *
 * This is the main workspace layout with:
 * - Fixed sidebar navigation
 * - Phase switcher (Overview/Discovery/Build/Live)
 * - Requirements canvas with drag & drop
 * - Collaboration panel
 *
 * Previous tab-based version removed 2026-01-30
 */

'use client'

import { useParams } from 'next/navigation'
import { WorkspaceLayout } from '@/components/workspace'

export default function ProjectWorkspacePage() {
  const params = useParams()
  const projectId = params.projectId as string

  return <WorkspaceLayout projectId={projectId} />
}
