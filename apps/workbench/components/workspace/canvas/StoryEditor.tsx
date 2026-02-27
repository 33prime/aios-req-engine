/**
 * StoryEditor - Editable pitch line / story
 *
 * "Building X for Y to achieve Z"
 * Click to edit, blur or Enter to save.
 */

'use client'

import { useState, useRef, useEffect } from 'react'
import { Edit3, Check, X } from 'lucide-react'

interface StoryEditorProps {
  pitchLine: string
  onSave: (pitchLine: string) => Promise<void>
}

export function StoryEditor({ pitchLine, onSave }: StoryEditorProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [value, setValue] = useState(pitchLine)
  const [isSaving, setIsSaving] = useState(false)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    setValue(pitchLine)
  }, [pitchLine])

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [isEditing])

  const handleSave = async () => {
    if (value === pitchLine) {
      setIsEditing(false)
      return
    }

    setIsSaving(true)
    try {
      await onSave(value)
      setIsEditing(false)
    } catch (error) {
      console.error('Failed to save pitch line:', error)
      setValue(pitchLine)
    } finally {
      setIsSaving(false)
    }
  }

  const handleCancel = () => {
    setValue(pitchLine)
    setIsEditing(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSave()
    } else if (e.key === 'Escape') {
      handleCancel()
    }
  }

  if (isEditing) {
    return (
      <div className="bg-white rounded-lg border border-border shadow-sm p-6">
        <label className="block text-[12px] font-medium text-text-placeholder mb-2">
          The Story
        </label>
        <div className="relative">
          <textarea
            ref={inputRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={handleSave}
            placeholder="Building [what] for [who] to achieve [goal]..."
            className="w-full text-xl font-medium text-text-body bg-surface-muted border border-border rounded-lg p-4 resize-none focus:outline-none focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary"
            rows={2}
            disabled={isSaving}
          />
          <div className="absolute right-2 bottom-2 flex items-center gap-1">
            <button
              onClick={handleCancel}
              className="p-1.5 text-text-placeholder hover:text-text-body rounded transition-colors"
              disabled={isSaving}
            >
              <X className="w-4 h-4" />
            </button>
            <button
              onClick={handleSave}
              className="p-1.5 text-brand-primary hover:bg-brand-primary-light rounded transition-colors"
              disabled={isSaving}
            >
              <Check className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div
      onClick={() => setIsEditing(true)}
      className="bg-white rounded-lg border border-border shadow-sm p-6 cursor-pointer hover:border-brand-primary/30 hover:shadow-md transition-all group"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <label className="block text-[12px] font-medium text-text-placeholder mb-2">
            The Story
          </label>
          {pitchLine ? (
            <p className="text-xl font-medium text-text-body">{pitchLine}</p>
          ) : (
            <p className="text-xl font-medium text-text-placeholder italic">
              Click to add your pitch line...
            </p>
          )}
        </div>
        <Edit3 className="w-4 h-4 text-text-placeholder opacity-0 group-hover:opacity-100 transition-opacity mt-1" />
      </div>
    </div>
  )
}

export default StoryEditor
