/**
 * QuickActionCards — Interactive card types rendered inline in chat messages.
 *
 * The assistant calls `suggest_actions` with structured card data.
 * Each card type has its own component. Button clicks send commands
 * back to the LLM via onAction → onSendMessage.
 */

'use client'

import { useState } from 'react'
import { CheckCircle2, Mail, Calendar, Quote, Check } from 'lucide-react'
import { URGENCY_COLORS } from '@/lib/action-constants'

// =============================================================================
// Shared Style Constants
// =============================================================================

const CARD_BASE = 'border border-border rounded-2xl bg-[#F7F8FA] px-4 py-4'
const CARD_RESOLVED = 'border border-brand-primary/40 bg-[#E8F5E9]/30 rounded-2xl px-4 py-3.5 flex items-center gap-2'
const CARD_HEADER = 'text-[10px] text-[#999] uppercase tracking-wider font-semibold mb-2.5'
const BTN_PRIMARY_OUTLINE = 'text-[12px] font-medium px-4 py-1.5 rounded-full border border-brand-primary text-brand-primary hover:bg-[#E8F5E9] transition-colors'
const BTN_PRIMARY_FILLED = 'text-[12px] font-medium px-4 py-1.5 rounded-full bg-brand-primary text-white hover:bg-[#25785A] transition-colors'
const BTN_SECONDARY = 'text-[12px] font-medium px-4 py-1.5 rounded-full border border-[#D5D5D5] text-text-secondary hover:bg-surface-subtle transition-colors'
const BTN_GHOST = 'text-[12px] font-medium px-3 py-1.5 text-[#999] hover:text-text-secondary transition-colors'
const BTN_CONFIRMED = 'text-[12px] font-medium px-4 py-1.5 rounded-full bg-[#E8F5E9] text-[#25785A] pointer-events-none flex items-center gap-1'

// =============================================================================
// Types
// =============================================================================

interface CardBase {
  card_type: string
  id: string
  data: any
}

interface GapCloserData {
  label: string
  severity: 'critical' | 'high' | 'normal' | 'low'
  resolution: string
  actions: Array<{ label: string; command: string; variant?: 'primary' | 'ghost' }>
  entity_type?: string
  gap_source?: string
}

interface ActionButtonsData {
  buttons: Array<{ label: string; command: string; variant?: 'primary' | 'outline' | 'ghost' }>
}

interface ChoiceData {
  title?: string
  question: string
  options: Array<{ label: string; command: string }>
}

interface ProposalData {
  title: string
  body?: string
  tags?: string[]
  bullets?: string[]
  actions: Array<{ label: string; command: string; variant?: 'primary' | 'outline' | 'ghost' }>
}

interface EmailDraftData {
  to: string
  subject: string
  body: string
}

interface MeetingData {
  topic: string
  attendees: string[]
  agenda: string[]
}

interface SmartSummaryItem {
  label: string
  type: 'feature' | 'constraint' | 'task' | 'question'
  checked?: boolean
}

interface SmartSummaryData {
  items: SmartSummaryItem[]
}

interface EvidenceItem {
  quote: string
  source: string
  section?: string
}

interface EvidenceData {
  items: EvidenceItem[]
}

interface DiscoveryProbeData {
  probe_id: string
  category: string // "organizational_impact" etc.
  context: string
  question: string
  why: string
  priority: number
}

const NORTH_STAR_CATEGORY_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  organizational_impact: { bg: '#DBEAFE', text: '#1D4ED8', label: 'Org Impact' },
  human_behavioral_goal: { bg: '#E8F5E9', text: '#25785A', label: 'Behavior' },
  success_metrics: { bg: '#FEF3C7', text: '#B45309', label: 'Metrics' },
  cultural_constraints: { bg: '#F3E8FF', text: '#7C3AED', label: 'Culture' },
}

// =============================================================================
// Main Renderer
// =============================================================================

interface QuickActionCardsProps {
  cards: CardBase[]
  onAction: (command: string) => void
}

