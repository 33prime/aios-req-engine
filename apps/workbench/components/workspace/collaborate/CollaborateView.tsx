'use client'

import { useCallback } from 'react'
import { Users } from 'lucide-react'
import { ClientHeaderBar } from './ClientHeaderBar'
import { ActionQueueSection } from './ActionQueueSection'
import { QuestionBoardSection } from './QuestionBoardSection'
import { AgendaCenterSection } from './AgendaCenterSection'
import { PrototypeEngagementSection } from './PrototypeEngagementSection'
import { ClientActivitySection } from './ClientActivitySection'
import type { WorkspacePhase } from '../PhaseSwitcher'

interface CollaborateViewProps {
  projectId: string
  onNavigateToPhase?: (phase: WorkspacePhase) => void
}

export function CollaborateView({ projectId, onNavigateToPhase }: CollaborateViewProps) {
  const scrollToSection = useCallback((sectionId: string) => {
    const el = document.getElementById(sectionId)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' })
      // Brief highlight flash
      el.classList.add('ring-2', 'ring-[#3FAF7A]/30')
      setTimeout(() => el.classList.remove('ring-2', 'ring-[#3FAF7A]/30'), 2000)
    }
  }, [])

  return (
    <div className="max-w-5xl mx-auto">
      {/* Page Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-[#3FAF7A]/10 flex items-center justify-center">
            <Users className="w-5 h-5 text-[#3FAF7A]" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-[#333333]">Collaborate</h1>
            <p className="text-[12px] text-[#999999]">Manage client engagement & portal</p>
          </div>
        </div>
      </div>

      {/* Client Header Bar */}
      <ClientHeaderBar projectId={projectId} />

      {/* Accordion Sections */}
      <div className="space-y-4 mt-6">
        <ActionQueueSection
          projectId={projectId}
          onScrollToSection={scrollToSection}
        />
        <div id="collab-questions" className="rounded-2xl transition-all duration-500">
          <QuestionBoardSection projectId={projectId} />
        </div>
        <div id="collab-agenda" className="rounded-2xl transition-all duration-500">
          <AgendaCenterSection projectId={projectId} />
        </div>
        <div id="collab-prototype" className="rounded-2xl transition-all duration-500">
          <PrototypeEngagementSection projectId={projectId} />
        </div>
        <div id="collab-activity" className="rounded-2xl transition-all duration-500">
          <ClientActivitySection projectId={projectId} />
        </div>
      </div>
    </div>
  )
}
