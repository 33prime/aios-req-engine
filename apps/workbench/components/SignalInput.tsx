'use client'

import { useState } from 'react'
import { FileText, Upload, MessageSquare, Globe } from 'lucide-react'

interface SignalInputProps {
  projectId: string
  onSignalAdded?: () => void
}

type SignalType = 'email' | 'transcript' | 'file_text' | 'note'

export default function SignalInput({ projectId, onSignalAdded }: SignalInputProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [signalType, setSignalType] = useState<SignalType>('email')
  const [source, setSource] = useState('')
  const [rawText, setRawText] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const signalTypeOptions = [
    { value: 'email', label: 'Client Email', icon: MessageSquare },
    { value: 'transcript', label: 'Meeting Transcript', icon: MessageSquare },
    { value: 'file_text', label: 'Document Text', icon: FileText },
    { value: 'note', label: 'Meeting Notes', icon: FileText },
  ]

  const isResearchSignal = rawText.toLowerCase().includes('research') ||
                          rawText.toLowerCase().includes('study') ||
                          rawText.toLowerCase().includes('analysis')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!rawText.trim() || !source.trim()) return

    setIsSubmitting(true)
    try {
      console.log('📤 Submitting signal:', { signalType, source, textLength: rawText.length })

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}/v1/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          signal_type: signalType,
          source: source,
          raw_text: rawText,
          metadata: {
            authority: isResearchSignal ? 'research' : 'client',
            submitted_via: 'workbench_ui',
            signal_category: signalType,
            auto_detected_research: isResearchSignal
          }
        })
      })

      if (!response.ok) {
        const error = await response.text()
        throw new Error(`Failed to add signal: ${error}`)
      }

      const result = await response.json()
      console.log('✅ Signal added successfully:', result)

      const researchNote = isResearchSignal ? ' (Research signal detected)' : ''
      alert(`Signal added successfully! Created ${result.chunks_inserted} chunks.${researchNote}`)

      // Reset form
      setRawText('')
      setSource('')
      setIsOpen(false)

      // Notify parent
      onSignalAdded?.()
    } catch (error) {
      console.error('❌ Failed to add signal:', error)
      alert(`Failed to add signal: ${error}`)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="mb-8">
      {!isOpen ? (
        <button
          onClick={() => setIsOpen(true)}
          className="btn btn-primary flex items-center"
        >
          <Upload className="h-4 w-4 mr-2" />
          Add New Signal
        </button>
      ) : (
        <div className="card">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-gray-900">Add New Signal</h3>
            <button
              onClick={() => setIsOpen(false)}
              className="text-gray-400 hover:text-gray-600"
            >
              ✕
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Signal Type
              </label>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {signalTypeOptions.map((option) => {
                  const Icon = option.icon
                  return (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => setSignalType(option.value as SignalType)}
                      className={`p-3 border rounded-lg text-sm font-medium flex items-center justify-center space-x-2 ${
                        signalType === option.value
                          ? 'border-blue-500 bg-blue-50 text-blue-700'
                          : 'border-gray-300 hover:border-gray-400'
                      }`}
                    >
                      <Icon className="h-4 w-4" />
                      <span>{option.label}</span>
                    </button>
                  )
                })}
              </div>
            </div>

            <div>
              <label htmlFor="source" className="block text-sm font-medium text-gray-700 mb-2">
                Source
              </label>
              <input
                type="text"
                id="source"
                value={source}
                onChange={(e) => setSource(e.target.value)}
                placeholder="e.g., Email from John Doe, Meeting with Client XYZ"
                className="input"
                required
              />
            </div>

            <div>
              <label htmlFor="rawText" className="block text-sm font-medium text-gray-700 mb-2">
                Content
              </label>
              <textarea
                id="rawText"
                value={rawText}
                onChange={(e) => setRawText(e.target.value)}
                placeholder="Paste the email content, meeting transcript, document text, or research findings here..."
                className="input h-48 resize-none"
                required
              />
              <div className="flex items-center justify-between mt-2">
                <span className="text-sm text-gray-500">
                  {rawText.length} characters
                </span>
                {isResearchSignal && (
                  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                    🔬 Research Detected
                  </span>
                )}
              </div>
            </div>

            <div className="flex justify-end space-x-3">
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                className="btn btn-secondary"
                disabled={isSubmitting}
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting || !rawText.trim() || !source.trim()}
                className="btn btn-primary"
              >
                {isSubmitting ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                ) : (
                  <Upload className="h-4 w-4 mr-2" />
                )}
                Add Signal
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
