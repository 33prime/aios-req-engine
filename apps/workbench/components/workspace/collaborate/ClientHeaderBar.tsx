'use client'

import { useState } from 'react'
import { Plus } from 'lucide-react'
import { useCollaborationCurrent } from '@/lib/hooks/use-api'
import { ClientPortalModal } from '@/components/collaboration/ClientPortalModal'

interface ClientHeaderBarProps {
  projectId: string
}

export function ClientHeaderBar({ projectId }: ClientHeaderBarProps) {
  const { data: collab } = useCollaborationCurrent(projectId)
  const [showInvite, setShowInvite] = useState(false)

  const clientsInvited = collab?.portal_sync?.clients_invited ?? 0
  const clientsActive = collab?.portal_sync?.clients_active ?? 0

  return (
    <>
      <div className="bg-white rounded-2xl border border-border shadow-sm p-4">
        <div className="flex items-center gap-4 flex-wrap">
          {clientsInvited > 0 ? (
            <div className="flex items-center gap-3">
              <span className="text-[11px] text-text-placeholder uppercase tracking-wider font-semibold">Team</span>
              <div className="flex items-center gap-1.5">
                <span className={`w-2 h-2 rounded-full ${clientsActive > 0 ? 'bg-brand-primary' : 'bg-border'}`} />
                <span className="text-sm font-medium text-text-body">
                  {clientsInvited} invited
                </span>
                {clientsActive > 0 && (
                  <span className="text-[11px] text-text-placeholder">
                    &middot; {clientsActive} active
                  </span>
                )}
              </div>
            </div>
          ) : (
            <span className="text-[12px] text-text-placeholder">No clients invited yet</span>
          )}

          <button
            onClick={() => setShowInvite(true)}
            className="ml-auto border border-dashed border-border rounded-xl px-3 py-1.5 text-[12px] text-brand-primary hover:bg-brand-primary-light transition-colors font-medium flex items-center gap-1.5"
          >
            <Plus className="w-3.5 h-3.5" />
            Invite
          </button>
        </div>
      </div>

      <ClientPortalModal
        projectId={projectId}
        projectName="Project"
        isOpen={showInvite}
        onClose={() => setShowInvite(false)}
      />
    </>
  )
}
