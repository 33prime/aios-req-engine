'use client'

import { useState, useCallback, useRef } from 'react'
import type {
  DesignProfile,
  DesignSelection,
  DesignTokens,
  BrandData,
  GenericStyle,
  DesignInspiration,
} from '@/types/prototype'

// ============================================================================
// Types
// ============================================================================

export type DesignChatStep = 'brand' | 'references' | 'tokens' | 'preview'

export interface DesignChatMessage {
  id: string
  role: 'assistant' | 'user'
  content: string
  /** Inline component to render inside the message */
  component?: ChatComponent
}

export type ChatComponent =
  | { type: 'brand_choice'; brand: BrandData }
  | { type: 'style_grid'; styles: GenericStyle[] }
  | { type: 'reference_selector'; inspirations: DesignInspiration[]; competitors: { id: string; name: string; url?: string }[] }
  | { type: 'token_editor'; tokens: DesignTokens }
  | { type: 'summary'; selection: DesignSelection }

export interface DesignChatState {
  messages: DesignChatMessage[]
  currentStep: DesignChatStep
  selections: {
    brandSource: 'extracted' | 'generic' | null
    selectedStyle: GenericStyle | null
    designReferences: string[]
    tokenOverrides: Partial<DesignTokens>
  }
  isComplete: boolean
}

export interface UseDesignChatReturn {
  messages: DesignChatMessage[]
  currentStep: DesignChatStep
  isTyping: boolean
  isComplete: boolean
  selections: DesignChatState['selections']
  initializeChat: (profile: DesignProfile, designRefCompetitors?: { id: string; name: string; url?: string }[]) => void
  selectBrandSource: (source: 'extracted' | 'generic') => void
  selectStyle: (style: GenericStyle) => void
  selectReferences: (ids: string[]) => void
  updateTokens: (overrides: Partial<DesignTokens>) => void
  confirmTokens: () => void
  getSelection: () => DesignSelection | null
  reset: () => void
}

// ============================================================================
// Helpers
// ============================================================================

let msgCounter = 0
function makeId(): string {
  return `dcm_${++msgCounter}_${Date.now()}`
}

function brandToTokens(brand: BrandData): DesignTokens {
  const colors = brand.brand_colors || []
  const chars = brand.design_characteristics
  return {
    primary_color: colors[0] || '#000000',
    secondary_color: colors[1] || '#f5f5f5',
    accent_color: colors[2] || colors[0] || '#3b82f6',
    font_heading: brand.typography?.heading_font || 'Inter',
    font_body: brand.typography?.body_font || 'Inter',
    spacing: chars?.spacing || 'balanced',
    corners: chars?.corners || 'slightly-rounded',
    style_direction: chars?.overall_feel
      ? `Match client brand: ${chars.overall_feel} feel with ${chars.visual_weight || 'medium'} visual weight`
      : 'Match client brand identity',
    logo_url: brand.logo_url || undefined,
  }
}

// ============================================================================
// Hook
// ============================================================================