export function QuickActionCards({ cards, onAction }: QuickActionCardsProps) {
  if (!cards || cards.length === 0) return null

  return (
    <div className="mt-3 space-y-3">
      {cards.map((card) => {
        switch (card.card_type) {
          case 'gap_closer':
            return <GapCloserCard key={card.id} data={card.data} onAction={onAction} />
          case 'action_buttons':
            return <ActionButtonsCard key={card.id} data={card.data} onAction={onAction} />
          case 'choice':
            return <ChoiceCard key={card.id} data={card.data} onAction={onAction} />
          case 'proposal':
            return <ProposalCard key={card.id} data={card.data} onAction={onAction} />
          case 'email_draft':
            return <EmailDraftCard key={card.id} data={card.data} onAction={onAction} />
          case 'meeting':
            return <MeetingCard key={card.id} data={card.data} onAction={onAction} />
          case 'smart_summary':
            return <SmartSummaryCard key={card.id} data={card.data} onAction={onAction} />
          case 'evidence':
            return <EvidenceCard key={card.id} data={card.data} onAction={onAction} />
          case 'discovery_probe':
            return <DiscoveryProbeCard key={card.id} data={card.data} onAction={onAction} />
          default:
            return null
        }
      })}
    </div>
  )
}

// =============================================================================
// Gap Closer
// =============================================================================

