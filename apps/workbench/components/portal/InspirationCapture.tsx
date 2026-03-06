'use client'

import { useState } from 'react'
import { X, Lightbulb, Send } from 'lucide-react'

interface InspirationCaptureProps {
  epicIndex: number | null
  epicTitle?: string
  onSubmit: (text: string) => void
  onClose: () => void
}

export function InspirationCapture({
  epicIndex,
  epicTitle,
  onSubmit,
  onClose,
}: InspirationCaptureProps) {
  const [text, setText] = useState('')

  const handleSubmit = () => {
    const trimmed = text.trim()
    if (!trimmed) return
    onSubmit(trimmed)
    setText('')
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />

      {/* Slide-up panel */}
      <div className="relative w-full max-w-lg bg-surface-card rounded-t-2xl shadow-2xl p-5 pb-8 animate-slide-up">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Lightbulb className="w-5 h-5 text-amber-500" />
            <h3 className="text-base font-semibold text-text-primary">What came to mind?</h3>
          </div>
          <button onClick={onClose} className="text-text-placeholder hover:text-text-secondary">
            <X className="w-5 h-5" />
          </button>
        </div>

        {epicTitle && (
          <p className="text-xs text-text-placeholder mb-3">
            While exploring: {epicTitle}
          </p>
        )}

        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Share your idea, concern, or anything that came to mind..."
          rows={3}
          autoFocus
          className="w-full px-4 py-3 text-sm border border-border rounded-xl focus:ring-2 focus:ring-brand-primary-ring focus:border-brand-primary resize-none"
        />

        <button
          onClick={handleSubmit}
          disabled={!text.trim()}
          className="mt-3 w-full flex items-center justify-center gap-2 px-4 py-3 bg-brand-primary text-white font-medium rounded-xl hover:bg-brand-primary-hover transition-all disabled:opacity-40"
        >
          <Send className="w-4 h-4" />
          Save Idea
        </button>
      </div>
    </div>
  )
}
