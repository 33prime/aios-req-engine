'use client'

import { useState, useMemo } from 'react'
import { Pencil, Sparkles, FileText, Check, X, Loader2, Copy, ChevronDown } from 'lucide-react'
import { enhanceNarrative } from '@/lib/api'
import { Markdown } from '@/components/ui/Markdown'

type EditorMode = 'idle' | 'menu' | 'manual' | 'ai_loading' | 'ai_notes' | 'ai_suggestion'

const NARRATIVE_MD = [
  'text-[14px] text-[#444444] leading-[1.7]',
  '[&_p]:mb-2.5 [&_p:last-child]:mb-0',
  '[&_strong]:text-[#1a1a1a] [&_strong]:font-semibold',
  '[&_em]:text-[#555555]',
  '[&_ul]:mt-1.5 [&_ul]:mb-2 [&_ul]:ml-1 [&_ul]:space-y-1',
  '[&_ol]:mt-1.5 [&_ol]:mb-2 [&_ol]:ml-1 [&_ol]:space-y-1',
  '[&_li]:text-[13.5px] [&_li]:leading-[1.65]',
].join(' ')

/** Truncate markdown to ~first N lines for collapsed preview. */
function truncateMarkdown(md: string, maxLines = 4): { truncated: string; wasTruncated: boolean } {
  const lines = md.split('\n').filter((l) => l.trim() !== '')
  if (lines.length <= maxLines) return { truncated: md, wasTruncated: false }
  return { truncated: lines.slice(0, maxLines).join('\n'), wasTruncated: true }
}

interface NarrativeEditorProps {
  field: 'vision' | 'background' | 'macro_outcome' | 'outcome_thesis'
  label: string
  currentValue: string | null | undefined
  projectId: string
  onSave: (value: string) => void
  placeholder?: string
  companyMeta?: { name?: string; industry?: string | null } | null
}

