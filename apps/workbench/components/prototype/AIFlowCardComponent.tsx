'use client'

import { Bot, ShieldCheck, ArrowRight } from 'lucide-react'
import type { AIFlowCard } from '@/types/epic-overlay'

interface AIFlowCardComponentProps {
  card: AIFlowCard
  isActive?: boolean
}

export default function AIFlowCardComponent({ card, isActive = false }: AIFlowCardComponentProps) {
  return (
    <div
      className={`rounded-xl border transition-colors ${
        isActive ? 'border-brand-primary bg-[#F0FAF4]' : 'border-border bg-white'
      }`}
    >
      <div className="px-4 py-3">
        {/* Header */}
        <div className="flex items-center gap-2 mb-2">
          <div className="w-6 h-6 rounded-lg bg-[#E8EDF2] flex items-center justify-center">
            <Bot className="w-3.5 h-3.5 text-[#0A1E2F]" />
          </div>
          <h3 className="text-sm font-semibold text-[#37352f]">{card.title}</h3>
        </div>

        {/* Narrative */}
        {card.narrative && (
          <p className="text-[13px] text-[#666666] leading-relaxed mb-3">
            {card.narrative}
          </p>
        )}

        {/* 4-section layout — tighter */}
        <div className="grid grid-cols-2 gap-2">
          {/* Data In */}
          <div className="rounded-lg bg-[#F8F8F8] p-2">
            <h4 className="text-[10px] font-semibold text-[#666666] uppercase tracking-wide mb-0.5">
              Data In
            </h4>
            <ul className="space-y-0">
              {card.data_in.slice(0, 3).map((d, i) => (
                <li key={i} className="text-[11px] text-[#37352f] truncate">{d}</li>
              ))}
            </ul>
          </div>

          {/* What AI Does */}
          <div className="rounded-lg bg-[#E8EDF2] p-2">
            <h4 className="text-[10px] font-semibold text-[#0A1E2F] uppercase tracking-wide mb-0.5 flex items-center gap-1">
              <ArrowRight className="w-3 h-3" />
              AI Does
            </h4>
            <ul className="space-y-0">
              {card.behaviors.slice(0, 3).map((b, i) => (
                <li key={i} className="text-[11px] text-[#37352f] truncate">{b}</li>
              ))}
            </ul>
          </div>

          {/* Guardrails */}
          <div className="rounded-lg bg-[#F8F8F8] p-2">
            <h4 className="text-[10px] font-semibold text-[#666666] uppercase tracking-wide mb-0.5 flex items-center gap-1">
              <ShieldCheck className="w-3 h-3" />
              Guardrails
            </h4>
            <ul className="space-y-0">
              {card.guardrails.slice(0, 3).map((g, i) => (
                <li key={i} className="text-[11px] text-[#37352f] truncate">{g}</li>
              ))}
              {card.guardrails.length === 0 && (
                <li className="text-[11px] text-text-placeholder italic">None defined</li>
              )}
            </ul>
          </div>

          {/* Output */}
          <div className="rounded-lg bg-[#F0FAF4] p-2">
            <h4 className="text-[10px] font-semibold text-brand-primary uppercase tracking-wide mb-0.5">
              Output
            </h4>
            <p className="text-[11px] text-[#37352f]">
              {card.output || 'AI-generated result'}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
