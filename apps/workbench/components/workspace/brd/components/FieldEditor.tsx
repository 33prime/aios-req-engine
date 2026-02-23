'use client'

import { useState } from 'react'
import { Pencil, Sparkles, FileText, Check, X, Loader2 } from 'lucide-react'
import { enhanceDriverField } from '@/lib/api'

type EditorMode = 'idle' | 'menu' | 'manual' | 'ai_loading' | 'ai_notes' | 'ai_suggestion'

interface FieldEditorProps {
  fieldName: string
  fieldLabel: string
  currentValue: string | null | undefined
  driverId: string
  projectId: string
  onSave: (value: string) => void
  multiline?: boolean
}

export function FieldEditor({
  fieldName,
  fieldLabel,
  currentValue,
  driverId,
  projectId,
  onSave,
  multiline = false,
}: FieldEditorProps) {
  const [mode, setMode] = useState<EditorMode>('idle')
  const [draft, setDraft] = useState(currentValue || '')
  const [notes, setNotes] = useState('')
  const [suggestion, setSuggestion] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleReset = () => {
    setMode('idle')
    setDraft(currentValue || '')
    setNotes('')
    setSuggestion(null)
    setError(null)
  }

  const handleManualSave = () => {
    onSave(draft)
    handleReset()
  }

  const handleRewriteWithEvidence = async () => {
    setMode('ai_loading')
    setError(null)
    try {
      const result = await enhanceDriverField(projectId, driverId, {
        field_name: fieldName,
        mode: 'rewrite',
      })
      setSuggestion(result.suggestion)
      setMode('ai_suggestion')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Enhancement failed')
      setMode('idle')
    }
  }

  const handleNotesRewrite = async () => {
    if (!notes.trim()) return
    setMode('ai_loading')
    setError(null)
    try {
      const result = await enhanceDriverField(projectId, driverId, {
        field_name: fieldName,
        mode: 'notes',
        user_notes: notes.trim(),
      })
      setSuggestion(result.suggestion)
      setMode('ai_suggestion')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Enhancement failed')
      setMode('ai_notes')
    }
  }

  const handleAcceptSuggestion = () => {
    if (suggestion) {
      onSave(suggestion)
      handleReset()
    }
  }

  const handleEditSuggestion = () => {
    if (suggestion) {
      setDraft(suggestion)
      setMode('manual')
      setSuggestion(null)
    }
  }

  // Idle: show value with hover pencil
  if (mode === 'idle') {
    return (
      <div className="group flex items-start gap-2">
        <div className="flex-1 min-w-0">
          <span className="text-[12px] font-medium text-[#999999] min-w-[120px]">{fieldLabel}</span>
          {currentValue ? (
            <p className="text-[13px] text-[#333333] leading-relaxed mt-0.5">{currentValue}</p>
          ) : (
            <p className="text-[12px] text-[#999999] italic mt-0.5">Not set</p>
          )}
        </div>
        <button
          onClick={() => { setDraft(currentValue || ''); setMode('menu') }}
          className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-[#F0F0F0] flex-shrink-0 mt-0.5"
          title={`Edit ${fieldLabel.toLowerCase()}`}
        >
          <Pencil className="w-3 h-3 text-[#999999]" />
        </button>

        {error && (
          <div className="mt-1 text-[11px] text-red-500">{error}</div>
        )}
      </div>
    )
  }

  // Action menu
  if (mode === 'menu') {
    return (
      <div className="space-y-1">
        <span className="text-[12px] font-medium text-[#999999]">{fieldLabel}</span>
        <div className="border border-[#E5E5E5] rounded-xl overflow-hidden bg-white shadow-sm">
          <button
            onClick={() => { setDraft(currentValue || ''); setMode('manual') }}
            className="w-full text-left px-3 py-2.5 hover:bg-[#FAFAFA] transition-colors border-b border-[#F0F0F0]"
          >
            <div className="flex items-center gap-2">
              <Pencil className="w-3.5 h-3.5 text-[#666666]" />
              <div>
                <div className="text-[12px] font-medium text-[#333333]">Edit manually</div>
                <div className="text-[11px] text-[#999999]">Open a text field to edit directly</div>
              </div>
            </div>
          </button>
          <button
            onClick={handleRewriteWithEvidence}
            className="w-full text-left px-3 py-2.5 hover:bg-[#FAFAFA] transition-colors border-b border-[#F0F0F0]"
          >
            <div className="flex items-center gap-2">
              <Sparkles className="w-3.5 h-3.5 text-[#3FAF7A]" />
              <div>
                <div className="text-[12px] font-medium text-[#333333]">Rewrite with evidence</div>
                <div className="text-[11px] text-[#999999]">AI rewrites using all provenance</div>
              </div>
            </div>
          </button>
          <button
            onClick={() => { setNotes(''); setMode('ai_notes') }}
            className="w-full text-left px-3 py-2.5 hover:bg-[#FAFAFA] transition-colors"
          >
            <div className="flex items-center gap-2">
              <FileText className="w-3.5 h-3.5 text-[#666666]" />
              <div>
                <div className="text-[12px] font-medium text-[#333333]">Add notes & rewrite</div>
                <div className="text-[11px] text-[#999999]">Give direction, AI incorporates it</div>
              </div>
            </div>
          </button>
        </div>
        <button
          onClick={handleReset}
          className="text-[11px] text-[#999999] hover:text-[#666666] transition-colors"
        >
          Cancel
        </button>
      </div>
    )
  }

  // Manual edit
  if (mode === 'manual') {
    const InputComponent = multiline ? 'textarea' : 'input'
    return (
      <div className="space-y-2">
        <span className="text-[12px] font-medium text-[#999999]">{fieldLabel}</span>
        <InputComponent
          value={draft}
          onChange={(e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setDraft(e.target.value)}
          className={`w-full px-3 py-2 text-[13px] text-[#333333] border border-[#E5E5E5] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#3FAF7A]/30 focus:border-[#3FAF7A] ${
            multiline ? 'resize-y min-h-[80px]' : ''
          }`}
          autoFocus
        />
        <div className="flex items-center gap-2">
          <button
            onClick={handleManualSave}
            className="px-3 py-1.5 text-[12px] font-medium text-white bg-[#3FAF7A] rounded-xl hover:bg-[#25785A] transition-colors"
          >
            Save
          </button>
          <button
            onClick={handleReset}
            className="px-3 py-1.5 text-[12px] font-medium text-[#666666] bg-white border border-[#E5E5E5] rounded-xl hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    )
  }

  // AI loading
  if (mode === 'ai_loading') {
    return (
      <div className="space-y-1">
        <span className="text-[12px] font-medium text-[#999999]">{fieldLabel}</span>
        <div className="p-3 border border-[#E5E5E5] rounded-xl bg-[#F4F4F4]">
          <div className="flex items-center gap-2 text-[12px] text-[#666666]">
            <Loader2 className="w-3.5 h-3.5 animate-spin text-[#3FAF7A]" />
            Generating suggestion...
          </div>
        </div>
      </div>
    )
  }

  // Notes input
  if (mode === 'ai_notes') {
    return (
      <div className="space-y-2">
        <span className="text-[12px] font-medium text-[#999999]">{fieldLabel}</span>
        <div>
          <p className="text-[11px] text-[#666666] mb-1.5">What would you like to change?</p>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full px-3 py-2 text-[12px] text-[#333333] border border-[#E5E5E5] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#3FAF7A]/30 focus:border-[#3FAF7A] resize-y min-h-[60px]"
            placeholder="e.g. make it more specific about the Q2 deadline..."
            autoFocus
          />
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleNotesRewrite}
            disabled={!notes.trim()}
            className="px-3 py-1.5 text-[12px] font-medium text-white bg-[#3FAF7A] rounded-xl hover:bg-[#25785A] transition-colors disabled:opacity-50"
          >
            Generate
          </button>
          <button
            onClick={handleReset}
            className="px-3 py-1.5 text-[12px] font-medium text-[#666666] bg-white border border-[#E5E5E5] rounded-xl hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
        </div>
        {error && (
          <div className="text-[11px] text-red-500">{error}</div>
        )}
      </div>
    )
  }

  // AI suggestion display
  if (mode === 'ai_suggestion' && suggestion) {
    return (
      <div className="space-y-2">
        <span className="text-[12px] font-medium text-[#999999]">{fieldLabel}</span>
        <div className="p-4 border border-[#3FAF7A]/30 rounded-xl bg-[#E8F5E9]/30">
          <p className="text-[11px] font-medium text-[#25785A] uppercase tracking-wide mb-2">AI Suggestion</p>
          <p className="text-[13px] text-[#333333] leading-relaxed">{suggestion}</p>
          <div className="mt-3 flex items-center gap-2">
            <button
              onClick={handleAcceptSuggestion}
              className="inline-flex items-center gap-1 px-3 py-1.5 text-[12px] font-medium text-white bg-[#3FAF7A] rounded-xl hover:bg-[#25785A] transition-colors"
            >
              <Check className="w-3 h-3" />
              Accept
            </button>
            <button
              onClick={handleEditSuggestion}
              className="inline-flex items-center gap-1 px-3 py-1.5 text-[12px] font-medium text-[#666666] bg-white border border-[#E5E5E5] rounded-xl hover:bg-gray-50 transition-colors"
            >
              <Pencil className="w-3 h-3" />
              Edit
            </button>
            <button
              onClick={handleReset}
              className="inline-flex items-center gap-1 px-3 py-1.5 text-[12px] font-medium text-[#999999] hover:text-[#666666] transition-colors"
            >
              <X className="w-3 h-3" />
              Dismiss
            </button>
          </div>
        </div>
      </div>
    )
  }

  return null
}
