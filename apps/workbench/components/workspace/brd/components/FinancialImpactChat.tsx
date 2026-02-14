'use client'

import { useState, useEffect, useRef } from 'react'
import { X, DollarSign } from 'lucide-react'
import { FinancialImpactCard } from './FinancialImpactCard'
import {
  useFinancialImpactChat,
  type FinancialChatMessage,
  type FinancialChatComponent,
  type FinancialValues,
} from '@/lib/useFinancialImpactChat'

// ============================================================================
// Props
// ============================================================================

interface FinancialImpactChatProps {
  existingValues?: Partial<FinancialValues>
  onSave: (values: FinancialValues) => void
  onCancel: () => void
}

// ============================================================================
// Constants
// ============================================================================

const IMPACT_TYPES = [
  { id: 'cost_reduction', label: 'Cost Reduction' },
  { id: 'revenue_increase', label: 'Revenue Increase' },
  { id: 'revenue_new', label: 'New Revenue' },
  { id: 'risk_avoidance', label: 'Risk Avoidance' },
  { id: 'productivity_gain', label: 'Productivity Gain' },
] as const

const TIMEFRAMES = [
  { id: 'annual', label: 'Annual' },
  { id: 'monthly', label: 'Monthly' },
  { id: 'quarterly', label: 'Quarterly' },
  { id: 'one_time', label: 'One-time' },
] as const

// ============================================================================
// Main Component
// ============================================================================

export function FinancialImpactChat({
  existingValues,
  onSave,
  onCancel,
}: FinancialImpactChatProps) {
  const chat = useFinancialImpactChat()
  const scrollRef = useRef<HTMLDivElement>(null)

  // Initialize on mount
  useEffect(() => {
    chat.initializeChat(existingValues)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Auto-scroll on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [chat.messages, chat.isTyping])

  return (
    <div className="border border-[#E5E5E5] rounded-xl overflow-hidden bg-white">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-[#F4F4F4] border-b border-[#E5E5E5]">
        <div className="flex items-center gap-2">
          <DollarSign className="w-4 h-4 text-[#3FAF7A]" />
          <span className="text-[13px] font-semibold text-[#333333]">Financial Impact Assessment</span>
        </div>
        <button
          onClick={onCancel}
          className="p-1 rounded-md text-[#999999] hover:text-[#666666] hover:bg-[#E5E5E5] transition-colors"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Messages area */}
      <div
        ref={scrollRef}
        className="max-h-[400px] overflow-y-auto px-4 py-3 space-y-3 bg-[#F4F4F4]"
      >
        {chat.messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} chat={chat} />
        ))}

        {/* Typing indicator */}
        {chat.isTyping && (
          <div className="flex justify-start">
            <div className="bg-[#E8F5E9] rounded-xl px-3 py-2 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-[#3FAF7A] animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-1.5 h-1.5 rounded-full bg-[#3FAF7A] animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-1.5 h-1.5 rounded-full bg-[#3FAF7A] animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-end gap-2 px-4 py-2.5 border-t border-[#E5E5E5] bg-white">
        <button
          onClick={onCancel}
          className="px-3 py-1.5 text-[12px] font-medium text-[#666666] hover:text-[#333333] rounded-lg hover:bg-[#F0F0F0] transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={() => onSave(chat.getValues())}
          disabled={!chat.isComplete}
          className={`px-4 py-1.5 text-[12px] font-medium rounded-lg transition-colors ${
            chat.isComplete
              ? 'bg-[#3FAF7A] text-white hover:bg-[#25785A]'
              : 'bg-[#F0F0F0] text-[#999999] cursor-not-allowed'
          }`}
        >
          Save Impact
        </button>
      </div>
    </div>
  )
}

// ============================================================================
// Message Bubble
// ============================================================================

function MessageBubble({
  message,
  chat,
}: {
  message: FinancialChatMessage
  chat: ReturnType<typeof useFinancialImpactChat>
}) {
  const isAssistant = message.role === 'assistant'

  return (
    <div className={`flex ${isAssistant ? 'justify-start' : 'justify-end'}`}>
      <div
        className={`max-w-[90%] ${
          isAssistant
            ? 'bg-[#E8F5E9] rounded-xl px-3 py-2'
            : 'bg-white border border-[#E5E5E5] rounded-xl px-3 py-2'
        }`}
      >
        {message.content && (
          <p className="text-[13px] text-[#333333] leading-relaxed whitespace-pre-wrap">
            {renderMarkdownBold(message.content)}
          </p>
        )}
        {message.component && (
          <div className={message.content ? 'mt-2' : ''}>
            <InlineComponent component={message.component} chat={chat} />
          </div>
        )}
      </div>
    </div>
  )
}

function renderMarkdownBold(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*)/)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i}>{part.slice(2, -2)}</strong>
    }
    return part
  })
}

// ============================================================================
// Inline Components
// ============================================================================

function InlineComponent({
  component,
  chat,
}: {
  component: FinancialChatComponent
  chat: ReturnType<typeof useFinancialImpactChat>
}) {
  switch (component.type) {
    case 'type_selector':
      return <TypeSelector onSelect={chat.selectType} disabled={chat.currentStep !== 'type'} selectedType={chat.values.monetary_type} />
    case 'range_input':
      return <RangeInput onSubmit={chat.setRange} disabled={chat.currentStep !== 'range'} />
    case 'timeframe_confidence':
      return <TimeframeConfidence onSubmit={chat.setTimeframeAndConfidence} disabled={chat.currentStep !== 'timeframe'} />
    case 'summary':
      return (
        <FinancialImpactCard
          monetaryValueLow={component.values.monetary_value_low}
          monetaryValueHigh={component.values.monetary_value_high}
          monetaryType={component.values.monetary_type}
          monetaryTimeframe={component.values.monetary_timeframe}
          monetaryConfidence={component.values.monetary_confidence}
          monetarySource={component.values.monetary_source}
        />
      )
    default:
      return null
  }
}

