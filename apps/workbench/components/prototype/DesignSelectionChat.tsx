'use client'

import { useState, useEffect, useRef } from 'react'
import { X, Palette, Sparkles, Loader2, Check } from 'lucide-react'
import { DesignCard } from './DesignCard'
import { getDesignProfile } from '@/lib/api'
import { useDesignChat } from '@/lib/useDesignChat'
import type { DesignSelection, DesignTokens, BrandData, GenericStyle, DesignInspiration } from '@/types/prototype'
import type { DesignChatMessage, ChatComponent } from '@/lib/useDesignChat'

interface DesignSelectionChatProps {
  isOpen: boolean
  onClose: () => void
  onGenerate: (selection: DesignSelection) => void
  projectId: string
  isGenerating: boolean
}

export function DesignSelectionChat({
  isOpen,
  onClose,
  onGenerate,
  projectId,
  isGenerating,
}: DesignSelectionChatProps) {
  const [loading, setLoading] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const chat = useDesignChat()

  // Fetch profile and initialize chat
  useEffect(() => {
    if (!isOpen) return

    let cancelled = false
    setLoading(true)

    getDesignProfile(projectId)
      .then((data) => {
        if (cancelled) return
        // Build competitor design refs from design_inspirations
        const competitorRefs = (data.design_inspirations || [])
          .filter((d) => d.source === 'competitor_ref')
          .map((d) => ({ id: d.id, name: d.name, url: d.url || undefined }))
        chat.initializeChat(data, competitorRefs)
      })
      .catch(() => {
        if (!cancelled) {
          // Initialize with empty profile
          chat.initializeChat({
            brand_available: false,
            brand: null,
            design_inspirations: [],
            suggested_style: null,
            style_source: null,
            generic_styles: [],
          })
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, projectId])

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chat.messages, chat.isTyping])

  // Reset on close
  useEffect(() => {
    if (!isOpen) chat.reset()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen])

  const handleGenerate = () => {
    const selection = chat.getSelection()
    if (selection) onGenerate(selection)
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-md">
      <div className="max-w-2xl w-full h-[66vh] bg-white rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="relative bg-gradient-to-r from-[#0A1E2F] to-[#0D2A35] px-4 py-3.5 text-white flex-shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-10 h-10 rounded-2xl bg-white/10 backdrop-blur-sm flex items-center justify-center">
                <Palette className="w-4.5 h-4.5" />
              </div>
              <h2 className="text-base font-bold">Design Assistant</h2>
            </div>
            <button onClick={onClose} className="text-white hover:text-gray-200 transition-colors p-1.5">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Messages area */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-2.5 bg-[#F4F4F4]">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-[#3FAF7A]" />
              <span className="ml-2 text-sm text-[#999999]">Loading design options...</span>
            </div>
          ) : (
            <>
              {chat.messages.map((msg) => (
                <MessageBubble
                  key={msg.id}
                  message={msg}
                  onSelectBrandSource={chat.selectBrandSource}
                  onSelectStyle={chat.selectStyle}
                  onSelectReferences={chat.selectReferences}
                  onUpdateTokens={chat.updateTokens}
                  onConfirmTokens={chat.confirmTokens}
                />
              ))}

              {/* Typing indicator */}
              {chat.isTyping && (
                <div className="flex items-start">
                  <div className="bg-white border border-[#E5E5E5] rounded-2xl rounded-bl-md px-4 py-3 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
                    <div className="flex items-center gap-2">
                      <div className="flex gap-1">
                        <div className="w-1.5 h-1.5 bg-[#3FAF7A] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                        <div className="w-1.5 h-1.5 bg-[#3FAF7A] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                        <div className="w-1.5 h-1.5 bg-[#3FAF7A] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                      </div>
                      <span className="text-[12px] text-[#999999]">Thinking...</span>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-[#E5E5E5] px-4 py-3.5 bg-white flex-shrink-0">
          {chat.isComplete ? (
            <div className="flex items-center justify-end gap-2.5">
              <button
                onClick={onClose}
                disabled={isGenerating}
                className="px-4 py-2.5 text-[13px] font-medium text-[#666666] bg-[#F0F0F0] rounded-2xl hover:bg-[#E5E5E5] transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleGenerate}
                disabled={isGenerating}
                className="px-4 py-2.5 text-[13px] font-medium text-white bg-[#3FAF7A] rounded-2xl hover:bg-[#25785A] transition-colors disabled:opacity-50 flex items-center gap-1.5"
              >
                {isGenerating ? (
                  <><Loader2 className="w-4 h-4 animate-spin" /> Generating...</>
                ) : (
                  <><Sparkles className="w-4 h-4" /> Generate Prototype</>
                )}
              </button>
            </div>
          ) : (
            <p className="text-center text-[12px] text-[#999999]">
              Step {['brand', 'references', 'tokens', 'preview'].indexOf(chat.currentStep) + 1} of 4
              {' — '}
              {chat.currentStep === 'brand' ? 'Brand Foundation' :
               chat.currentStep === 'references' ? 'Design References' :
               chat.currentStep === 'tokens' ? 'Fine-tune Tokens' : 'Preview & Generate'}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// Message Bubble
// ============================================================================

function MessageBubble({
  message,
  onSelectBrandSource,
  onSelectStyle,
  onSelectReferences,
  onUpdateTokens,
  onConfirmTokens,
}: {
  message: DesignChatMessage
  onSelectBrandSource: (source: 'extracted' | 'generic') => void
  onSelectStyle: (style: GenericStyle) => void
  onSelectReferences: (ids: string[]) => void
  onUpdateTokens: (overrides: Partial<DesignTokens>) => void
  onConfirmTokens: () => void
}) {
  if (message.role === 'user') {
    return (
      <div className="flex items-start justify-end">
        <div className="bg-[#0A1E2F] text-white rounded-2xl rounded-br-md px-4 py-3 shadow-sm max-w-[80%]">
          <p className="text-[13px] leading-relaxed">{message.content}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-start">
      <div className="bg-white border border-[#E5E5E5] rounded-2xl rounded-bl-md px-4 py-3 shadow-[0_1px_2px_rgba(0,0,0,0.04)] max-w-[90%]">
        <div className="text-[13px] leading-relaxed text-[#333333]">
          {renderMarkdown(message.content)}
        </div>
        {message.component && (
          <div className="mt-3">
            <InlineChatComponent
              component={message.component}
              onSelectBrandSource={onSelectBrandSource}
              onSelectStyle={onSelectStyle}
              onSelectReferences={onSelectReferences}
              onUpdateTokens={onUpdateTokens}
              onConfirmTokens={onConfirmTokens}
            />
          </div>
        )}
      </div>
    </div>
  )
}

// ============================================================================
// Inline Chat Components
// ============================================================================

function InlineChatComponent({
  component,
  onSelectBrandSource,
  onSelectStyle,
  onSelectReferences,
  onUpdateTokens,
  onConfirmTokens,
}: {
  component: ChatComponent
  onSelectBrandSource: (source: 'extracted' | 'generic') => void
  onSelectStyle: (style: GenericStyle) => void
  onSelectReferences: (ids: string[]) => void
  onUpdateTokens: (overrides: Partial<DesignTokens>) => void
  onConfirmTokens: () => void
}) {
  switch (component.type) {
    case 'brand_choice':
      return <BrandChoiceInline brand={component.brand} onSelect={onSelectBrandSource} />
    case 'style_grid':
      return <StyleGridInline styles={component.styles} onSelect={onSelectStyle} />
    case 'reference_selector':
      return <ReferenceSelectorInline inspirations={component.inspirations} competitors={component.competitors} onConfirm={onSelectReferences} />
    case 'token_editor':
      return <TokenEditorInline tokens={component.tokens} onUpdate={onUpdateTokens} onConfirm={onConfirmTokens} />
    case 'summary':
      return <SummaryInline selection={component.selection} />
    default:
      return null
  }
}

function BrandChoiceInline({ brand, onSelect }: { brand: BrandData; onSelect: (source: 'extracted' | 'generic') => void }) {
  return (
    <div className="space-y-3">
      {/* Brand preview */}
      <div className="p-3 bg-white rounded-lg border border-[#E5E5E5]">
        <div className="flex items-center gap-2 mb-2">
          {brand.logo_url && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={brand.logo_url} alt="Logo" className="h-5 max-w-[80px] object-contain" />
          )}
          <div className="flex items-center gap-1">
            {brand.brand_colors.slice(0, 5).map((c, i) => (
              <div key={i} className="w-4 h-4 rounded-full border border-black/10" style={{ backgroundColor: c }} />
            ))}
          </div>
        </div>
        {brand.typography && (
          <p className="text-[11px] text-[#999999]">
            {brand.typography.heading_font} / {brand.typography.body_font}
          </p>
        )}
      </div>

      {/* Choice buttons */}
      <div className="flex gap-2">
        <button
          onClick={() => onSelect('extracted')}
          className="flex-1 px-3 py-2 text-[12px] font-medium text-white bg-[#3FAF7A] rounded-lg hover:bg-[#25785A] transition-colors"
        >
          Use my brand
        </button>
        <button
          onClick={() => onSelect('generic')}
          className="flex-1 px-3 py-2 text-[12px] font-medium text-[#666666] bg-white border border-[#E5E5E5] rounded-lg hover:bg-[#F4F4F4] transition-colors"
        >
          Choose a style
        </button>
      </div>
    </div>
  )
}

function StyleGridInline({ styles, onSelect }: { styles: GenericStyle[]; onSelect: (style: GenericStyle) => void }) {
  return (
    <div className="grid grid-cols-2 gap-2">
      {styles.map((style) => (
        <DesignCard
          key={style.id}
          id={style.id}
          label={style.label}
          description={style.description}
          colors={style.preview_colors}
          isSelected={false}
          onSelect={() => onSelect(style)}
          size="sm"
        />
      ))}
    </div>
  )
}

function ReferenceSelectorInline({
  inspirations,
  competitors,
  onConfirm,
}: {
  inspirations: DesignInspiration[]
  competitors: { id: string; name: string; url?: string }[]
  onConfirm: (ids: string[]) => void
}) {
  const [selected, setSelected] = useState<Set<string>>(new Set())

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const allItems = [
    ...inspirations.map((i) => ({ id: i.id, name: i.name, subtitle: i.source === 'competitor_ref' ? 'Design reference' : i.source })),
    ...competitors.map((c) => ({ id: c.id, name: c.name, subtitle: 'Competitor' })),
  ]

  return (
    <div className="space-y-2">
      {allItems.map((item) => (
        <button
          key={item.id}
          onClick={() => toggle(item.id)}
          className={`w-full text-left p-2.5 rounded-lg border transition-all flex items-center gap-2 ${
            selected.has(item.id)
              ? 'border-[#3FAF7A] bg-[#E8F5E9]/50'
              : 'border-[#E5E5E5] bg-white hover:border-[#3FAF7A]/30'
          }`}
        >
          <div className={`w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 ${
            selected.has(item.id) ? 'border-[#3FAF7A] bg-[#3FAF7A]' : 'border-[#E5E5E5]'
          }`}>
            {selected.has(item.id) && <Check className="w-3 h-3 text-white" />}
          </div>
          <div>
            <p className="text-[12px] font-medium text-[#333333]">{item.name}</p>
            <p className="text-[10px] text-[#999999]">{item.subtitle}</p>
          </div>
        </button>
      ))}
      <div className="flex gap-2 pt-1">
        <button
          onClick={() => onConfirm(Array.from(selected))}
          className="flex-1 px-3 py-2 text-[12px] font-medium text-white bg-[#3FAF7A] rounded-lg hover:bg-[#25785A] transition-colors"
        >
          {selected.size > 0 ? `Continue with ${selected.size} selected` : 'Continue'}
        </button>
        <button
          onClick={() => onConfirm([])}
          className="px-3 py-2 text-[12px] font-medium text-[#999999] hover:text-[#666666] transition-colors"
        >
          Skip
        </button>
      </div>
    </div>
  )
}

function TokenEditorInline({
  tokens,
  onUpdate,
  onConfirm,
}: {
  tokens: DesignTokens
  onUpdate: (overrides: Partial<DesignTokens>) => void
  onConfirm: () => void
}) {
  const [localTokens, setLocalTokens] = useState(tokens)

  const handleChange = (key: keyof DesignTokens, value: string) => {
    setLocalTokens((prev) => ({ ...prev, [key]: value }))
    onUpdate({ [key]: value })
  }

  const SPACING_OPTIONS = ['compact', 'balanced', 'generous']
  const CORNER_OPTIONS = ['sharp', 'slightly-rounded', 'rounded', 'pill']
  const FONT_OPTIONS = ['Inter', 'DM Sans', 'Plus Jakarta Sans', 'Sora', 'Playfair Display', 'DM Serif Display', 'Lato', 'System UI']

  return (
    <div className="space-y-3 bg-white rounded-lg border border-[#E5E5E5] p-3">
      {/* Colors */}
      <div>
        <p className="text-[11px] font-medium text-[#999999] uppercase tracking-wider mb-1.5">Colors</p>
        <div className="flex gap-3">
          {(['primary_color', 'secondary_color', 'accent_color'] as const).map((key) => (
            <div key={key} className="flex items-center gap-1.5">
              <label className="relative">
                <input
                  type="color"
                  value={localTokens[key]}
                  onChange={(e) => handleChange(key, e.target.value)}
                  className="w-7 h-7 rounded-full border border-black/10 cursor-pointer appearance-none bg-transparent [&::-webkit-color-swatch-wrapper]:p-0 [&::-webkit-color-swatch]:rounded-full [&::-webkit-color-swatch]:border-0"
                />
              </label>
              <span className="text-[10px] text-[#999999]">{key.replace('_color', '').replace('_', ' ')}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Fonts */}
      <div className="grid grid-cols-2 gap-2">
        <div>
          <p className="text-[10px] font-medium text-[#999999] uppercase tracking-wider mb-1">Heading Font</p>
          <select
            value={localTokens.font_heading}
            onChange={(e) => handleChange('font_heading', e.target.value)}
            className="w-full text-[12px] px-2 py-1.5 border border-[#E5E5E5] rounded-lg text-[#333333] focus:outline-none focus:ring-1 focus:ring-[#3FAF7A]"
          >
            {FONT_OPTIONS.map((f) => <option key={f} value={f}>{f}</option>)}
          </select>
        </div>
        <div>
          <p className="text-[10px] font-medium text-[#999999] uppercase tracking-wider mb-1">Body Font</p>
          <select
            value={localTokens.font_body}
            onChange={(e) => handleChange('font_body', e.target.value)}
            className="w-full text-[12px] px-2 py-1.5 border border-[#E5E5E5] rounded-lg text-[#333333] focus:outline-none focus:ring-1 focus:ring-[#3FAF7A]"
          >
            {FONT_OPTIONS.map((f) => <option key={f} value={f}>{f}</option>)}
          </select>
        </div>
      </div>

      {/* Spacing + Corners */}
      <div className="grid grid-cols-2 gap-2">
        <div>
          <p className="text-[10px] font-medium text-[#999999] uppercase tracking-wider mb-1">Spacing</p>
          <div className="flex gap-1">
            {SPACING_OPTIONS.map((opt) => (
              <button
                key={opt}
                onClick={() => handleChange('spacing', opt)}
                className={`flex-1 px-2 py-1 text-[10px] font-medium rounded-md transition-colors ${
                  localTokens.spacing === opt
                    ? 'bg-[#E8F5E9] text-[#25785A] border border-[#3FAF7A]/20'
                    : 'bg-[#F0F0F0] text-[#999999] border border-transparent hover:bg-[#E5E5E5]'
                }`}
              >
                {opt}
              </button>
            ))}
          </div>
        </div>
        <div>
          <p className="text-[10px] font-medium text-[#999999] uppercase tracking-wider mb-1">Corners</p>
          <div className="flex gap-1">
            {CORNER_OPTIONS.map((opt) => (
              <button
                key={opt}
                onClick={() => handleChange('corners', opt)}
                className={`flex-1 px-1 py-1 text-[10px] font-medium rounded-md transition-colors ${
                  localTokens.corners === opt
                    ? 'bg-[#E8F5E9] text-[#25785A] border border-[#3FAF7A]/20'
                    : 'bg-[#F0F0F0] text-[#999999] border border-transparent hover:bg-[#E5E5E5]'
                }`}
              >
                {opt === 'slightly-rounded' ? 'slight' : opt}
              </button>
            ))}
          </div>
        </div>
      </div>

      <button
        onClick={onConfirm}
        className="w-full px-3 py-2 text-[12px] font-medium text-white bg-[#3FAF7A] rounded-lg hover:bg-[#25785A] transition-colors flex items-center justify-center gap-1.5"
      >
        <Check className="w-3.5 h-3.5" />
        Confirm Tokens
      </button>
    </div>
  )
}

function SummaryInline({ selection }: { selection: DesignSelection }) {
  const t = selection.tokens
  return (
    <div className="bg-white rounded-lg border border-[#E5E5E5] p-3 space-y-2">
      <div className="flex items-center gap-3 mb-2">
        <div className="flex gap-1">
          {[t.primary_color, t.secondary_color, t.accent_color].map((c, i) => (
            <div key={i} className="w-6 h-6 rounded-full border border-black/10" style={{ backgroundColor: c }} />
          ))}
        </div>
        <span className="text-[11px] text-[#999999]">
          Source: {selection.source === 'brand' ? 'Client Brand' : 'Preset Style'}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px]">
        <div><span className="text-[#999999]">Heading:</span> <span className="text-[#333333]">{t.font_heading}</span></div>
        <div><span className="text-[#999999]">Body:</span> <span className="text-[#333333]">{t.font_body}</span></div>
        <div><span className="text-[#999999]">Spacing:</span> <span className="text-[#333333]">{t.spacing}</span></div>
        <div><span className="text-[#999999]">Corners:</span> <span className="text-[#333333]">{t.corners}</span></div>
      </div>
      {t.logo_url && (
        <div className="pt-1">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={t.logo_url} alt="Logo" className="h-5 max-w-[80px] object-contain" />
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Markdown renderer (simple)
// ============================================================================

function renderMarkdown(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i}>{part.slice(2, -2)}</strong>
    }
    return <span key={i}>{part}</span>
  })
}
