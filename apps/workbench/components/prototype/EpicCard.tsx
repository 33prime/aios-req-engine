'use client'

import { MessageCircle, User } from 'lucide-react'
import type { Epic } from '@/types/epic-overlay'

interface EpicCardProps {
  epic: Epic
  isActive?: boolean
}

export default function EpicCard({ epic, isActive = false }: EpicCardProps) {
  return (
    <div
      className={`rounded-xl border transition-colors ${
        isActive ? 'border-brand-primary bg-[#F0FAF4]' : 'border-border bg-white'
      }`}
    >
      <div className="px-4 py-3">
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-medium text-brand-primary bg-brand-primary-light px-2 py-0.5 rounded-full">
                Epic {epic.epic_index}
              </span>
              {epic.persona_names.length > 0 && (
                <span className="text-[10px] text-text-placeholder flex items-center gap-0.5">
                  <User className="w-3 h-3" />
                  {epic.persona_names.slice(0, 2).join(', ')}
                </span>
              )}
            </div>
            <h3 className="text-sm font-semibold text-[#37352f] leading-snug">
              {epic.title}
            </h3>
          </div>
        </div>

        {/* Narrative — 2-3 sentences, text-[13px] */}
        <p className="text-[13px] text-[#666666] leading-relaxed mt-2">
          {epic.narrative}
        </p>

        {/* Feature chips — small context, not the focus */}
        {epic.features.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2.5">
            {epic.features.slice(0, 4).map((f) => (
              <span
                key={f.feature_id}
                className="text-[10px] px-2 py-0.5 rounded-full border border-border text-[#666666] bg-[#F8F8F8]"
              >
                {f.name}
              </span>
            ))}
            {epic.features.length > 4 && (
              <span className="text-[10px] text-text-placeholder">
                +{epic.features.length - 4}
              </span>
            )}
          </div>
        )}

        {/* 1-2 key questions */}
        {epic.open_questions.length > 0 && (
          <div className="mt-3 pt-2.5 border-t border-border space-y-1.5">
            <h4 className="text-[11px] font-semibold text-[#666666] uppercase tracking-wide flex items-center gap-1">
              <MessageCircle className="w-3 h-3" />
              Questions
            </h4>
            {epic.open_questions.slice(0, 2).map((q, i) => (
              <p key={i} className="text-[12px] text-[#37352f] pl-4 leading-relaxed">
                {q}
              </p>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