// ============================================================================
// Type Selector
// ============================================================================

function TypeSelector({
  onSelect,
  disabled,
  selectedType,
}: {
  onSelect: (type: string) => void
  disabled: boolean
  selectedType: string | null
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {IMPACT_TYPES.map((t) => {
        const isSelected = selectedType === t.id
        return (
          <button
            key={t.id}
            onClick={() => !disabled && onSelect(t.id)}
            disabled={disabled}
            className={`px-3 py-1.5 text-[12px] font-medium rounded-lg transition-colors ${
              isSelected
                ? 'bg-[#3FAF7A] text-white'
                : disabled
                  ? 'bg-[#F0F0F0] text-[#999999] cursor-default'
                  : 'bg-white border border-[#E5E5E5] text-[#666666] hover:border-[#3FAF7A] hover:text-[#25785A]'
            }`}
          >
            {t.label}
          </button>
        )
      })}
    </div>
  )
}

// ============================================================================
// Range Input
// ============================================================================

function RangeInput({
  onSubmit,
  disabled,
}: {
  onSubmit: (low: number, high: number) => void
  disabled: boolean
}) {
  const [low, setLow] = useState('')
  const [high, setHigh] = useState('')

  const handleSubmit = () => {
    const lowNum = parseFloat(low.replace(/[^0-9.]/g, '')) || 0
    const highNum = parseFloat(high.replace(/[^0-9.]/g, '')) || lowNum
    if (lowNum > 0 || highNum > 0) {
      onSubmit(lowNum, highNum)
    }
  }

  if (disabled) {
    return null
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[12px] text-[#999999]">$</span>
          <input
            type="text"
            value={low}
            onChange={(e) => setLow(e.target.value)}
            placeholder="Low estimate"
            className="w-full pl-6 pr-3 py-1.5 text-[12px] border border-[#E5E5E5] rounded-lg bg-white text-[#333333] placeholder:text-[#999999] focus:outline-none focus:border-[#3FAF7A]"
          />
        </div>
        <span className="text-[12px] text-[#999999]">—</span>
        <div className="relative flex-1">
          <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[12px] text-[#999999]">$</span>
          <input
            type="text"
            value={high}
            onChange={(e) => setHigh(e.target.value)}
            placeholder="High estimate"
            className="w-full pl-6 pr-3 py-1.5 text-[12px] border border-[#E5E5E5] rounded-lg bg-white text-[#333333] placeholder:text-[#999999] focus:outline-none focus:border-[#3FAF7A]"
          />
        </div>
      </div>
      <button
        onClick={handleSubmit}
        disabled={!low && !high}
        className={`w-full py-1.5 text-[12px] font-medium rounded-lg transition-colors ${
          low || high
            ? 'bg-[#3FAF7A] text-white hover:bg-[#25785A]'
            : 'bg-[#F0F0F0] text-[#999999] cursor-not-allowed'
        }`}
      >
        Set Range
      </button>
    </div>
  )
}

// ============================================================================
// Timeframe + Confidence
// ============================================================================

function TimeframeConfidence({
  onSubmit,
  disabled,
}: {
  onSubmit: (timeframe: string, confidence: number, source?: string) => void
  disabled: boolean
}) {
  const [timeframe, setTimeframe] = useState('annual')
  const [confidence, setConfidence] = useState(50)
  const [source, setSource] = useState('')

  if (disabled) {
    return null
  }

  return (
    <div className="space-y-3">
      {/* Timeframe */}
      <div>
        <span className="text-[11px] font-medium text-[#999999] uppercase tracking-wide block mb-1.5">
          Timeframe
        </span>
        <div className="flex gap-1">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf.id}
              onClick={() => setTimeframe(tf.id)}
              className={`flex-1 px-2 py-1.5 text-[11px] font-medium rounded-lg transition-colors ${
                timeframe === tf.id
                  ? 'bg-[#3FAF7A] text-white'
                  : 'bg-white border border-[#E5E5E5] text-[#666666] hover:border-[#3FAF7A]'
              }`}
            >
              {tf.label}
            </button>
          ))}
        </div>
      </div>

      {/* Confidence */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[11px] font-medium text-[#999999] uppercase tracking-wide">
            Confidence
          </span>
          <span className="text-[12px] font-semibold text-[#333333]">{confidence}%</span>
        </div>
        <input
          type="range"
          min={0}
          max={100}
          value={confidence}
          onChange={(e) => setConfidence(parseInt(e.target.value))}
          className="w-full h-1.5 bg-[#E5E5E5] rounded-full appearance-none cursor-pointer accent-[#3FAF7A]"
        />
      </div>

      {/* Source (optional) */}
      <div>
        <span className="text-[11px] font-medium text-[#999999] uppercase tracking-wide block mb-1.5">
          Source / Notes (optional)
        </span>
        <textarea
          value={source}
          onChange={(e) => setSource(e.target.value)}
          placeholder="e.g. CFO estimate, industry benchmark..."
          rows={2}
          className="w-full px-3 py-1.5 text-[12px] border border-[#E5E5E5] rounded-lg bg-white text-[#333333] placeholder:text-[#999999] focus:outline-none focus:border-[#3FAF7A] resize-none"
        />
      </div>

      <button
        onClick={() => onSubmit(timeframe, confidence / 100, source || undefined)}
        className="w-full py-1.5 text-[12px] font-medium rounded-lg bg-[#3FAF7A] text-white hover:bg-[#25785A] transition-colors"
      >
        Continue
      </button>
    </div>
  )
}
