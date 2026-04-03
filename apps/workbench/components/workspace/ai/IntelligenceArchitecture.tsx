'use client'

/**
 * IntelligenceArchitecture — 4-quadrant view of what makes the product intelligent.
 *
 * Collapsed: 2x2 grid with icon + title + count + summary pills
 * Expanded: full-width split pane — inventory (left) + detail/demo (right)
 *
 * Quadrants: Knowledge Systems | Scoring Models | Decision Logic | AI Capabilities
 * Matches playground-intelligence-layer-v3.html design spec.
 *
 * v2: outcome links on items, discuss buttons on open questions, review tracking
 */

import { useState } from 'react'
import {
  BookOpen, Gauge, GitBranch, Sparkles,
  ChevronDown, CornerDownRight, MessageCircle,
} from 'lucide-react'
import type { IntelArchitecture, QuadrantData, ArchitectureItem, ArchitectureOpenQuestion } from '@/types/workspace'

// ── Quadrant definitions ──

type QuadrantKey = 'knowledge_systems' | 'scoring_models' | 'decision_logic' | 'ai_capabilities'

const QUADRANTS: Array<{
  key: QuadrantKey
  title: string
  icon: React.ElementType
  label: string
  demoLabel: string
  deliverLabel: string
  iconCls: string
}> = [
  {
    key: 'knowledge_systems',
    title: 'Knowledge Systems',
    icon: BookOpen,
    label: 'What the product needs to know',
    demoLabel: 'Explore',
    deliverLabel: 'This knowledge delivers',
    iconCls: 'bg-[rgba(10,30,47,0.06)] text-[#0A1E2F]',
  },
  {
    key: 'scoring_models',
    title: 'Scoring Models',
    icon: Gauge,
    label: 'What the product measures',
    demoLabel: 'Watch it score',
    deliverLabel: 'This score drives',
    iconCls: 'bg-[rgba(4,65,89,0.08)] text-[#044159]',
  },
  {
    key: 'decision_logic',
    title: 'Decision Logic',
    icon: GitBranch,
    label: 'Decisions the product makes',
    demoLabel: 'Trace a scenario',
    deliverLabel: 'This decision enables',
    iconCls: 'bg-[rgba(4,65,89,0.06)] text-[#044159]',
  },
  {
    key: 'ai_capabilities',
    title: 'AI Capabilities',
    icon: Sparkles,
    label: 'Where AI adds value',
    demoLabel: 'See it work',
    deliverLabel: 'This capability enables',
    iconCls: 'bg-[rgba(63,175,122,0.08)] text-[#3FAF7A]',
  },
]

// ── Props ──

// Selected can be a defined item or an open question
type SelectedItem =
  | { kind: 'item'; idx: number }
  | { kind: 'question'; idx: number }

interface Props {
  architecture: IntelArchitecture
  reviewedItems?: Set<string>
  onItemReviewed?: (key: string) => void
  onDiscuss?: (quadrant: string, question: string, context: string) => void
}

