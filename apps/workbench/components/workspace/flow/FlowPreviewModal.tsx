'use client'

import type { SolutionFlowStepDetail, PersonaSummary } from '@/types/workspace'
import { PATTERN_LABELS } from '@/lib/solution-flow-constants'
import { getPatternRenderer } from './patterns'
import { NavItem } from './patterns/shared'
import { X } from 'lucide-react'

interface FlowPreviewModalProps {
  step: { title: string; actors: string[] }
  detail: SolutionFlowStepDetail
  isOpen: boolean
  onClose: () => void
  personas: PersonaSummary[]
  projectName?: string
}

function getPersonaColor(name: string): string {
  const palette = ['#3FAF7A', '#044159', '#2D6B4A', '#0A1E2F']
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash)
  return palette[Math.abs(hash) % palette.length]
}

function getInitials(name: string): string {
  return name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
}

/** Extract first sentence from text */
function firstSentence(text: string): string {
  const match = text.match(/^[^.!?]+[.!?]/)
  return match ? match[0] : text.slice(0, 120)
}

export function FlowPreviewModal({ step, detail, isOpen, onClose, personas, projectName }: FlowPreviewModalProps) {
  if (!isOpen) return null

  const actor = step.actors[0] || 'User'
  const color = getPersonaColor(actor)
  const initials = getInitials(actor)
  const pattern = detail.implied_pattern || 'dashboard'
  const fields = detail.information_fields || []
  const appName = projectName || 'AppName'

  // Story overlay
  const storyHeadline = detail.story_headline || (detail.mock_data_narrative ? firstSentence(detail.mock_data_narrative) : null)

  // AI presence
  const agentName = detail.ai_config?.agent_name

  // Pattern renderer
  const PatternComponent = getPatternRenderer(pattern)

  return (
    <div
      className="fixed top-0 left-0 bottom-0 z-[190] flex items-stretch"
      style={{ right: 480, background: 'rgba(10,30,47,0.4)' }}
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="flex-1 flex items-center justify-center p-6">
        <div
          className="bg-white rounded-xl w-full flex flex-col overflow-hidden"
          style={{
            maxWidth: 800,
            maxHeight: '92vh',
            boxShadow: '0 20px 60px rgba(10,30,47,0.25)',
            animation: 'previewIn 0.3s ease',
          }}
        >
          {/* Browser chrome */}
          <div
            className="flex items-center px-3.5 py-2 flex-shrink-0 gap-2"
            style={{ background: 'linear-gradient(180deg, #FAFAFA 0%, #F0F0F0 100%)', borderBottom: '1px solid #E2E8F0' }}
          >
            <div className="flex gap-1">
              <div className="w-2 h-2 rounded-full" style={{ background: '#FF5F57' }} />
              <div className="w-2 h-2 rounded-full" style={{ background: '#FEBC2E' }} />
              <div className="w-2 h-2 rounded-full" style={{ background: '#28C840' }} />
            </div>
            <div className="flex-1 text-center text-[10px] font-medium" style={{ color: '#718096' }}>
              {step.title}
            </div>
            <button
              onClick={onClose}
              className="w-[22px] h-[22px] rounded-full flex items-center justify-center transition-colors"
              style={{ border: '1px solid #E2E8F0', background: '#fff', color: '#718096' }}
              onMouseEnter={e => { e.currentTarget.style.background = '#EDF2F7'; e.currentTarget.style.color = '#0A1E2F' }}
              onMouseLeave={e => { e.currentTarget.style.background = '#fff'; e.currentTarget.style.color = '#718096' }}
            >
              <X size={10} />
            </button>
          </div>

          {/* App body */}
          <div className="flex-1 overflow-y-auto bg-white relative">
            {/* App top bar */}
            <div className="flex items-center px-4 py-2" style={{ borderBottom: '1px solid #E2E8F0' }}>
              <div className="text-[11px] font-bold mr-2.5" style={{ color: '#3FAF7A' }}>{appName}</div>
              <div className="flex gap-0.5">
                <NavItem label="Dashboard" />
                <NavItem label={step.title.split(' ').slice(0, 2).join(' ')} active />
                <NavItem label="Reports" />
                <NavItem label="Settings" />
              </div>
              <div className="ml-auto flex items-center gap-1.5">
                <span className="text-[9px]" style={{ color: '#718096' }}>{actor}</span>
                <div
                  className="w-5 h-5 rounded-full flex items-center justify-center text-[6px] font-bold text-white"
                  style={{ background: color }}
                >
                  {initials}
                </div>
              </div>
            </div>

            {/* Story overlay strip */}
            {storyHeadline && (
              <div
                className="px-4 py-2"
                style={{ background: 'rgba(63,175,122,0.03)', borderBottom: '1px solid rgba(63,175,122,0.10)' }}
              >
                <div className="text-[10px] leading-snug" style={{ color: '#2D3748', borderLeft: '2px solid #3FAF7A', paddingLeft: 8 }}>
                  {storyHeadline}
                </div>
              </div>
            )}

            {/* Content */}
            <div className="p-4">
              <div className="text-[15px] font-bold mb-[3px]" style={{ color: '#0A1E2F' }}>
                {step.title}
              </div>
              <div className="text-[10px] mb-3.5" style={{ color: '#718096' }}>
                {PATTERN_LABELS[pattern] || pattern} view
              </div>

              {/* Pattern render via registry */}
              <PatternComponent fields={fields} step={step} detail={detail} projectName={projectName} />
            </div>

            {/* AI presence indicator */}
            {agentName && (
              <div
                className="absolute bottom-3 right-3 flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg"
                style={{ background: 'rgba(4,65,89,0.04)', border: '1px solid rgba(4,65,89,0.10)' }}
              >
                <span className="text-[10px]" style={{ color: '#044159' }}>&#x25C8;</span>
                <span className="text-[9px] font-medium" style={{ color: '#044159' }}>{agentName}</span>
                <span className="text-[8px]" style={{ color: '#A0AEC0' }}>&middot; Active</span>
              </div>
            )}
          </div>
        </div>
      </div>

      <style jsx>{`
        @keyframes previewIn {
          from { opacity: 0; transform: scale(0.96) translateY(10px); }
          to { opacity: 1; transform: scale(1) translateY(0); }
        }
      `}</style>
    </div>
  )
}
