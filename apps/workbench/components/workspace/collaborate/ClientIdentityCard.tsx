'use client'

import { useState, useMemo } from 'react'
import { Plus, Building2 } from 'lucide-react'
import { useBRDData, useCollaborationCurrent, useSalesIntel } from '@/lib/hooks/use-api'
import { useProjectStakeholders } from '@/lib/hooks/use-api'
import { ClientPortalModal } from '@/components/collaboration/ClientPortalModal'
import { MeddicTracker, computeMeddicDimensions } from './MeddicTracker'

interface ClientIdentityCardProps {
  projectId: string
}

const PHASE_LABELS: Record<string, string> = {
  pre_discovery: 'Pre-Discovery',
  discovery: 'Discovery',
  validation: 'Validation',
  prototype: 'Prototype',
  proposal: 'Proposal',
  closed: 'Closed',
}

export function ClientIdentityCard({ projectId }: ClientIdentityCardProps) {
  const { data: brd } = useBRDData(projectId)
  const { data: collab, mutate } = useCollaborationCurrent(projectId)
  const { data: salesIntel } = useSalesIntel(projectId)
  const { data: stakeholderData } = useProjectStakeholders(projectId)
  const [showInvite, setShowInvite] = useState(false)

  const companyName = brd?.business_context?.company_name || salesIntel?.client_name || 'Client'
  const industry = brd?.business_context?.industry || salesIntel?.client_industry
  const vision = brd?.business_context?.vision
  const phase = collab?.collaboration_phase
  const clientsInvited = collab?.portal_sync?.clients_invited ?? 0
  const clientsActive = collab?.portal_sync?.clients_active ?? 0

  // Initials for avatar
  const initials = companyName
    .split(/\s+/)
    .slice(0, 2)
    .map(w => w[0])
    .join('')
    .toUpperCase()

  // MEDDIC dimensions
  const meddicDimensions = useMemo(() => {
    const painPoints = brd?.business_context?.pain_points ?? []
    const successMetrics = brd?.business_context?.success_metrics ?? []
    // Use enriched stakeholders if available, fall back to BRD summary
    const stakeholders = stakeholderData?.stakeholders ?? brd?.stakeholders ?? []
    return computeMeddicDimensions(painPoints, stakeholders, successMetrics, phase)
  }, [brd, stakeholderData, phase])

  return (
    <>
      <div className="bg-white rounded-2xl border border-border shadow-sm p-5">
        {/* Row 1: Identity + status */}
        <div className="flex items-center gap-4 flex-wrap">
          {/* Company avatar */}
          <div className="w-11 h-11 rounded-xl bg-accent flex items-center justify-center text-white font-bold text-sm shrink-0">
            {initials || <Building2 className="w-5 h-5" />}
          </div>

          {/* Name + badges */}
          <div className="flex items-center gap-2.5 flex-wrap min-w-0">
            <h2 className="text-lg font-semibold text-text-body truncate">{companyName}</h2>
            {industry && (
              <span className="px-2 py-0.5 rounded-full bg-surface-subtle text-[11px] font-medium text-text-secondary">
                {industry}
              </span>
            )}
            {phase && (
              <span className="px-2 py-0.5 rounded-full bg-brand-primary-light text-[11px] font-semibold text-brand-primary">
                {PHASE_LABELS[phase] || phase}
              </span>
            )}
          </div>

          {/* Right side: team count + invite */}
          <div className="ml-auto flex items-center gap-3">
            {clientsInvited > 0 && (
              <div className="flex items-center gap-1.5 text-sm text-text-secondary">
                <span className={`w-2 h-2 rounded-full ${clientsActive > 0 ? 'bg-brand-primary' : 'bg-border'}`} />
                <span className="font-medium">{clientsInvited} invited</span>
                {clientsActive > 0 && (
                  <span className="text-text-placeholder">&middot; {clientsActive} active</span>
                )}
              </div>
            )}
            <button
              onClick={() => setShowInvite(true)}
              className="border border-dashed border-border rounded-xl px-3 py-1.5 text-[12px] text-brand-primary hover:bg-brand-primary-light transition-colors font-medium flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" />
              Invite
            </button>
          </div>
        </div>

        {/* Row 2: Vision one-liner */}
        {vision && (
          <p className="mt-2.5 text-sm text-text-secondary line-clamp-2 pl-[60px]">
            {vision}
          </p>
        )}

        {/* Row 3: MEDDIC tracker */}
        <div className="mt-3 pl-[60px]">
          <MeddicTracker dimensions={meddicDimensions} />
        </div>
      </div>

      <ClientPortalModal
        projectId={projectId}
        projectName={companyName}
        isOpen={showInvite}
        onClose={() => setShowInvite(false)}
        onRefresh={() => mutate()}
      />
    </>
  )
}
