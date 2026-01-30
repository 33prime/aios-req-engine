/**
 * Client Portal Page
 *
 * Shows the AI-synthesized questions and action items for clients to respond to.
 * Minimal, focused UI optimized for quick client responses.
 */

'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { useParams } from 'next/navigation'
import {
  Loader2,
  AlertCircle,
  MessageSquare,
  FileText,
  CheckCircle2,
  Lightbulb,
  User,
  Upload,
  ChevronDown,
  ChevronUp,
  Sparkles,
} from 'lucide-react'

interface PackageQuestion {
  id: string
  question_text: string
  hint?: string
  suggested_answerer?: string
  covers_summary?: string
  answer_text?: string
  answered_by?: string
  answered_by_name?: string
  answered_at?: string
}

interface ActionItem {
  id: string
  title: string
  description?: string
  item_type: string
  hint?: string
  status?: string
  uploaded_files?: Array<{
    id: string
    file_name: string
  }>
}

interface AssetSuggestion {
  id: string
  category: string
  title: string
  description: string
  why_valuable: string
  examples: string[]
  priority: string
}

interface ClientPackage {
  id: string
  status: string
  sent_at: string
  questions: PackageQuestion[]
  action_items: ActionItem[]
  suggested_assets?: AssetSuggestion[]
  progress: {
    questions_total: number
    questions_answered: number
    items_total: number
    items_completed: number
    overall_percent: number
  }
}

