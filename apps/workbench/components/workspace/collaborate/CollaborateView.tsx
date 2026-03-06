'use client'

import { useCallback, useState } from 'react'
import { ClientIdentityCard } from './ClientIdentityCard'
import { PainValueCenter } from './PainValueCenter'
import { StakeholderMapSection } from './StakeholderMapSection'
import { ActionQueueSection } from './ActionQueueSection'
import { QuestionBoardSection } from './QuestionBoardSection'
import { AgendaCenterSection } from './AgendaCenterSection'
import { PrototypeEngagementSection } from './PrototypeEngagementSection'
import { ClientActivitySection } from './ClientActivitySection'
import { ClientStagingSection } from './ClientStagingSection'
import type { WorkspacePhase } from '../PhaseSwitcher'

interface CollaborateViewProps {
  projectId: string
  onNavigateToPhase?: (phase: WorkspacePhase) => void
}

export function CollaborateView({ projectId, onNavigateToPhase }: CollaborateViewProps) {
  const [synthesizeTrigger, setSynthesizeTrigger] = useState(0)

  const scrollToSection = useCallback((sectionId: string) => {
    const el = document.getElementById(sectionId)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' })
      el.classList.add('ring-2', 'ring-brand-primary/30')
      setTimeout(() => el.classList.remove('ring-2', 'ring-brand-primary/30'), 2000)
    }
  }, [])

  const handleTriggerSynthesize = useCallback(() => {
    setSynthesizeTrigger(prev => prev + 1)
  }, [])

  return (
    <div className="max-w-7xl mx-auto">
      {/* Client Identity Card — full width */}
      <ClientIdentityCard projectId={projectId} />

      {/* Two-column layout */}
      <div className="mt-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Strategic — Pain, Value, Stakeholders */}
        <div className="lg:col-span-7 space-y-4">
          <PainValueCenter projectId={projectId} />
          <StakeholderMapSection projectId={projectId} />
        </div>

        {/* Right: Operational — Existing sections (unchanged) */}
        <div className="lg:col-span-5 space-y-4">
          <ActionQueueSection
            projectId={projectId}
            onScrollToSection={scrollToSection}
            onTriggerSynthesize={handleTriggerSynthesize}
          />
          <div id="collab-questions" className="rounded-2xl transition-all duration-500">
            <QuestionBoardSection
              projectId={projectId}
              synthesizeTrigger={synthesizeTrigger}
            />
          </div>
          <div id="collab-client-exploration" className="rounded-2xl transition-all duration-500">
            <ClientStagingSection projectId={projectId} />
          </div>
          <div id="collab-prototype" className="rounded-2xl transition-all duration-500">
            <PrototypeEngagementSection projectId={projectId} />
          </div>
          <div id="collab-agenda" className="rounded-2xl transition-all duration-500">
            <AgendaCenterSection projectId={projectId} />
          </div>
          <div id="collab-activity" className="rounded-2xl transition-all duration-500">
            <ClientActivitySection projectId={projectId} />
          </div>
        </div>
      </div>
    </div>
  )
}