export function IntelligenceArchitecture({ architecture, reviewedItems, onItemReviewed, onDiscuss }: Props) {
  const [expandedKey, setExpandedKey] = useState<QuadrantKey | null>(null)
  const [selected, setSelected] = useState<SelectedItem>({ kind: 'item', idx: 0 })

  const toggleQuadrant = (key: QuadrantKey) => {
    if (expandedKey === key) {
      setExpandedKey(null)
    } else {
      setExpandedKey(key)
      setSelected({ kind: 'item', idx: 0 })
    }
  }

  const handleSelectItem = (idx: number, item: ArchitectureItem, quadrantKey: string) => {
    setSelected({ kind: 'item', idx })
    const reviewKey = `${quadrantKey}:${item.name}`
    if (onItemReviewed && !reviewedItems?.has(reviewKey)) {
      onItemReviewed(reviewKey)
    }
  }

  const handleSelectQuestion = (idx: number) => {
    setSelected({ kind: 'question', idx })
  }

  const isReviewed = (quadrantKey: string, itemName: string) =>
    reviewedItems?.has(`${quadrantKey}:${itemName}`) ?? false

  return (
    <div className="grid grid-cols-2 gap-2">
      {QUADRANTS.map(q => {
        const data: QuadrantData = architecture[q.key] || { items: [], open_questions: [] }
        const isExpanded = expandedKey === q.key
        const totalCount = data.items.length
        const Icon = q.icon

        // Resolve selected item or question for the right pane
        const selectedItem: ArchitectureItem | null =
          isExpanded && selected.kind === 'item' ? (data.items[selected.idx] || null) : null
        const selectedQuestion: ArchitectureOpenQuestion | null =
          isExpanded && selected.kind === 'question' ? (data.open_questions[selected.idx] || null) : null

        return (
          <div
            key={q.key}
            className={`bg-white border border-[rgba(10,30,47,0.08)] rounded-xl overflow-hidden transition-all duration-200 ${
              isExpanded
                ? 'col-span-2 border-[rgba(10,30,47,0.14)] shadow-[0_2px_12px_rgba(0,0,0,0.06)]'
                : 'hover:border-[rgba(10,30,47,0.14)] hover:shadow-[0_2px_12px_rgba(0,0,0,0.06)]'
            }`}
          >
            {/* ── Header (always visible) ── */}
            <div
              className="flex items-center gap-2 px-3.5 py-3 cursor-pointer"
              onClick={() => toggleQuadrant(q.key)}
            >
              <div className={`w-7 h-7 rounded-md flex items-center justify-center ${q.iconCls}`}>
                <Icon size={14} />
              </div>
              <span className="text-[12px] font-bold text-[#0A1E2F] flex-1">{q.title}</span>
              <span className="text-[10px] font-bold text-[#A0AEC0] bg-[rgba(0,0,0,0.02)] px-1.5 py-0.5 rounded-md">
                {totalCount}
              </span>
              <ChevronDown
                size={12}
                className={`text-[#A0AEC0] transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
              />
            </div>

            {/* ── Summary pills (collapsed only) ── */}
            {!isExpanded && data.items.length > 0 && (
              <div className="px-3.5 pb-3 flex flex-wrap gap-1">
                {data.items.map((item, i) => (
                  <span
                    key={i}
                    className="px-2 py-0.5 rounded text-[9px] font-medium text-[#4A5568]"
                    style={{ background: 'rgba(0,0,0,0.02)', border: '1px solid rgba(10,30,47,0.08)' }}
                  >
                    {item.name}
                  </span>
                ))}
              </div>
            )}

            {/* ── Expanded: Split Pane ── */}
            {isExpanded && (
              <div
                className="border-t border-[rgba(10,30,47,0.08)]"
                style={{ display: 'grid', gridTemplateColumns: '280px 1fr', minHeight: 260 }}
              >
                {/* Left: Inventory */}
                <div className="border-r border-[rgba(10,30,47,0.08)] p-3.5">
                  {/* Defined items */}
                  <p className="text-[8px] font-bold uppercase tracking-[0.06em] text-[#A0AEC0] mb-1.5 pl-0.5">
                    {q.label}
                  </p>
                  {data.items.map((item, i) => {
                    const reviewed = isReviewed(q.key, item.name)
                    const isSel = selected.kind === 'item' && selected.idx === i

                    return (
                      <div
                        key={i}
                        className={`flex items-start gap-2 px-2 py-1.5 rounded-md cursor-pointer transition-colors mb-0.5 ${
                          isSel ? 'bg-[rgba(63,175,122,0.08)]' : 'hover:bg-[rgba(0,0,0,0.02)]'
                        }`}
                        onClick={() => handleSelectItem(i, item, q.key)}
                      >
                        <div
                          className="w-[7px] h-[7px] rounded-full mt-[4px] flex-shrink-0"
                          style={{
                            background: (item.status === 'defined' || reviewed) ? '#3FAF7A' : 'transparent',
                            border: (item.status === 'defined' || reviewed) ? '1.5px solid #3FAF7A' : '1.5px solid #A0AEC0',
                          }}
                        />
                        <div className="flex-1 min-w-0">
                          <p className="text-[10px] font-semibold text-[#2D3748] mb-px">{item.name}</p>
                          <p className="text-[9px] text-[#A0AEC0] leading-snug line-clamp-2">{item.description}</p>
                          {/* Outcome link arrow */}
                          {item.powers && (
                            <div className="flex items-center gap-1 mt-1">
                              <CornerDownRight size={9} className="text-[#A0AEC0] flex-shrink-0" />
                              <span className="text-[8px] font-semibold text-[#044159]">
                                {item.outcome_title || `Powers ${item.powers}`}
                              </span>
                            </div>
                          )}
                        </div>
                        {item.status === 'defined' && (
                          <span className="text-[7px] font-bold uppercase px-1 py-0.5 rounded bg-[rgba(63,175,122,0.06)] text-[#1B6B3A] flex-shrink-0 mt-0.5">
                            Defined
                          </span>
                        )}
                      </div>
                    )
                  })}

                  {/* Open Questions */}
                  {data.open_questions.length > 0 && (
                    <>
                      <p className="text-[8px] font-bold uppercase tracking-[0.06em] text-[#A0AEC0] mb-1.5 mt-3.5 pl-0.5">
                        Open questions
                      </p>
                      {data.open_questions.map((oq, i) => {
                        const isSel = selected.kind === 'question' && selected.idx === i
                        return (
                          <div
                            key={i}
                            className={`flex items-start gap-2 px-2 py-1.5 rounded-md cursor-pointer transition-colors mb-0.5 ${
                              isSel ? 'bg-[rgba(4,65,89,0.06)]' : 'hover:bg-[rgba(0,0,0,0.02)]'
                            }`}
                            onClick={() => handleSelectQuestion(i)}
                          >
                            <div
                              className="w-[7px] h-[7px] rounded-full mt-[4px] flex-shrink-0"
                              style={{ border: '1.5px dashed #044159', background: 'none' }}
                            />
                            <div className="flex-1 min-w-0">
                              <p className="text-[10px] font-semibold text-[#2D3748]">{oq.question}</p>
                              <p className="text-[9px] text-[#A0AEC0] leading-snug">{oq.context}</p>
                            </div>
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                onDiscuss?.(q.title, oq.question, oq.context)
                              }}
                              className="text-[7px] font-bold uppercase px-1.5 py-0.5 rounded text-[#044159] bg-[rgba(4,65,89,0.06)] border border-[rgba(4,65,89,0.08)] flex-shrink-0 mt-0.5 cursor-pointer hover:bg-[rgba(4,65,89,0.12)] transition-colors"
                            >
                              Discuss
                            </button>
                          </div>
                        )
                      })}
                    </>
                  )}
                </div>

                {/* Right: Detail + Demo */}
                <div className="p-3.5">
                  {selectedItem ? (
                    <>
                      <p className="text-[13px] font-bold text-[#0A1E2F] mb-1">{selectedItem.name}</p>
                      <p className="text-[11px] text-[#718096] leading-relaxed mb-3">
                        {selectedItem.description}
                      </p>

                      {/* Demo block */}
                      <div
                        className="rounded-lg overflow-hidden"
                        style={{ background: 'rgba(0,0,0,0.02)', border: '1px solid rgba(10,30,47,0.08)' }}
                      >
                        <div
                          className="flex items-center gap-1.5 px-2.5 py-1.5"
                          style={{ borderBottom: '1px solid rgba(10,30,47,0.08)' }}
                        >
                          <div className="w-[5px] h-[5px] rounded-full bg-[#3FAF7A]" />
                          <span className="text-[9px] font-bold uppercase tracking-wider text-[#1B6B3A]">
                            {q.demoLabel}
                          </span>
                        </div>
                        <div className="p-3">
                          <p className="text-[10px] text-[#4A5568] leading-relaxed">
                            {selectedItem.description}
                          </p>
                        </div>
                      </div>

                      {/* "This delivers" callout */}
                      {selectedItem.powers && (
                        <div
                          className="mt-3 rounded-md px-3 py-2.5"
                          style={{ background: 'rgba(4,65,89,0.03)', borderLeft: '2px solid #044159' }}
                        >
                          <p className="text-[8px] font-bold uppercase tracking-[0.04em] text-[#044159] mb-1">
                            {q.deliverLabel}
                          </p>
                          <p className="text-[10px] text-[#4A5568] leading-relaxed">
                            {selectedItem.powers}
                          </p>
                        </div>
                      )}
                    </>
                  ) : selectedQuestion ? (
                    /* Open question detail pane */
                    <>
                      <div className="flex items-start gap-2 mb-3">
                        <MessageCircle size={16} className="text-[#044159] mt-0.5 flex-shrink-0" />
                        <div>
                          <p className="text-[13px] font-bold text-[#0A1E2F] mb-1">{selectedQuestion.question}</p>
                          <p className="text-[11px] text-[#718096] leading-relaxed">{selectedQuestion.context}</p>
                        </div>
                      </div>

                      {/* Discuss CTA box */}
                      <div
                        className="flex items-start gap-2 p-3 rounded-lg"
                        style={{ background: 'rgba(4,65,89,0.03)', border: '1px solid rgba(4,65,89,0.08)' }}
                      >
                        <MessageCircle size={12} className="text-[#044159] mt-0.5 flex-shrink-0" />
                        <div className="flex-1">
                          <p className="text-[10px] text-[#4A5568] leading-relaxed mb-2">
                            This is an open question that could shape the intelligence design. Discuss it to refine your thinking.
                          </p>
                          <button
                            onClick={() => onDiscuss?.(q.title, selectedQuestion.question, selectedQuestion.context)}
                            className="px-3 py-1.5 rounded-md text-[10px] font-semibold text-white bg-[#044159] hover:bg-[#0A1E2F] transition-colors"
                          >
                            Discuss this question
                          </button>
                        </div>
                      </div>
                    </>
                  ) : (
                    <p className="text-[11px] text-[#A0AEC0]">Select an item to explore</p>
                  )}
                </div>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
