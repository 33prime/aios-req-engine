/**
 * Portal Layout
 *
 * Minimal server-side wrapper — all chrome lives in PortalShell (client component).
 */

import React from 'react'
import PortalShell from './PortalShell'

export default function PortalLayout({
  children,
  params,
}: {
  children: React.ReactNode
  params: { projectId: string }
}) {
  return (
    <div className="min-h-screen bg-surface-page font-[var(--font-body)]">
      <PortalShell projectId={params.projectId}>
        {children}
      </PortalShell>
    </div>
  )
}
