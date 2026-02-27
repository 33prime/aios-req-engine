'use client'

import { useState, useEffect, useCallback } from 'react'
import type { FeatureOverlay, FeatureVerdict } from '@/types/prototype'
import { submitFeatureVerdict } from '@/lib/api'

interface FeatureVerdictCardProps {
  overlay: FeatureOverlay
  prototypeId: string
  source: 'consultant' | 'client'
  /** For client view: show consultant's verdict + notes */
  consultantContext?: {
    verdict: FeatureVerdict | null
    notes: string | null
  }
  /** Callback after verdict is saved */
  onVerdictSubmit?: (overlayId: string, verdict: FeatureVerdict) => void
}

const VERDICT_OPTIONS: { value: FeatureVerdict; label: string; icon: string }[] = [
  { value: 'aligned', label: 'Aligned', icon: '✓' },
  { value: 'needs_adjustment', label: 'Needs Adjustment', icon: '⚠' },
  { value: 'off_track', label: 'Off Track', icon: '✗' },
]

const VERDICT_STYLES: Record<FeatureVerdict, { button: string; active: string }> = {
  aligned: {
    button: 'border-border hover:border-brand-primary hover:bg-[#E8F5E9]',
    active: 'border-brand-primary bg-[#E8F5E9] text-[#25785A]',
  },
  needs_adjustment: {
    button: 'border-border hover:border-amber-400 hover:bg-amber-50',
    active: 'border-amber-400 bg-amber-50 text-amber-800',
  },
  off_track: {
    button: 'border-border hover:border-red-400 hover:bg-red-50',
    active: 'border-red-400 bg-red-50 text-red-800',
  },
}

const IMPL_STYLES: Record<string, string> = {
  functional: 'bg-[#E8F5E9] text-[#25785A]',
  partial: 'bg-gray-100 text-[#666666]',
  placeholder: 'bg-gray-100 text-text-placeholder',
}

