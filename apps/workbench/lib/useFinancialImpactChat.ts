'use client'

import { useState, useCallback, useRef } from 'react'

// ============================================================================
// Types
// ============================================================================

export type FinancialChatStep = 'type' | 'range' | 'timeframe' | 'summary'

export interface FinancialChatMessage {
  id: string
  role: 'assistant' | 'user'
  content: string
  component?: FinancialChatComponent
}

export type FinancialChatComponent =
  | { type: 'type_selector' }
  | { type: 'range_input' }
  | { type: 'timeframe_confidence' }
  | { type: 'summary'; values: FinancialValues }

export interface FinancialValues {
  monetary_type: string | null
  monetary_value_low: number | null
  monetary_value_high: number | null
  monetary_timeframe: string | null
  monetary_confidence: number | null
  monetary_source: string | null
}

export interface FinancialChatState {
  messages: FinancialChatMessage[]
  currentStep: FinancialChatStep
  values: FinancialValues
  isComplete: boolean
}

export interface UseFinancialImpactChatReturn {
  messages: FinancialChatMessage[]
  currentStep: FinancialChatStep
  isTyping: boolean
  isComplete: boolean
  values: FinancialValues
  initializeChat: (existingValues?: Partial<FinancialValues>) => void
  selectType: (type: string) => void
  setRange: (low: number, high: number) => void
  setTimeframeAndConfidence: (timeframe: string, confidence: number, source?: string) => void
  getValues: () => FinancialValues
  reset: () => void
}

// ============================================================================
// Helpers
// ============================================================================

let msgCounter = 0
function makeId(): string {
  return `fim_${++msgCounter}_${Date.now()}`
}

const TYPE_LABELS: Record<string, string> = {
  cost_reduction: 'Cost Reduction',
  revenue_increase: 'Revenue Increase',
  revenue_new: 'New Revenue',
  risk_avoidance: 'Risk Avoidance',
  productivity_gain: 'Productivity Gain',
}

const TIMEFRAME_LABELS: Record<string, string> = {
  annual: 'Annual',
  monthly: 'Monthly',
  quarterly: 'Quarterly',
  one_time: 'One-time',
}

function formatCurrency(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `$${Math.round(value / 1_000)}K`
  return `$${value.toFixed(0)}`
}

const EMPTY_VALUES: FinancialValues = {
  monetary_type: null,
  monetary_value_low: null,
  monetary_value_high: null,
  monetary_timeframe: null,
  monetary_confidence: null,
  monetary_source: null,
}

// ============================================================================
// Hook
// ============================================================================

export function useFinancialImpactChat(): UseFinancialImpactChatReturn {
  const [state, setState] = useState<FinancialChatState>({
    messages: [],
    currentStep: 'type',
    values: { ...EMPTY_VALUES },
    isComplete: false,
  })
  const [isTyping, setIsTyping] = useState(false)
  const existingRef = useRef<Partial<FinancialValues> | null>(null)

  const addMessages = useCallback((msgs: FinancialChatMessage[], delay = 400) => {
    setIsTyping(true)
    setTimeout(() => {
      setState((prev) => ({
        ...prev,
        messages: [...prev.messages, ...msgs],
      }))
      setIsTyping(false)
    }, delay)
  }, [])

  const initializeChat = useCallback((existingValues?: Partial<FinancialValues>) => {
    existingRef.current = existingValues || null
    const hasExisting = existingValues &&
      (existingValues.monetary_value_low || existingValues.monetary_value_high)

    const msgs: FinancialChatMessage[] = []

    if (hasExisting) {
      const low = existingValues!.monetary_value_low ?? 0
      const high = existingValues!.monetary_value_high ?? low
      const typeLabel = TYPE_LABELS[existingValues!.monetary_type || ''] || existingValues!.monetary_type || ''
      const range = low > 0 && high > 0 && low !== high
        ? `${formatCurrency(low)} – ${formatCurrency(high)}`
        : formatCurrency(high || low)
      msgs.push({
        id: makeId(),
        role: 'assistant',
        content: `I see you already have a ${typeLabel ? typeLabel.toLowerCase() + ' ' : ''}estimate of **${range}**. Let's update it.`,
      })
    } else {
      msgs.push({
        id: makeId(),
        role: 'assistant',
        content: "Let's estimate the financial impact of this KPI. First, what type of impact does this represent?",
      })
    }

    msgs.push({
      id: makeId(),
      role: 'assistant',
      content: '',
      component: { type: 'type_selector' },
    })

    setState({
      messages: msgs,
      currentStep: 'type',
      values: existingValues
        ? { ...EMPTY_VALUES, ...existingValues }
        : { ...EMPTY_VALUES },
      isComplete: false,
    })
  }, [])

  const selectType = useCallback((type: string) => {
    const label = TYPE_LABELS[type] || type

    setState((prev) => ({
      ...prev,
      currentStep: 'range',
      values: { ...prev.values, monetary_type: type },
      messages: [
        ...prev.messages,
        { id: makeId(), role: 'user', content: label },
      ],
    }))

    addMessages([
      {
        id: makeId(),
        role: 'assistant',
        content: `Got it — **${label}**. What's the estimated value range?`,
        component: { type: 'range_input' },
      },
    ])
  }, [addMessages])

  const setRange = useCallback((low: number, high: number) => {
    const rangeText = low > 0 && high > 0 && low !== high
      ? `${formatCurrency(low)} – ${formatCurrency(high)}`
      : formatCurrency(high || low)

    setState((prev) => ({
      ...prev,
      currentStep: 'timeframe',
      values: { ...prev.values, monetary_value_low: low, monetary_value_high: high },
      messages: [
        ...prev.messages,
        { id: makeId(), role: 'user', content: rangeText },
      ],
    }))

    addMessages([
      {
        id: makeId(),
        role: 'assistant',
        content: 'How often does this recur, and how confident are you in this estimate?',
        component: { type: 'timeframe_confidence' },
      },
    ])
  }, [addMessages])

  const setTimeframeAndConfidence = useCallback((
    timeframe: string,
    confidence: number,
    source?: string,
  ) => {
    const tfLabel = TIMEFRAME_LABELS[timeframe] || timeframe
    const confPct = Math.round(confidence * 100)

    setState((prev) => {
      const newValues: FinancialValues = {
        ...prev.values,
        monetary_timeframe: timeframe,
        monetary_confidence: confidence,
        monetary_source: source || prev.values.monetary_source,
      }

      return {
        ...prev,
        currentStep: 'summary' as const,
        isComplete: true,
        values: newValues,
        messages: [
          ...prev.messages,
          {
            id: makeId(),
            role: 'user',
            content: `${tfLabel}, ${confPct}% confidence${source ? ` — ${source}` : ''}`,
          },
          {
            id: makeId(),
            role: 'assistant',
            content: "Here's your financial impact summary:",
            component: { type: 'summary', values: newValues },
          },
        ],
      }
    })
  }, [])

  const getValues = useCallback((): FinancialValues => {
    return state.values
  }, [state.values])

  const reset = useCallback(() => {
    msgCounter = 0
    existingRef.current = null
    setState({
      messages: [],
      currentStep: 'type',
      values: { ...EMPTY_VALUES },
      isComplete: false,
    })
    setIsTyping(false)
  }, [])

  return {
    messages: state.messages,
    currentStep: state.currentStep,
    isTyping,
    isComplete: state.isComplete,
    values: state.values,
    initializeChat,
    selectType,
    setRange,
    setTimeframeAndConfidence,
    getValues,
    reset,
  }
}
