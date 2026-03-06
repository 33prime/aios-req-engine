/**
 * Portal Layout
 *
 * Client-facing layout with navigation tabs for the project portal.
 * PortalShell handles auth and role-based nav rendering client-side.
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
      {/* Nav + Content — client component handles header + role-based nav */}
      <PortalShell projectId={params.projectId}>
        {children}
      </PortalShell>

      {/* Footer */}
      <footer className="border-t border-border mt-12">
        <div className="max-w-5xl mx-auto px-4 py-6 text-center text-xs text-text-placeholder">
          &copy; {new Date().getFullYear()} All rights reserved.
        </div>
      </footer>
    </div>
  )
}