function GapCloserCard({ data, onAction }: { data: GapCloserData; onAction: (cmd: string) => void }) {
  const [resolved, setResolved] = useState(false)
  const severityColor = URGENCY_COLORS[data.severity] || URGENCY_COLORS.normal

  if (resolved) {
    return (
      <div className={CARD_RESOLVED}>
        <CheckCircle2 className="h-3.5 w-3.5 text-brand-primary" />
        <span className="text-[12px] text-[#25785A] font-medium">Resolved</span>
      </div>
    )
  }

  return (
    <div className={CARD_BASE}>
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-[13px] font-medium text-[#333] flex-1 min-w-0">{data.label}</span>
        <span
          className="text-[10px] rounded-full px-2 py-0.5 font-medium shrink-0"
          style={{ backgroundColor: `${severityColor}18`, color: severityColor }}
        >
          {data.severity}
        </span>
      </div>
      {data.resolution && (
        <p className="text-[11px] text-text-muted border-l-2 border-border pl-2 mt-1.5">{data.resolution}</p>
      )}
      <div className="flex items-center gap-2 mt-3">
        {data.actions?.map((action, i) => (
          <button
            key={i}
            onClick={() => {
              setResolved(true)
              onAction(action.command)
            }}
            className={action.variant === 'ghost' ? BTN_SECONDARY : BTN_PRIMARY_OUTLINE}
          >
            {action.label}
          </button>
        ))}
      </div>
    </div>
  )
}

// =============================================================================
// Action Buttons (inline, no card wrapper)
// =============================================================================

function ActionButtonsCard({ data, onAction }: { data: ActionButtonsData; onAction: (cmd: string) => void }) {
  const [confirmed, setConfirmed] = useState<string | null>(null)

  return (
    <div className="flex items-center gap-2 flex-wrap">
      {data.buttons?.map((btn, i) => {
        const isConfirmed = confirmed === btn.label
        if (isConfirmed) {
          return (
            <span key={i} className={BTN_CONFIRMED}>
              <Check className="h-3 w-3" />
              {btn.label}
            </span>
          )
        }
        const variant = btn.variant || 'primary'
        const cls =
          variant === 'ghost'
            ? BTN_GHOST
            : BTN_PRIMARY_OUTLINE
        return (
          <button
            key={i}
            onClick={() => {
              setConfirmed(btn.label)
              onAction(btn.command)
            }}
            className={cls}
          >
            {btn.label}
          </button>
        )
      })}
    </div>
  )
}

// =============================================================================
// Choice
// =============================================================================

function ChoiceCard({ data, onAction }: { data: ChoiceData; onAction: (cmd: string) => void }) {
  const [selected, setSelected] = useState<string | null>(null)

  return (
    <div className={CARD_BASE}>
      {data.title && <p className={CARD_HEADER}>{data.title}</p>}
      <p className="text-[13px] font-medium text-[#333] mb-3">{data.question}</p>
      <div className="flex items-center gap-2 flex-wrap">
        {data.options?.map((opt, i) => {
          const isSelected = selected === opt.label
          const isOther = selected !== null && !isSelected
          return (
            <button
              key={i}
              onClick={() => {
                if (selected) return
                setSelected(opt.label)
                onAction(opt.command)
              }}
              className={`rounded-full px-4 py-1.5 text-[12px] font-medium border transition-all ${
                isSelected
                  ? 'bg-brand-primary text-white border-brand-primary'
                  : isOther
                    ? 'border-[#D5D5D5] text-[#999] opacity-30 pointer-events-none'
                    : 'border-[#D5D5D5] text-text-secondary hover:border-brand-primary hover:text-brand-primary'
              }`}
            >
              {opt.label}
            </button>
          )
        })}
      </div>
      {selected && (
        <p className="text-[11px] text-brand-primary mt-1.5 animate-in fade-in duration-300">
          <Check className="h-3 w-3 inline mr-0.5 -mt-0.5" />
          Saved
        </p>
      )}
    </div>
  )
}

// =============================================================================
// Proposal
// =============================================================================

function ProposalCard({ data, onAction }: { data: ProposalData; onAction: (cmd: string) => void }) {
  const [approved, setApproved] = useState(false)

  if (approved) {
    return (
      <div className={CARD_RESOLVED}>
        <CheckCircle2 className="h-3.5 w-3.5 text-brand-primary" />
        <span className="text-[12px] text-[#25785A] font-medium">Added to BRD</span>
      </div>
    )
  }

  return (
    <div className={CARD_BASE}>
      <p className={CARD_HEADER}>{data.title}</p>
      {data.tags && data.tags.length > 0 && (
        <div className="flex items-center gap-1.5 flex-wrap mb-2.5">
          {data.tags.map((tag, i) => (
            <span key={i} className="text-[10px] rounded-full px-2 py-0.5 bg-[#E8F5E9] text-[#25785A]">
              {tag}
            </span>
          ))}
        </div>
      )}
      {data.bullets && data.bullets.length > 0 && (
        <ul className="mt-1.5 space-y-1">
          {data.bullets.map((b, i) => (
            <li key={i} className="text-[12px] text-text-secondary flex items-start gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-brand-primary mt-1.5 shrink-0" />
              {b}
            </li>
          ))}
        </ul>
      )}
      {data.body && !data.bullets && (
        <p className="text-[12px] text-text-secondary mt-1.5">{data.body}</p>
      )}
      <div className="border-t border-border mt-3 pt-3 flex items-center gap-2">
        {data.actions?.map((action, i) => {
          const variant = action.variant || 'primary'
          const cls =
            variant === 'ghost'
              ? BTN_GHOST
              : variant === 'outline'
                ? BTN_SECONDARY
                : BTN_PRIMARY_FILLED
          return (
            <button
              key={i}
              onClick={() => {
                if (variant === 'primary') setApproved(true)
                onAction(action.command)
              }}
              className={cls}
            >
              {action.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}

// =============================================================================
// Email Draft
// =============================================================================

function EmailDraftCard({ data, onAction }: { data: EmailDraftData; onAction: (cmd: string) => void }) {
  const [sent, setSent] = useState(false)

  if (sent) {
    return (
      <div className={CARD_RESOLVED}>
        <Mail className="h-3.5 w-3.5 text-brand-primary" />
        <span className="text-[12px] text-[#25785A] font-medium">Draft copied</span>
      </div>
    )
  }

  return (
    <div className="border border-border rounded-2xl bg-[#F7F8FA] overflow-hidden">
      <div className="px-4 py-3 bg-[#F0F1F3] border-b border-border flex items-center gap-2">
        <Mail className="h-3 w-3 text-[#999]" />
        <span className="text-[10px] text-[#999] uppercase tracking-wider font-semibold">Email Draft</span>
      </div>
      <div className="px-4 py-3 space-y-1">
        <div className="flex items-baseline gap-2">
          <span className="text-[10px] text-[#999] uppercase tracking-wider w-10">To</span>
          <span className="text-[12px] text-[#333]">{data.to}</span>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-[10px] text-[#999] uppercase tracking-wider w-10">Subj</span>
          <span className="text-[12px] text-[#333] font-medium">{data.subject}</span>
        </div>
        <div className="border-t border-border mt-1.5 pt-1.5">
          <p className="text-[12px] text-text-secondary line-clamp-4 whitespace-pre-line">{data.body}</p>
        </div>
      </div>
      <div className="border-t border-border px-4 py-3 flex items-center gap-2">
        <button
          onClick={() => {
            setSent(true)
            onAction(`Send email draft to ${data.to} about "${data.subject}"`)
          }}
          className={BTN_PRIMARY_FILLED}
        >
          Send Draft
        </button>
        <button
          onClick={() => onAction(`Edit email draft to ${data.to} about "${data.subject}"`)}
          className={BTN_SECONDARY}
        >
          Edit
        </button>
      </div>
    </div>
  )
}

// =============================================================================
// Meeting
// =============================================================================

function MeetingCard({ data, onAction }: { data: MeetingData; onAction: (cmd: string) => void }) {
  const [booked, setBooked] = useState(false)

  if (booked) {
    return (
      <div className={CARD_RESOLVED}>
        <Calendar className="h-3.5 w-3.5 text-brand-primary" />
        <span className="text-[12px] text-[#25785A] font-medium">Meeting prep saved</span>
      </div>
    )
  }

  return (
    <div className="border border-border rounded-2xl bg-[#F7F8FA] overflow-hidden">
      <div className="px-4 py-3 bg-[#F0F1F3] border-b border-border flex items-center gap-2">
        <Calendar className="h-3 w-3 text-[#999]" />
        <span className="text-[10px] text-[#999] uppercase tracking-wider font-semibold">Meeting</span>
      </div>
      <div className="px-4 py-3 space-y-1.5">
        <p className="text-[13px] font-medium text-[#333]">{data.topic}</p>
        {data.attendees?.length > 0 && (
          <p className="text-[11px] text-text-muted">With: {data.attendees.join(', ')}</p>
        )}
        {data.agenda?.length > 0 && (
          <ol className="space-y-0.5 mt-1">
            {data.agenda.map((item, i) => (
              <li key={i} className="text-[12px] text-text-secondary flex items-start gap-1.5">
                <span className="text-[10px] text-[#999] mt-0.5 w-3 shrink-0">{i + 1}.</span>
                {item}
              </li>
            ))}
          </ol>
        )}
      </div>
      <div className="border-t border-border px-4 py-3 flex items-center gap-2">
        <button
          onClick={() => {
            setBooked(true)
            onAction(`Book meeting: "${data.topic}" with ${data.attendees?.join(', ')}`)
          }}
          className={BTN_PRIMARY_FILLED}
        >
          Book
        </button>
        <button
          onClick={() => onAction(`Edit meeting agenda for "${data.topic}"`)}
          className={BTN_SECONDARY}
        >
          Edit Agenda
        </button>
      </div>
    </div>
  )
}

// =============================================================================
// Smart Summary (batch save with checkboxes)
// =============================================================================

const TYPE_BADGE_STYLES: Record<string, string> = {
  feature: 'bg-[#E8F5E9] text-[#25785A]',
  constraint: 'bg-[#FEF3C7] text-[#B45309]',
  task: 'bg-[#DBEAFE] text-[#1D4ED8]',
  question: 'bg-[#F3E8FF] text-[#7C3AED]',
}

function SmartSummaryCard({ data, onAction }: { data: SmartSummaryData; onAction: (cmd: string) => void }) {
  const [checks, setChecks] = useState<boolean[]>(() =>
    (data.items || []).map((item) => item.checked ?? true)
  )
  const [saved, setSaved] = useState(false)

  const selectedCount = checks.filter(Boolean).length

  const handleToggle = (idx: number) => {
    if (saved) return
    setChecks((prev) => {
      const next = [...prev]
      next[idx] = !next[idx]
      return next
    })
  }

  const handleSave = () => {
    const selectedItems = (data.items || [])
      .filter((_, i) => checks[i])
      .map((item, i) => `${i + 1}. ${item.type}: ${item.label}`)
      .join(', ')
    setSaved(true)
    onAction(`Save these to BRD: ${selectedItems}`)
  }

  if (saved) {
    return (
      <div className={CARD_RESOLVED}>
        <CheckCircle2 className="h-3.5 w-3.5 text-brand-primary" />
        <span className="text-[12px] text-[#25785A] font-medium">
          {selectedCount} item{selectedCount !== 1 ? 's' : ''} saved to BRD
        </span>
      </div>
    )
  }

  return (
    <div className={CARD_BASE}>
      <p className={CARD_HEADER}>From our discussion</p>
      <div className="space-y-1">
        {(data.items || []).map((item, i) => (
          <label
            key={i}
            className="flex items-start gap-2.5 cursor-pointer group py-1.5"
            onClick={() => handleToggle(i)}
          >
            <span
              className={`w-[18px] h-[18px] rounded border flex items-center justify-center shrink-0 mt-0.5 transition-colors ${
                checks[i]
                  ? 'bg-brand-primary border-brand-primary'
                  : 'border-[#D5D5D5] group-hover:border-brand-primary'
              }`}
            >
              {checks[i] && <Check className="h-3 w-3 text-white" />}
            </span>
            <div className="flex-1 min-w-0">
              <span
                className={`text-[10px] rounded px-1.5 py-0.5 font-medium uppercase tracking-wide mb-1 inline-block ${
                  TYPE_BADGE_STYLES[item.type] || TYPE_BADGE_STYLES.task
                }`}
              >
                {item.type}
              </span>
              <span className="text-[12px] text-[#333] block">{item.label}</span>
            </div>
          </label>
        ))}
      </div>
      <div className="border-t border-border mt-3 pt-3 flex items-center justify-between">
        <span className="text-[11px] text-[#999]">
          {selectedCount} of {data.items?.length || 0} selected
        </span>
        <button
          onClick={handleSave}
          disabled={selectedCount === 0}
          className={`${BTN_PRIMARY_FILLED} disabled:opacity-40 disabled:pointer-events-none`}
        >
          Save selected to BRD
        </button>
      </div>
    </div>
  )
}

// =============================================================================
// Evidence (tag document quotes)
// =============================================================================

const EVIDENCE_TAG_STYLES: Record<string, string> = {
  feature: 'hover:bg-[#E8F5E9] hover:text-[#25785A] hover:border-brand-primary',
  constraint: 'hover:bg-[#FEF3C7] hover:text-[#B45309] hover:border-[#B45309]',
  assumption: 'hover:bg-[#F3E8FF] hover:text-[#7C3AED] hover:border-[#7C3AED]',
  dismiss: 'hover:bg-surface-subtle hover:text-[#999] hover:border-[#999]',
}

function EvidenceCard({ data, onAction }: { data: EvidenceData; onAction: (cmd: string) => void }) {
  return (
    <div className="space-y-3">
      {(data.items || []).map((item, i) => (
        <EvidenceItem key={i} item={item} onAction={onAction} />
      ))}
    </div>
  )
}

function EvidenceItem({ item, onAction }: { item: EvidenceItem; onAction: (cmd: string) => void }) {
  const [tagged, setTagged] = useState(false)

  return (
    <div
      className={`border border-border rounded-2xl bg-[#F7F8FA] px-4 py-4 transition-all duration-300 ${
        tagged ? 'opacity-0 max-h-0 py-0 px-0 mt-0 overflow-hidden border-0' : ''
      }`}
    >
      <div className="border-l-[3px] border-brand-primary pl-3 mb-2">
        <p className="text-[12px] italic text-text-secondary">&ldquo;{item.quote}&rdquo;</p>
        <p className="text-[10px] text-[#999] mt-0.5">
          {item.source}{item.section ? ` — ${item.section}` : ''}
        </p>
      </div>
      <div className="flex items-center gap-1.5">
        {(['feature', 'constraint', 'assumption', 'dismiss'] as const).map((tag) => (
          <button
            key={tag}
            onClick={() => {
              setTagged(true)
              if (tag === 'dismiss') {
                onAction(`Dismiss evidence: "${item.quote.slice(0, 60)}..."`)
              } else {
                onAction(`Tag as ${tag}: "${item.quote.slice(0, 60)}..." from ${item.source}`)
              }
            }}
            className={`text-[12px] font-medium px-3 py-1 rounded-full border border-border text-text-secondary transition-colors capitalize ${
              EVIDENCE_TAG_STYLES[tag] || ''
            }`}
          >
            {tag}
          </button>
        ))}
      </div>
    </div>
  )
}

// =============================================================================
// Discovery Probe
// =============================================================================

function DiscoveryProbeCard({ data, onAction }: { data: DiscoveryProbeData; onAction: (cmd: string) => void }) {
  const [resolved, setResolved] = useState(false)
  const categoryStyle = NORTH_STAR_CATEGORY_STYLES[data.category] || NORTH_STAR_CATEGORY_STYLES.organizational_impact

  if (resolved) {
    return (
      <div className={CARD_RESOLVED}>
        <CheckCircle2 className="h-3.5 w-3.5 text-brand-primary" />
        <span className="text-[12px] text-[#25785A] font-medium">Probe resolved</span>
      </div>
    )
  }

  return (
    <div className={CARD_BASE}>
      <div className="flex items-center gap-2 mb-2">
        <span
          className="text-[10px] rounded-full px-2 py-0.5 font-medium"
          style={{ backgroundColor: categoryStyle.bg, color: categoryStyle.text }}
        >
          {categoryStyle.label}
        </span>
      </div>
      {data.context && (
        <p className="text-[11px] text-text-muted mb-1.5">{data.context}</p>
      )}
      <p className="text-[13px] font-medium text-[#333] mb-1">{data.question}</p>
      {data.why && (
        <p className="text-[11px] italic text-[#999] mb-3">{data.why}</p>
      )}
      <div className="flex items-center gap-2">
        <button
          onClick={() => onAction(data.question)}
          className={BTN_PRIMARY_OUTLINE}
        >
          Discuss in Chat
        </button>
        <button
          onClick={() => {
            setResolved(true)
            onAction(`Mark probe resolved: ${data.question.slice(0, 60)}`)
          }}
          className={BTN_SECONDARY}
        >
          Mark Resolved
        </button>
      </div>
    </div>
  )
}
