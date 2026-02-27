/**
 * BottomDock - Fixed bottom-center bar with toggle buttons for panels
 *
 * Three panels: Unlocks (strategic outcomes + competitors), Evidence (sources), Memory (decisions + activity).
 * Unlocks and Memory panels open at 75vw x 75vh; Evidence keeps max-w-5xl.
 */

'use client'

import { Zap, Database, Brain, X } from 'lucide-react'
import { UnlocksPanel } from './panels/UnlocksPanel'
import { EvidencePanel } from './panels/EvidencePanel'
import { MemoryPanel } from './panels/memory/MemoryPanel'

type PanelType = 'context' | 'evidence' | 'history' | null

interface BottomDockProps {
  projectId: string
  activePanel: PanelType
  onPanelChange: (panel: PanelType) => void
}

const DOCK_BUTTONS = [
  { id: 'context' as const, icon: Zap, label: 'Unlocks' },
  { id: 'evidence' as const, icon: Database, label: 'Evidence' },
  { id: 'history' as const, icon: Brain, label: 'Memory' },
]

const PANEL_TITLES: Record<string, string> = {
  context: 'Unlocks',
  evidence: 'Evidence & Sources',
  history: 'Intelligence',
}

export function BottomDock({ projectId, activePanel, onPanelChange }: BottomDockProps) {
  const handleToggle = (panel: 'context' | 'evidence' | 'history') => {
    onPanelChange(activePanel === panel ? null : panel)
  }

  const isFullScreen = activePanel === 'history' || activePanel === 'context'

  return (
    <>
      {/* Backdrop — blurred */}
      {activePanel && (
        <div
          className="fixed inset-0 z-30 bg-black/30 backdrop-blur-sm"
          onClick={() => onPanelChange(null)}
        />
      )}

      {/* Centered modal */}
      {activePanel && (
        <div className="fixed inset-0 z-30 flex items-center justify-center p-8 pointer-events-none">
          <div
            className={`bg-white rounded-xl border border-border shadow-xl overflow-hidden flex flex-col pointer-events-auto ${
              isFullScreen
                ? 'w-[75vw] h-[75vh]'
                : 'w-full max-w-5xl max-h-[75vh]'
            }`}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-surface-muted shrink-0">
              <h3 className="text-base font-semibold text-text-body">
                {PANEL_TITLES[activePanel] || activePanel}
              </h3>
              <button
                onClick={() => onPanelChange(null)}
                className="p-1.5 rounded-lg text-text-placeholder hover:text-text-body hover:bg-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            {/* Content */}
            <div className={`flex-1 overflow-hidden ${isFullScreen ? '' : 'overflow-y-auto p-6'}`}>
              {activePanel === 'context' && <UnlocksPanel projectId={projectId} />}
              {activePanel === 'evidence' && <EvidencePanel projectId={projectId} />}
              {activePanel === 'history' && <MemoryPanel projectId={projectId} />}
            </div>
          </div>
        </div>
      )}

      {/* Dock bar */}
      <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-40">
        <div className="flex items-center gap-1 bg-white rounded-full border border-border shadow-lg px-2 py-1.5">
          {DOCK_BUTTONS.map((btn) => {
            const Icon = btn.icon
            const isActive = activePanel === btn.id
            return (
              <button
                key={btn.id}
                onClick={() => handleToggle(btn.id)}
                className={`
                  flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all
                  ${isActive
                    ? 'bg-brand-primary-light text-brand-primary'
                    : 'text-text-placeholder hover:text-text-body hover:bg-surface-muted'
                  }
                `}
                title={btn.label}
              >
                <Icon className="w-4 h-4" />
                <span>{btn.label}</span>
              </button>
            )
          })}
        </div>
      </div>
    </>
  )
}

export default BottomDock
