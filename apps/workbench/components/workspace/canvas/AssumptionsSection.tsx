'use client'

import { CircleDot, HelpCircle } from 'lucide-react'

interface AssumptionsSectionProps {
  assumptions: string[]
  openQuestions: string[]
}

export function AssumptionsSection({ assumptions, openQuestions }: AssumptionsSectionProps) {
  const hasContent = assumptions.length > 0 || openQuestions.length > 0

  if (!hasContent) return null

  return (
    <section>
      <div className="flex items-center gap-2 mb-4">
        <CircleDot className="w-4 h-4 text-brand-primary" />
        <h2 className="text-[16px] font-semibold text-text-body">Assumptions & Open Questions</h2>
        <span className="text-[12px] text-text-placeholder">
          ({assumptions.length + openQuestions.length} items)
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Assumptions column */}
        {assumptions.length > 0 && (
          <div className="bg-white rounded-2xl shadow-md border border-border overflow-hidden">
            <div className="px-5 py-3 bg-[#F0F0F0] border-b border-border">
              <div className="flex items-center gap-1.5">
                <CircleDot className="w-3.5 h-3.5 text-[#666666]" />
                <span className="text-[11px] font-semibold text-[#666666] uppercase tracking-wide">
                  Assumptions
                </span>
                <span className="text-[11px] text-text-placeholder">({assumptions.length})</span>
              </div>
            </div>
            <div className="px-5 py-4">
              <ul className="space-y-2.5">
                {assumptions.map((assumption, idx) => (
                  <li key={idx} className="flex items-start gap-2.5">
                    <span className="mt-1.5 w-2 h-2 rounded-full bg-border shrink-0" />
                    <p className="text-[13px] text-[#666666] leading-relaxed">{assumption}</p>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {/* Open Questions column */}
        {openQuestions.length > 0 && (
          <div className="bg-white rounded-2xl shadow-md border border-border overflow-hidden">
            <div className="px-5 py-3 bg-[#E8F5E9] border-b border-border">
              <div className="flex items-center gap-1.5">
                <HelpCircle className="w-3.5 h-3.5 text-[#25785A]" />
                <span className="text-[11px] font-semibold text-[#25785A] uppercase tracking-wide">
                  Open Questions
                </span>
                <span className="text-[11px] text-[#25785A]/70">({openQuestions.length})</span>
              </div>
            </div>
            <div className="px-5 py-4">
              <ul className="space-y-2.5">
                {openQuestions.map((question, idx) => (
                  <li key={idx} className="flex items-start gap-2.5">
                    <HelpCircle className="w-3.5 h-3.5 text-brand-primary mt-0.5 shrink-0" />
                    <p className="text-[13px] text-[#666666] leading-relaxed">{question}</p>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>
    </section>
  )
}
