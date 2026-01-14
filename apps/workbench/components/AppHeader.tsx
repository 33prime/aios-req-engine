'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Settings } from 'lucide-react'
import OrganizationSwitcher from './organizations/OrganizationSwitcher'
import { CreateOrganizationModal } from './organizations'

export default function AppHeader() {
  const [showCreateOrgModal, setShowCreateOrgModal] = useState(false)

  const handleOrgCreated = () => {
    // Refresh the page to update organization data
    window.location.reload()
  }

  return (
    <>
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-3">
            <div className="flex items-center gap-6">
              <Link href="/projects" className="text-xl font-bold text-gray-900 hover:text-emerald-600 transition-colors">
                Consultant Workbench
              </Link>
              <div className="h-6 w-px bg-zinc-200" />
              <OrganizationSwitcher onCreateOrg={() => setShowCreateOrgModal(true)} />
            </div>
            <div className="flex items-center gap-4">
              <Link
                href="/settings"
                className="p-2 hover:bg-zinc-100 rounded-lg transition-colors text-zinc-500 hover:text-zinc-700"
                title="Settings"
              >
                <Settings className="w-5 h-5" />
              </Link>
              <div className="text-sm text-gray-500">
                AIOS Req Engine
              </div>
            </div>
          </div>
        </div>
      </header>

      <CreateOrganizationModal
        isOpen={showCreateOrgModal}
        onClose={() => setShowCreateOrgModal(false)}
        onSuccess={handleOrgCreated}
      />
    </>
  )
}
