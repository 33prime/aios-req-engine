'use client'

import { useState } from 'react'
import { BookOpen, ChevronDown, Quote } from 'lucide-react'
import type { NeedNarrative } from '@/types/workspace'

interface NeedNarrativeSectionProps {
  narrative: NeedNarrative | null | undefined
}

export function NeedNarrativeSection({ narrative }: NeedNarrativeSectionProps) {
  const [showAnchors, setShowAnchors] = useState(false)

  if (!narrative) {
    return (
      <div className="bg-gradient-to-r from-[#F4F4F4] to-[#FAFAFA] rounded-2xl border border-border p-6 text-center">
        <BookOpen className="w-5 h-5 text-text-placeholder mx-auto mb-2" />
        <p className="text-[13px] text-text-placeholder">
          Process signals to unlock the project narrative
        </p>
      </div>
    )
  }

  const anchors = narrative.anchors || []

  return (
    <div className="bg-gradient-to-br from-white to-[#F8FBF9] rounded-2xl border border-border shadow-sm overflow-hidden">
      <div className="p-6">
        {/* Header */}
        <div className="flex items-center gap-2 mb-4">
          <BookOpen className="w-5 h-5 text-[#25785A]" />
          <h3 className="text-[15px] font-semibold text-text-body">What Drove the Need</h3>
        </div>

        {/* Narrative text */}
        <p className="text-[14px] text-[#444444] leading-relaxed">
          {narrative.text}
        </p>

        {/* Provenance anchors */}
        {anchors.length > 0 && (
          <div className="mt-4">
            <button
              onClick={() => setShowAnchors(!showAnchors)}
              className="flex items-center gap-1.5 text-[11px] font-medium text-text-placeholder hover:text-[#25785A] transition-colors"
            >
              <ChevronDown className={`w-3 h-3 transition-transform ${showAnchors ? 'rotate-180' : ''}`} />
              {anchors.length} source{anchors.length !== 1 ? 's' : ''} grounding this narrative
            </button>

            {showAnchors && (
              <div className="mt-3 space-y-2">
                {anchors.map((anchor, i) => (
                  <div key={i} className="flex items-start gap-2 pl-3 border-l-2 border-[#25785A]/20">
                    <Quote className="w-3 h-3 text-[#25785A]/40 shrink-0 mt-0.5" />
                    <div className="flex-1 min-w-0">
                      <p className="text-[12px] text-[#666666] italic leading-relaxed">
                        &ldquo;{anchor.excerpt}&rdquo;
                      </p>
                      {anchor.rationale && (
                        <p className="text-[10px] text-text-placeholder mt-0.5">{anchor.rationale}</p>
                      )}
                    </div>
                    <span className="text-[10px] text-text-placeholder bg-[#F0F0F0] px-1.5 py-0.5 rounded shrink-0">
                      {anchor.source_type}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