export function NarrativeEditor({
  field,
  label,
  currentValue,
  projectId,
  onSave,
  placeholder,
  companyMeta,
}: NarrativeEditorProps) {
  const [mode, setMode] = useState<EditorMode>('idle')
  const [draft, setDraft] = useState(currentValue || '')
  const [notes, setNotes] = useState('')
  const [suggestion, setSuggestion] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [expanded, setExpanded] = useState(false)

  const { truncated, wasTruncated } = useMemo(
    () => (currentValue ? truncateMarkdown(currentValue) : { truncated: '', wasTruncated: false }),
    [currentValue]
  )

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
      const result = await enhanceNarrative(projectId, {
        field,
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
      const result = await enhanceNarrative(projectId, {
        field,
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

  const handleCopy = async () => {
    if (!currentValue) return
    try {
      await navigator.clipboard.writeText(currentValue)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      const textarea = document.createElement('textarea')
      textarea.value = currentValue
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    }
  }

  // ── Idle: show value with expand/collapse + hover actions ──
  if (mode === 'idle') {
    const displayContent = expanded || !wasTruncated ? currentValue : truncated

    return (
      <div className="group">
        {companyMeta?.name && (
          <p className="text-[14px] font-medium text-text-body mb-1">
            {companyMeta.name}
            {companyMeta.industry && (
              <span className="text-[#666666] font-normal"> &mdash; {companyMeta.industry}</span>
            )}
          </p>
        )}

        {displayContent ? (
          <div className="relative">
            <Markdown content={displayContent} className={NARRATIVE_MD} />
            {/* Fade overlay when collapsed */}
            {wasTruncated && !expanded && (
              <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-white to-transparent pointer-events-none" />
            )}
          </div>
        ) : (
          <p className="text-[13px] text-text-placeholder italic">{placeholder}</p>
        )}

        {/* Expand/collapse + actions row */}
        <div className="mt-1.5 flex items-center gap-1">
          {wasTruncated && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="inline-flex items-center gap-0.5 px-2 py-1 text-[12px] text-brand-primary hover:bg-surface-page rounded-lg transition-colors"
            >
              <ChevronDown className={`w-3 h-3 transition-transform ${expanded ? 'rotate-180' : ''}`} />
              {expanded ? 'Show less' : 'Show more'}
            </button>
          )}
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={() => { setDraft(currentValue || ''); setMode('menu') }}
              className="inline-flex items-center gap-1 px-2 py-1 text-[12px] text-text-placeholder hover:text-brand-primary hover:bg-surface-page rounded-lg transition-colors"
            >
              <Pencil className="w-3 h-3" />
              Edit
            </button>
            {currentValue && (
              <button
                onClick={handleCopy}
                className="inline-flex items-center gap-1 px-2 py-1 text-[12px] text-text-placeholder hover:text-brand-primary hover:bg-surface-page rounded-lg transition-colors"
              >
                {copied ? (
                  <>
                    <Check className="w-3 h-3 text-brand-primary" />
                    <span className="text-brand-primary">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3 h-3" />
                    Copy
                  </>
                )}
              </button>
            )}
          </div>
        </div>

        {error && <div className="mt-2 text-[11px] text-red-500">{error}</div>}
      </div>
    )
  }

  // ── Action menu ──
  if (mode === 'menu') {
    return (
      <div className="space-y-1">
        <div className="border border-border rounded-xl overflow-hidden bg-white shadow-sm">
          <button
            onClick={() => { setDraft(currentValue || ''); setMode('manual') }}
            className="w-full text-left px-3 py-2.5 hover:bg-surface-page transition-colors border-b border-[#F0F0F0]"
          >
            <div className="flex items-center gap-2">
              <Pencil className="w-3.5 h-3.5 text-[#666666]" />
              <div>
                <div className="text-[12px] font-medium text-text-body">Edit manually</div>
                <div className="text-[11px] text-text-placeholder">Open a text field to edit directly</div>
              </div>
            </div>
          </button>
          <button
            onClick={handleRewriteWithEvidence}
            className="w-full text-left px-3 py-2.5 hover:bg-surface-page transition-colors border-b border-[#F0F0F0]"
          >
            <div className="flex items-center gap-2">
              <Sparkles className="w-3.5 h-3.5 text-brand-primary" />
              <div>
                <div className="text-[12px] font-medium text-text-body">Rewrite with evidence</div>
                <div className="text-[11px] text-text-placeholder">AI rewrites using all provenance</div>
              </div>
            </div>
          </button>
          <button
            onClick={() => { setNotes(''); setMode('ai_notes') }}
            className="w-full text-left px-3 py-2.5 hover:bg-surface-page transition-colors"
          >
            <div className="flex items-center gap-2">
              <FileText className="w-3.5 h-3.5 text-[#666666]" />
              <div>
                <div className="text-[12px] font-medium text-text-body">Add notes & rewrite</div>
                <div className="text-[11px] text-text-placeholder">Give direction, AI incorporates it</div>
              </div>
            </div>
          </button>
        </div>
        <button onClick={handleReset} className="text-[11px] text-text-placeholder hover:text-[#666666] transition-colors">
          Cancel
        </button>
      </div>
    )
  }

  // ── Manual edit ──
  if (mode === 'manual') {
    return (
      <div className="space-y-2">
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          className="w-full px-3 py-2 text-[14px] text-text-body border border-border rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-primary/30 focus:border-brand-primary resize-y min-h-[100px]"
          placeholder={placeholder || `Describe the ${label.toLowerCase()}...`}
          autoFocus
        />
        <p className="text-[10px] text-text-placeholder">Supports markdown: **bold**, *italic*, - bullet points</p>
        <div className="flex items-center gap-2">
          <button onClick={handleManualSave} className="px-3 py-1.5 text-[12px] font-medium text-white bg-brand-primary rounded-xl hover:bg-[#25785A] transition-colors">
            Save
          </button>
          <button onClick={handleReset} className="px-3 py-1.5 text-[12px] font-medium text-[#666666] bg-white border border-border rounded-xl hover:bg-gray-50 transition-colors">
            Cancel
          </button>
        </div>
      </div>
    )
  }

  // ── AI loading ──
  if (mode === 'ai_loading') {
    return (
      <div className="p-3 border border-border rounded-xl bg-[#F4F4F4]">
        <div className="flex items-center gap-2 text-[12px] text-[#666666]">
          <Loader2 className="w-3.5 h-3.5 animate-spin text-brand-primary" />
          Generating suggestion...
        </div>
      </div>
    )
  }

  // ── Notes input ──
  if (mode === 'ai_notes') {
    return (
      <div className="space-y-2">
        <div>
          <p className="text-[11px] text-[#666666] mb-1.5">What would you like to change?</p>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full px-3 py-2 text-[12px] text-text-body border border-border rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-primary/30 focus:border-brand-primary resize-y min-h-[60px]"
            placeholder="e.g. emphasize the compliance angle more, make it longer..."
            autoFocus
          />
        </div>
        <div className="flex items-center gap-2">
          <button onClick={handleNotesRewrite} disabled={!notes.trim()} className="px-3 py-1.5 text-[12px] font-medium text-white bg-brand-primary rounded-xl hover:bg-[#25785A] transition-colors disabled:opacity-50">
            Generate
          </button>
          <button onClick={handleReset} className="px-3 py-1.5 text-[12px] font-medium text-[#666666] bg-white border border-border rounded-xl hover:bg-gray-50 transition-colors">
            Cancel
          </button>
        </div>
        {error && <div className="text-[11px] text-red-500">{error}</div>}
      </div>
    )
  }

  // ── AI suggestion display ──
  if (mode === 'ai_suggestion' && suggestion) {
    return (
      <div className="space-y-2">
        <div className="p-4 border border-brand-primary/30 rounded-xl bg-[#E8F5E9]/20">
          <p className="text-[11px] font-medium text-[#25785A] uppercase tracking-wide mb-2">AI Suggestion</p>
          <Markdown content={suggestion} className={NARRATIVE_MD} />
          <div className="mt-3 flex items-center gap-2">
            <button onClick={handleAcceptSuggestion} className="inline-flex items-center gap-1 px-3 py-1.5 text-[12px] font-medium text-white bg-brand-primary rounded-xl hover:bg-[#25785A] transition-colors">
              <Check className="w-3 h-3" />
              Accept
            </button>
            <button onClick={handleEditSuggestion} className="inline-flex items-center gap-1 px-3 py-1.5 text-[12px] font-medium text-[#666666] bg-white border border-border rounded-xl hover:bg-gray-50 transition-colors">
              <Pencil className="w-3 h-3" />
              Edit
            </button>
            <button onClick={handleReset} className="inline-flex items-center gap-1 px-3 py-1.5 text-[12px] font-medium text-text-placeholder hover:text-[#666666] transition-colors">
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