export default function PortalPage() {
  const params = useParams()
  const projectId = params.projectId as string

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [package_, setPackage] = useState<ClientPackage | null>(null)
  const [projectName, setProjectName] = useState('Project')

  // Active question for answering
  const [activeQuestionId, setActiveQuestionId] = useState<string | null>(null)
  const [answerText, setAnswerText] = useState('')
  const [submitting, setSubmitting] = useState(false)

  // Show assets section
  const [showAssets, setShowAssets] = useState(false)

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      // Get active package
      const response = await fetch(`/api/v1/collaboration/portal/projects/${projectId}/active-package`)
      if (!response.ok) {
        throw new Error('Failed to load package')
      }

      const data = await response.json()
      setPackage(data.package)

      // Get project name
      const projectResponse = await fetch(`/api/v1/portal/projects/${projectId}`)
      if (projectResponse.ok) {
        const projectData = await projectResponse.json()
        setProjectName(projectData.client_display_name || projectData.name || 'Project')
      }
    } catch (err: unknown) {
      console.error('Failed to load portal data:', err)
      setError(err instanceof Error ? err.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    loadData()
  }, [loadData])

  // Submit answer handler
  const handleSubmitAnswer = async (questionId: string) => {
    if (!answerText.trim()) return

    try {
      setSubmitting(true)
      const response = await fetch(`/api/v1/collaboration/portal/questions/${questionId}/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ answer_text: answerText }),
      })

      if (!response.ok) {
        throw new Error('Failed to submit answer')
      }

      // Refresh data
      await loadData()
      setActiveQuestionId(null)
      setAnswerText('')
    } catch (err: unknown) {
      console.error('Failed to submit:', err)
      alert(err instanceof Error ? err.message : 'Failed to submit answer')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-[#009b87] mx-auto mb-3" />
          <p className="text-gray-500">Loading your questions...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <AlertCircle className="w-10 h-10 text-red-400 mx-auto mb-3" />
          <p className="text-red-600">{error}</p>
        </div>
      </div>
    )
  }

  if (!package_) {
    return (
      <div className="text-center py-16">
        <MessageSquare className="w-12 h-12 text-gray-300 mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-gray-900 mb-2">No Questions Yet</h2>
        <p className="text-gray-500 max-w-md mx-auto">
          Your consultant hasn't sent any questions yet. Check back later or reach out
          to them directly.
        </p>
      </div>
    )
  }

  const { progress } = package_

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">{projectName}</h1>
        <p className="text-gray-600">
          Please answer the questions below to help us understand your needs better.
        </p>
      </div>

      {/* Progress */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-gray-900">Your Progress</h2>
          <span className="text-2xl font-bold text-[#009b87]">{progress.overall_percent}%</span>
        </div>
        <div className="w-full h-3 bg-gray-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-[#009b87] rounded-full transition-all duration-500"
            style={{ width: `${progress.overall_percent}%` }}
          />
        </div>
        <div className="flex items-center justify-between mt-4 text-sm text-gray-500">
          <span>
            {progress.questions_answered} of {progress.questions_total} questions answered
          </span>
          <span>
            {progress.items_completed} of {progress.items_total} items completed
          </span>
        </div>
      </div>

      {/* Questions Section */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <MessageSquare className="w-5 h-5 text-[#009b87]" />
          Questions ({package_.questions.length})
        </h2>

        {package_.questions.map((question, index) => {
          const isAnswered = !!question.answer_text
          const isActive = activeQuestionId === question.id
          const existingAnswer = question.answer_text || ''

          return (
            <div
              key={question.id}
              className={`bg-white rounded-xl border ${
                isAnswered ? 'border-green-200 bg-green-50/50' : 'border-gray-200'
              } p-6`}
            >
              <div className="flex items-start gap-4">
                {/* Number */}
                <span
                  className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                    isAnswered
                      ? 'bg-green-500 text-white'
                      : 'bg-[#009b87] text-white'
                  }`}
                >
                  {isAnswered ? <CheckCircle2 className="w-5 h-5" /> : index + 1}
                </span>

                <div className="flex-1">
                  {/* Question text */}
                  <p className="text-gray-900 font-medium text-lg mb-3">
                    {question.question_text}
                  </p>

                  {/* Hint */}
                  {question.hint && (
                    <div className="flex items-start gap-2 text-sm text-gray-600 mb-3 p-3 bg-amber-50 rounded-lg border border-amber-100">
                      <Lightbulb className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
                      <span>{question.hint}</span>
                    </div>
                  )}

                  {/* Suggested answerer */}
                  {question.suggested_answerer && (
                    <div className="flex items-center gap-2 text-sm text-gray-500 mb-4">
                      <User className="w-4 h-4 text-gray-400" />
                      <span>Best answered by: {question.suggested_answerer}</span>
                    </div>
                  )}

                  {/* Existing answer or answer form */}
                  {isAnswered && !isActive ? (
                    <div className="mt-4 p-4 bg-white rounded-lg border border-green-200">
                      <p className="text-sm text-gray-500 mb-1">Your answer:</p>
                      <p className="text-gray-900">{existingAnswer}</p>
                      <button
                        onClick={() => {
                          setActiveQuestionId(question.id)
                          setAnswerText(existingAnswer)
                        }}
                        className="mt-3 text-sm text-[#009b87] hover:underline"
                      >
                        Edit answer
                      </button>
                    </div>
                  ) : isActive ? (
                    <div className="mt-4">
                      <textarea
                        value={answerText}
                        onChange={(e) => setAnswerText(e.target.value)}
                        placeholder="Type your answer here..."
                        rows={4}
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#009b87] focus:border-transparent resize-none"
                        autoFocus
                      />
                      <div className="flex items-center justify-end gap-3 mt-3">
                        <button
                          onClick={() => {
                            setActiveQuestionId(null)
                            setAnswerText('')
                          }}
                          className="px-4 py-2 text-gray-600 hover:text-gray-800"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={() => handleSubmitAnswer(question.id)}
                          disabled={submitting || !answerText.trim()}
                          className="px-6 py-2 bg-[#009b87] text-white font-medium rounded-lg hover:bg-[#008775] disabled:opacity-50"
                        >
                          {submitting ? 'Saving...' : 'Save Answer'}
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => setActiveQuestionId(question.id)}
                      className="mt-4 w-full py-3 border-2 border-dashed border-gray-300 rounded-lg text-gray-500 hover:border-[#009b87] hover:text-[#009b87] transition-colors"
                    >
                      Click to answer this question
                    </button>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Action Items Section */}
      {package_.action_items.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <FileText className="w-5 h-5 text-[#009b87]" />
            Documents & Files ({package_.action_items.length})
          </h2>

          {package_.action_items.map((item) => {
            const isComplete = item.status === 'complete' || (item.uploaded_files && item.uploaded_files.length > 0)
            const hasFiles = item.uploaded_files && item.uploaded_files.length > 0

            return (
              <div
                key={item.id}
                className={`bg-white rounded-xl border ${
                  isComplete ? 'border-green-200 bg-green-50/50' : 'border-gray-200'
                } p-6`}
              >
                <div className="flex items-start gap-4">
                  <div
                    className={`p-2 rounded-lg ${
                      isComplete ? 'bg-green-100' : 'bg-gray-100'
                    }`}
                  >
                    {isComplete ? (
                      <CheckCircle2 className="w-5 h-5 text-green-600" />
                    ) : (
                      <FileText className="w-5 h-5 text-gray-500" />
                    )}
                  </div>

                  <div className="flex-1">
                    <p className="font-medium text-gray-900">{item.title}</p>
                    {item.description && (
                      <p className="text-sm text-gray-600 mt-1">{item.description}</p>
                    )}
                    {item.hint && (
                      <p className="text-sm text-gray-500 mt-2 italic">{item.hint}</p>
                    )}

                    {/* Uploaded files */}
                    {hasFiles && (
                      <div className="mt-3 space-y-2">
                        {item.uploaded_files!.map((file) => (
                          <div
                            key={file.id}
                            className="flex items-center gap-2 text-sm text-green-700"
                          >
                            <CheckCircle2 className="w-4 h-4" />
                            {file.file_name}
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Upload button */}
                    {!isComplete && (
                      <button
                        className="mt-4 inline-flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
                        onClick={() => alert('File upload coming soon!')}
                      >
                        <Upload className="w-4 h-4" />
                        Upload File
                      </button>
                    )}
                  </div>

                  <span
                    className={`text-xs px-2 py-1 rounded-full ${
                      item.item_type === 'document'
                        ? 'bg-blue-100 text-blue-700'
                        : 'bg-gray-100 text-gray-600'
                    }`}
                  >
                    {item.item_type}
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Asset Suggestions (Optional - Collapsible) */}
      {package_.suggested_assets && package_.suggested_assets.length > 0 && (
        <div className="bg-amber-50 rounded-xl border border-amber-100 p-6">
          <button
            onClick={() => setShowAssets(!showAssets)}
            className="w-full flex items-center justify-between"
          >
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-amber-500" />
              <span className="font-semibold text-gray-900">
                Helpful Assets ({package_.suggested_assets.length})
              </span>
              <span className="text-sm text-gray-500">
                - Optional items that would help us build better for you
              </span>
            </div>
            {showAssets ? (
              <ChevronUp className="w-5 h-5 text-gray-400" />
            ) : (
              <ChevronDown className="w-5 h-5 text-gray-400" />
            )}
          </button>

          {showAssets && (
            <div className="mt-4 space-y-3">
              {package_.suggested_assets.map((asset) => (
                <div key={asset.id} className="bg-white rounded-lg p-4 border border-amber-200">
                  <div className="flex items-start justify-between mb-2">
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full ${
                        asset.priority === 'high'
                          ? 'bg-red-100 text-red-700'
                          : 'bg-amber-100 text-amber-700'
                      }`}
                    >
                      {asset.priority} priority
                    </span>
                    <span className="text-xs text-gray-500">
                      {asset.category.replace('_', ' ')}
                    </span>
                  </div>
                  <p className="font-medium text-gray-900">{asset.title}</p>
                  <p className="text-sm text-gray-600 mt-1">{asset.description}</p>
                  <p className="text-sm text-amber-700 mt-2 flex items-center gap-1">
                    <Sparkles className="w-3.5 h-3.5" />
                    {asset.why_valuable}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Completion message */}
      {progress.overall_percent === 100 && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-6 text-center">
          <CheckCircle2 className="w-12 h-12 text-green-500 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-green-800 mb-2">All Done!</h3>
          <p className="text-green-700">
            Thank you for completing all the questions. Your consultant will review
            your responses and follow up soon.
          </p>
        </div>
      )}
    </div>
  )
}
