'use client'

import { useCallback, useState } from 'react'
import { Target, MessageSquare, ArrowUpRight, ArrowDownLeft } from 'lucide-react'
import { DealReadinessHero } from './DealReadinessHero'
import { ValueStorySection } from './deal-intelligence/ValueStorySection'
import { StakeholderOutcomeMap } from './deal-intelligence/StakeholderOutcomeMap'
import { ConversationPlaybook } from './deal-intelligence/ConversationPlaybook'
import { InvestmentCase } from './deal-intelligence/InvestmentCase'
import { ActionBar } from './ActionBar'
import { OutboxCard } from './OutboxCard'
import { ClientStagingSection } from './ClientStagingSection'
import { PrototypeStatusCard } from './PrototypeStatusCard'
import { ClientResponsesCard } from './ClientResponsesCard'
import { ExplorationResultsCard } from './ExplorationResultsCard'
import { ClientActivitySection } from './ClientActivitySection'
import type { WorkspacePhase } from '../PhaseSwitcher'

type CollaborateTab = 'intel' | 'collab'

interface CollaborateViewProps {
  projectId: string
  onNavigateToPhase?: (phase: WorkspacePhase) => void
}

export function CollaborateView({ projectId, onNavigateToPhase }: CollaborateViewProps) {
  const [activeTab, setActiveTab] = useState<CollaborateTab>('intel')
  const [synthesizeTrigger, setSynthesizeTrigger] = useState(0)
  const [explorationState, setExplorationState] = useState<{
    sessionId: string | null
    reviewState: string | null
  }>({ sessionId: null, reviewState: null })

  const handleTriggerSynthesize = useCallback(() => {
    setSynthesizeTrigger(prev => prev + 1)
  }, [])

  const handleNavigateToBuild = useCallback(() => {
    onNavigateToPhase?.('build')
  }, [onNavigateToPhase])

  const handleExplorationStateChange = useCallback((state: { sessionId: string | null; reviewState: string | null }) => {
    setExplorationState(state)
  }, [])

  return (
    <div className="max-w-6xl mx-auto">
      {/* Deal Readiness Hero — always visible above tabs */}
      <DealReadinessHero projectId={projectId} />

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
          <Target className="w-4 h-4" />
          Deal Intelligence
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
          <div className="space-y-3">
            <ValueStorySection projectId={projectId} />
            <StakeholderOutcomeMap projectId={projectId} />
            <ConversationPlaybook projectId={projectId} />
            <InvestmentCase projectId={projectId} />
          </div>
        )}

        {activeTab === 'collab' && (
          <div className="space-y-4">
            {/* Action Bar — slim priority alerts */}
            <ActionBar projectId={projectId} onTriggerSynthesize={handleTriggerSynthesize} />

            {/* 2-column grid: Outbox | Inbox */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              {/* OUTBOX — Consultant → Client */}
              <div className="space-y-4">
                <div className="flex items-center gap-2 px-1">
                  <ArrowUpRight className="w-4 h-4 text-text-placeholder" />
                  <span className="text-[11px] uppercase tracking-wider text-text-placeholder font-semibold">
                    Outbox
                  </span>
                  <span className="text-[10px] text-text-placeholder">
                    Consultant → Client
                  </span>
                </div>
                <OutboxCard projectId={projectId} synthesizeTrigger={synthesizeTrigger} />
                <ClientStagingSection projectId={projectId} onStateChange={handleExplorationStateChange} />
              </div>

              {/* INBOX — Client → Consultant */}
              <div className="space-y-4">
                <div className="flex items-center gap-2 px-1">
                  <ArrowDownLeft className="w-4 h-4 text-text-placeholder" />
                  <span className="text-[11px] uppercase tracking-wider text-text-placeholder font-semibold">
                    Inbox
                  </span>
                  <span className="text-[10px] text-text-placeholder">
                    Client → Consultant
                  </span>
                </div>
                <PrototypeStatusCard projectId={projectId} onNavigateToBuild={handleNavigateToBuild} />
                <ClientResponsesCard projectId={projectId} />
                {(explorationState.reviewState === 'exploring' || explorationState.reviewState === 'results') && (
                  <ExplorationResultsCard projectId={projectId} sessionId={explorationState.sessionId} />
                )}
                <ClientActivitySection projectId={projectId} />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
