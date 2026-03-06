'use client'

import { useCallback, useState } from 'react'
import { BarChart3, MessageSquare } from 'lucide-react'
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

type CollaborateTab = 'intel' | 'collab'

interface CollaborateViewProps {
  projectId: string
  onNavigateToPhase?: (phase: WorkspacePhase) => void
}

export function CollaborateView({ projectId, onNavigateToPhase }: CollaborateViewProps) {
  const [activeTab, setActiveTab] = useState<CollaborateTab>('intel')
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
    <div className="max-w-5xl mx-auto">
      {/* Client Identity Card — always visible */}
      <ClientIdentityCard projectId={projectId} />

      {/* Tab switcher */}
      <div className="mt-5 flex items-center gap-1 border-b border-border">
        <button
          onClick={() => setActiveTab('intel')}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'intel'
              ? 'border-brand-primary text-brand-primary'
              : 'border-transparent text-text-placeholder hover:text-text-secondary'
          }`}
        >
          <BarChart3 className="w-4 h-4" />
          Client Intel
        </button>
        <button
          onClick={() => setActiveTab('collab')}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'collab'
              ? 'border-brand-primary text-brand-primary'
              : 'border-transparent text-text-placeholder hover:text-text-secondary'
          }`}
        >
          <MessageSquare className="w-4 h-4" />
          Collaboration
        </button>
      </div>

      {/* Tab content */}
      <div className="mt-6">
        {activeTab === 'intel' && (
          <div className="space-y-4">
            <PainValueCenter projectId={projectId} />
            <StakeholderMapSection projectId={projectId} />
          </div>
        )}

        {activeTab === 'collab' && (
          <div className="space-y-4">
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
        )}
      </div>
    </div>
  )
}
