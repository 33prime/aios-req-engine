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
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-[#009b87] rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">A</span>
            </div>
            <span className="font-semibold text-gray-900">AIOS Client Portal</span>
          </div>
        </div>
      </header>

      {/* Nav + Content — client component handles role-based nav */}
      <PortalShell projectId={params.projectId}>
        {children}
      </PortalShell>

      {/* Footer */}
      <footer className="border-t border-gray-200 mt-12">
        <div className="max-w-5xl mx-auto px-4 py-6 text-center text-sm text-gray-500">
          Powered by AIOS Requirements Engine
        </div>
      </footer>
    </div>
  )
}