export function useDesignChat(): UseDesignChatReturn {
  const [state, setState] = useState<DesignChatState>({
    messages: [],
    currentStep: 'brand',
    selections: {
      brandSource: null,
      selectedStyle: null,
      designReferences: [],
      tokenOverrides: {},
    },
    isComplete: false,
  })
  const [isTyping, setIsTyping] = useState(false)
  const profileRef = useRef<DesignProfile | null>(null)
  const competitorsRef = useRef<{ id: string; name: string; url?: string }[]>([])

  const addMessages = useCallback((msgs: DesignChatMessage[], delay = 400) => {
    setIsTyping(true)
    setTimeout(() => {
      setState((prev) => ({
        ...prev,
        messages: [...prev.messages, ...msgs],
      }))
      setIsTyping(false)
    }, delay)
  }, [])

  const initializeChat = useCallback((profile: DesignProfile, designRefCompetitors?: { id: string; name: string; url?: string }[]) => {
    profileRef.current = profile
    competitorsRef.current = designRefCompetitors || []

    const greeting: DesignChatMessage = {
      id: makeId(),
      role: 'assistant',
      content: "Welcome to the Design Assistant! I'll help you configure the visual direction for your prototype in a few quick steps.",
    }

    const msgs: DesignChatMessage[] = [greeting]

    if (profile.brand_available && profile.brand) {
      msgs.push({
        id: makeId(),
        role: 'assistant',
        content: "I found brand data from your client's website. Would you like to use their brand identity, or start with a preset style?",
        component: { type: 'brand_choice', brand: profile.brand },
      })
    } else {
      msgs.push({
        id: makeId(),
        role: 'assistant',
        content: "No brand data was found for this project. Let's pick a preset style to get started.",
        component: { type: 'style_grid', styles: profile.generic_styles },
      })
    }

    setState({
      messages: msgs,
      currentStep: 'brand',
      selections: {
        brandSource: null,
        selectedStyle: null,
        designReferences: [],
        tokenOverrides: {},
      },
      isComplete: false,
    })
  }, [])

  const selectBrandSource = useCallback((source: 'extracted' | 'generic') => {
    const profile = profileRef.current
    if (!profile) return

    setState((prev) => ({
      ...prev,
      selections: { ...prev.selections, brandSource: source },
      messages: [
        ...prev.messages,
        {
          id: makeId(),
          role: 'user',
          content: source === 'extracted' ? 'Use my brand' : 'Choose a style',
        },
      ],
    }))

    if (source === 'extracted') {
      // Move to references step
      const refMsg: DesignChatMessage[] = [
        {
          id: makeId(),
          role: 'assistant',
          content: "Great choice! Your brand identity will be used as the foundation.",
        },
      ]

      const hasRefs = (profile.design_inspirations?.length || 0) > 0 || competitorsRef.current.length > 0
      if (hasRefs) {
        refMsg.push({
          id: makeId(),
          role: 'assistant',
          content: "Do you have any design references to draw inspiration from? Select any that apply, or skip this step.",
          component: {
            type: 'reference_selector',
            inspirations: profile.design_inspirations || [],
            competitors: competitorsRef.current,
          },
        })
        addMessages(refMsg)
        setState((prev) => ({ ...prev, currentStep: 'references' }))
      } else {
        // Skip to tokens
        const tokens = brandToTokens(profile.brand!)
        refMsg.push({
          id: makeId(),
          role: 'assistant',
          content: "Here are the design tokens based on your brand. Adjust anything you'd like, then confirm.",
          component: { type: 'token_editor', tokens },
        })
        addMessages(refMsg)
        setState((prev) => ({
          ...prev,
          currentStep: 'tokens',
          selections: { ...prev.selections, tokenOverrides: tokens },
        }))
      }
    } else {
      // Show style grid
      addMessages([{
        id: makeId(),
        role: 'assistant',
        content: "Pick the style that best matches your vision:",
        component: { type: 'style_grid', styles: profile.generic_styles },
      }])
    }
  }, [addMessages])

  const selectStyle = useCallback((style: GenericStyle) => {
    const profile = profileRef.current
    if (!profile) return

    setState((prev) => ({
      ...prev,
      selections: {
        ...prev.selections,
        brandSource: 'generic',
        selectedStyle: style,
        tokenOverrides: { ...style.tokens },
      },
      messages: [
        ...prev.messages,
        { id: makeId(), role: 'user', content: style.label },
      ],
    }))

    const hasRefs = (profile.design_inspirations?.length || 0) > 0 || competitorsRef.current.length > 0
    if (hasRefs) {
      addMessages([
        {
          id: makeId(),
          role: 'assistant',
          content: `**${style.label}** — nice pick! Any design references you'd like to factor in?`,
          component: {
            type: 'reference_selector',
            inspirations: profile.design_inspirations || [],
            competitors: competitorsRef.current,
          },
        },
      ])
      setState((prev) => ({ ...prev, currentStep: 'references' }))
    } else {
      addMessages([
        {
          id: makeId(),
          role: 'assistant',
          content: "Here are the design tokens. Adjust anything you'd like, then confirm.",
          component: { type: 'token_editor', tokens: style.tokens },
        },
      ])
      setState((prev) => ({ ...prev, currentStep: 'tokens' }))
    }
  }, [addMessages])

  const selectReferences = useCallback((ids: string[]) => {
    const profile = profileRef.current
    if (!profile) return

    const label = ids.length === 0 ? 'Skip references' : `Selected ${ids.length} reference${ids.length > 1 ? 's' : ''}`

    setState((prev) => ({
      ...prev,
      currentStep: 'tokens',
      selections: { ...prev.selections, designReferences: ids },
      messages: [
        ...prev.messages,
        { id: makeId(), role: 'user', content: label },
      ],
    }))

    // Determine base tokens
    const baseTokens = state.selections.brandSource === 'extracted' && profile.brand
      ? brandToTokens(profile.brand)
      : state.selections.selectedStyle?.tokens || profile.generic_styles[0]?.tokens || {
          primary_color: '#000000',
          secondary_color: '#f5f5f5',
          accent_color: '#3b82f6',
          font_heading: 'Inter',
          font_body: 'Inter',
          spacing: 'balanced',
          corners: 'slightly-rounded',
          style_direction: '',
        }

    addMessages([
      {
        id: makeId(),
        role: 'assistant',
        content: "Here are the design tokens. You can fine-tune colors, fonts, and spacing before generating.",
        component: { type: 'token_editor', tokens: baseTokens as DesignTokens },
      },
    ])

    setState((prev) => ({
      ...prev,
      selections: { ...prev.selections, tokenOverrides: baseTokens },
    }))
  }, [state.selections.brandSource, state.selections.selectedStyle, addMessages])

  const updateTokens = useCallback((overrides: Partial<DesignTokens>) => {
    setState((prev) => ({
      ...prev,
      selections: {
        ...prev.selections,
        tokenOverrides: { ...prev.selections.tokenOverrides, ...overrides },
      },
    }))
  }, [])

  const confirmTokens = useCallback(() => {
    const tokens = state.selections.tokenOverrides as DesignTokens
    const source = state.selections.brandSource === 'extracted' ? 'brand' : 'generic'
    const optionId = state.selections.brandSource === 'extracted'
      ? 'brand_match'
      : state.selections.selectedStyle?.id || 'custom'

    const selection: DesignSelection = {
      option_id: optionId,
      tokens,
      source,
    }

    setState((prev) => ({
      ...prev,
      currentStep: 'preview',
      isComplete: true,
      messages: [
        ...prev.messages,
        { id: makeId(), role: 'user', content: 'Looks good!' },
        {
          id: makeId(),
          role: 'assistant',
          content: "Here's your design configuration. Click **Generate Prototype** when ready!",
          component: { type: 'summary', selection },
        },
      ],
    }))
  }, [state.selections])

  const getSelection = useCallback((): DesignSelection | null => {
    if (!state.isComplete) return null
    const tokens = state.selections.tokenOverrides as DesignTokens
    const source = state.selections.brandSource === 'extracted' ? 'brand' : 'generic'
    const optionId = state.selections.brandSource === 'extracted'
      ? 'brand_match'
      : state.selections.selectedStyle?.id || 'custom'

    return { option_id: optionId, tokens, source }
  }, [state.isComplete, state.selections])

  const reset = useCallback(() => {
    msgCounter = 0
    profileRef.current = null
    competitorsRef.current = []
    setState({
      messages: [],
      currentStep: 'brand',
      selections: {
        brandSource: null,
        selectedStyle: null,
        designReferences: [],
        tokenOverrides: {},
      },
      isComplete: false,
    })
    setIsTyping(false)
  }, [])

  return {
    messages: state.messages,
    currentStep: state.currentStep,
    isTyping,
    isComplete: state.isComplete,
    selections: state.selections,
    initializeChat,
    selectBrandSource,
    selectStyle,
    selectReferences,
    updateTokens,
    confirmTokens,
    getSelection,
    reset,
  }
}