export default function FeatureVerdictCard({
  overlay,
  prototypeId,
  source,
  consultantContext,
  onVerdictSubmit,
}: FeatureVerdictCardProps) {
  const content = overlay.overlay_content
  const existingVerdict = source === 'consultant' ? overlay.consultant_verdict : overlay.client_verdict
  const existingNotes = source === 'consultant' ? overlay.consultant_notes : overlay.client_notes
  const suggestedVerdict = content?.suggested_verdict

  const [selectedVerdict, setSelectedVerdict] = useState<FeatureVerdict | null>(
    existingVerdict || null
  )
  const [notes, setNotes] = useState(existingNotes || '')
  const [showNotes, setShowNotes] = useState(!!existingNotes)
  const [saving, setSaving] = useState(false)
  const [flash, setFlash] = useState(false)

  // Pre-select AI suggestion if no existing verdict
  useEffect(() => {
    if (!existingVerdict && suggestedVerdict && !selectedVerdict) {
      setSelectedVerdict(suggestedVerdict)
    }
  }, [existingVerdict, suggestedVerdict, selectedVerdict])

  const handleVerdictClick = useCallback(async (verdict: FeatureVerdict) => {
    setSelectedVerdict(verdict)
    setSaving(true)
    try {
      await submitFeatureVerdict(prototypeId, overlay.id, verdict, source, notes || undefined)
      setFlash(true)
      setTimeout(() => setFlash(false), 600)
      onVerdictSubmit?.(overlay.id, verdict)
    } catch (err) {
      console.error('Failed to save verdict:', err)
    } finally {
      setSaving(false)
    }
  }, [prototypeId, overlay.id, source, notes, onVerdictSubmit])

  const handleNotesBlur = useCallback(async () => {
    if (!selectedVerdict || notes === (existingNotes || '')) return
    try {
      await submitFeatureVerdict(prototypeId, overlay.id, selectedVerdict, source, notes || undefined)
    } catch (err) {
      console.error('Failed to save notes:', err)
    }
  }, [prototypeId, overlay.id, selectedVerdict, source, notes, existingNotes])

  if (!content) return null

  const gap = content.gaps?.[0]
  const implStatus = content.overview?.implementation_status

  return (
    <div
      className={`rounded-2xl border bg-white shadow-md transition-all duration-300 ${
        flash ? 'border-brand-primary shadow-brand-primary/20' : 'border-border'
      }`}
    >
      {/* Header */}
      <div className="px-5 py-4 border-b border-border">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-text-body truncate">
              {content.feature_name}
            </h3>
            <div className="flex items-center gap-2 mt-1">
              {implStatus && (
                <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${IMPL_STYLES[implStatus] || IMPL_STYLES.placeholder}`}>
                  {implStatus}
                </span>
              )}
              <span className="text-[11px] text-text-placeholder">
                {Math.round((content.confidence ?? 0) * 100)}% confidence
              </span>
            </div>
          </div>
          {suggestedVerdict && (
            <span className="text-[10px] text-text-placeholder whitespace-nowrap">
              AI: {suggestedVerdict.replace('_', ' ')}
            </span>
          )}
        </div>
      </div>

      {/* Consultant context (client view only) */}
      {consultantContext?.verdict && (
        <div className="px-5 py-3 border-b border-border bg-[#F4F4F4]">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[11px] font-medium text-[#666666] uppercase tracking-wide">
              Consultant says:
            </span>
            <span className={`text-[11px] font-semibold ${
              consultantContext.verdict === 'aligned' ? 'text-[#25785A]' :
              consultantContext.verdict === 'needs_adjustment' ? 'text-amber-700' :
              'text-red-700'
            }`}>
              {consultantContext.verdict === 'aligned' ? '✓ Aligned' :
               consultantContext.verdict === 'needs_adjustment' ? '⚠ Needs Adjustment' :
               '✗ Off Track'}
            </span>
          </div>
          {consultantContext.notes && (
            <p className="text-xs text-[#666666] leading-relaxed">
              {consultantContext.notes}
            </p>
          )}
        </div>
      )}

      {/* Verdict buttons */}
      <div className="px-5 py-3 border-b border-border">
        <p className="text-[11px] font-medium text-[#666666] uppercase tracking-wide mb-2">
          Your Verdict
        </p>
        <div className="flex gap-2">
          {VERDICT_OPTIONS.map(({ value, label, icon }) => {
            const isActive = selectedVerdict === value
            const styles = VERDICT_STYLES[value]
            return (
              <button
                key={value}
                onClick={() => handleVerdictClick(value)}
                disabled={saving}
                className={`flex-1 px-3 py-2 rounded-xl border text-xs font-medium transition-all duration-200 ${
                  isActive ? styles.active : styles.button
                } disabled:opacity-60`}
              >
                <span className="mr-1">{icon}</span>
                {label}
              </button>
            )
          })}
        </div>
      </div>

      {/* Validation question */}
      {gap && (
        <div className="px-5 py-3 border-b border-border">
          <p className="text-[11px] font-medium text-[#666666] uppercase tracking-wide mb-2">
            Key Question
          </p>
          <p className="text-sm text-text-body leading-relaxed">
            &ldquo;{gap.question}&rdquo;
          </p>
          <div className="flex items-center gap-2 mt-1.5">
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#F0F0F0] text-[#666666]">
              {gap.requirement_area.replace('_', ' ')}
            </span>
            {gap.why_it_matters && (
              <span className="text-[10px] text-text-placeholder italic truncate">
                {gap.why_it_matters}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Notes */}
      <div className="px-5 py-3">
        {showNotes ? (
          <div>
            <p className="text-[11px] font-medium text-[#666666] uppercase tracking-wide mb-2">
              Notes <span className="font-normal normal-case">(optional)</span>
            </p>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              onBlur={handleNotesBlur}
              rows={2}
              placeholder="Anything else about this feature..."
              className="w-full px-3 py-2 text-sm border border-border rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary resize-none text-text-body placeholder:text-text-placeholder"
            />
          </div>
        ) : (
          <button
            onClick={() => setShowNotes(true)}
            className="text-xs text-text-placeholder hover:text-[#666666] transition-colors"
          >
            + Add notes
          </button>
        )}
      </div>
    </div>
  )
}
