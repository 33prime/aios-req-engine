'use client'

import { HelpCircle, Users, Lightbulb } from 'lucide-react'
import type { DiscoveryThread } from '@/types/epic-overlay'

interface DiscoveryThreadCardProps {
  thread: DiscoveryThread
  isActive?: boolean
}

const KNOWLEDGE_LABELS: Record<string, { label: string; color: string }> = {
  document: { label: 'Document', color: 'bg-[#E8F5E9] text-[#25785A]' },
  meeting: { label: 'Meeting', color: 'bg-[#F4F4F4] text-[#37352f]' },
  portal: { label: 'Portal', color: 'bg-[#E8EDF2] text-[#0A1E2F]' },
  tribal: { label: 'Tribal', color: 'bg-[#F4F4F4] text-[#666666]' },
}

export default function DiscoveryThreadCard({ thread, isActive = false }: DiscoveryThreadCardProps) {
  const knowledgeInfo = thread.knowledge_type
    ? KNOWLEDGE_LABELS[thread.knowledge_type] || { label: thread.knowledge_type, color: 'bg-[#F4F4F4] text-[#666666]' }
    : null

  return (
    <div
      className={`rounded-xl border transition-colors ${
        isActive ? 'border-brand-primary bg-[#F0FAF4]' : 'border-border bg-white'
      }`}
    >
      <div className="px-4 py-3">
        {/* Header */}
        <div className="flex items-start gap-2 mb-2">
          <div className="w-6 h-6 rounded-lg bg-[#F4F4F4] flex items-center justify-center flex-shrink-0 mt-0.5">
            <Lightbulb className="w-3.5 h-3.5 text-[#666666]" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-[#37352f] leading-snug">
              {thread.theme}
            </h3>
            <div className="flex items-center gap-2 mt-0.5">
              {knowledgeInfo && (
                <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${knowledgeInfo.color}`}>
                  {knowledgeInfo.label}
                </span>
              )}
              {thread.features.length > 0 && (
                <span className="text-[10px] text-text-placeholder">
                  {thread.features.length} feature{thread.features.length !== 1 ? 's' : ''}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Questions — cap at 2 */}
        {thread.questions.length > 0 && (
          <div className="space-y-1.5 mb-3">
            <h4 className="text-[10px] font-semibold text-[#666666] uppercase tracking-wide flex items-center gap-1">
              <HelpCircle className="w-3 h-3" />
              Questions
            </h4>
            {thread.questions.slice(0, 2).map((q, i) => (
              <p key={i} className="text-xs text-[#37352f] pl-4 leading-relaxed">
                {q}
              </p>
            ))}
          </div>
        )}

        {/* Speaker hints */}
        {thread.speaker_hints.length > 0 && (
          <div className="flex items-center gap-1.5 text-[10px] text-text-placeholder">
            <Users className="w-3 h-3" />
            <span>
              Ask: {thread.speaker_hints.map((s) => s.name).join(', ')}
            </span>
          </div>
        )}

        {/* Feature tags */}
        {thread.features.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {thread.features.slice(0, 3).map((f, i) => (
              <span
                key={i}
                className="text-[10px] px-2 py-0.5 rounded-full border border-border text-[#666666]"
              >
                {f}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
