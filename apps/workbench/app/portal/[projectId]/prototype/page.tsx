'use client'

import { useEffect, useState } from 'react'
import { useParams, useSearchParams } from 'next/navigation'
import PrototypeFrame from '@/components/prototype/PrototypeFrame'
import { getPrototypeClientData, submitPrototypeFeedback } from '@/lib/api'

interface ClientQuestion {
  id: string
  question: string
  category: string
  priority: string
}

/**
 * Client prototype review page — simpler than consultant view.
 *
 * Layout:
 * - Top 65%: PrototypeFrame (iframe)
 * - Bottom 35%: Feedback form with optional per-feature feedback
 */
export default function PortalPrototypePage() {
  const params = useParams()
  const searchParams = useSearchParams()
  const projectId = params.projectId as string
  const token = searchParams.get('token') || ''
  const sessionId = searchParams.get('session') || ''

  const [deployUrl, setDeployUrl] = useState<string | null>(null)
  const [questions, setQuestions] = useState<ClientQuestion[]>([])
  const [feedback, setFeedback] = useState('')
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [submitted, setSubmitted] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Load client data
  useEffect(() => {
    async function load() {
      if (!sessionId || !token) {
        setError('Missing session or token parameter.')
        setLoading(false)
        return
      }
      try {
        const data = await getPrototypeClientData(sessionId, token)
        setDeployUrl(data.deploy_url)
        setQuestions(data.questions)
        setLoading(false)
      } catch {
        setError('Unable to load prototype review. The link may have expired.')
        setLoading(false)
      }
    }
    load()
  }, [sessionId, token])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!sessionId) return

    try {
      // Submit general feedback
      if (feedback.trim()) {
        await submitPrototypeFeedback(sessionId, {
          content: feedback.trim(),
          feedback_type: 'observation',
          priority: 'medium',
        })
      }

      // Submit question answers
      for (const [questionId, answer] of Object.entries(answers)) {
        if (answer.trim()) {
          await submitPrototypeFeedback(sessionId, {
            content: answer.trim(),
            feedback_type: 'answer',
            answers_question_id: questionId,
            priority: 'medium',
          })
        }
      }

      setSubmitted(true)
    } catch {
      setError('Failed to submit feedback. Please try again.')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-ui-background">
        <p className="text-ui-supportText">Loading prototype review...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-ui-background">
        <div className="text-center max-w-md">
          <h2 className="text-h2 text-ui-headingDark mb-2">Review Unavailable</h2>
          <p className="text-body text-ui-bodyText">{error}</p>
        </div>
      </div>
    )
  }

  if (submitted) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-ui-background">
        <div className="text-center max-w-md">
          <h2 className="text-h2 text-ui-headingDark mb-2">Thank You!</h2>
          <p className="text-body text-ui-bodyText">
            Your feedback has been submitted. The team will review it and update the prototype.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-screen bg-ui-background">
      {/* Header */}
      <div className="bg-white border-b border-ui-cardBorder px-6 py-4">
        <h1 className="text-h2 text-ui-headingDark">Prototype Review</h1>
        <p className="text-support text-ui-supportText mt-1">
          Explore the prototype below and share your feedback.
        </p>
      </div>

      {/* Prototype iframe — top 65% */}
      <div className="flex-[65] min-h-0">
        {deployUrl ? (
          <PrototypeFrame
            deployUrl={deployUrl}
            onFeatureClick={() => {}}
            onPageChange={() => {}}
          />
        ) : (
          <div className="flex items-center justify-center h-full text-ui-supportText">
            Prototype preview unavailable
          </div>
        )}
      </div>

      {/* Feedback form — bottom 35% */}
      <div className="flex-[35] border-t border-ui-cardBorder bg-white overflow-y-auto">
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto p-6 space-y-6">
          {/* General feedback */}
          <div>
            <label className="block text-sm font-semibold text-ui-headingDark mb-2">
              Overall Feedback
            </label>
            <textarea
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              rows={3}
              placeholder="What do you think of the prototype? Anything missing or incorrect?"
              className="w-full px-3 py-2 text-sm border border-ui-cardBorder rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary resize-none"
            />
          </div>

          {/* Per-question answers */}
          {questions.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-ui-headingDark mb-3">
                Questions from the Team
              </h3>
              <div className="space-y-4">
                {questions.map((q) => (
                  <div key={q.id}>
                    <label className="block text-sm text-ui-bodyText mb-1">
                      {q.question}
                      {q.priority === 'high' && (
                        <span className="ml-2 text-badge text-brand-primary">(Important)</span>
                      )}
                    </label>
                    <input
                      type="text"
                      value={answers[q.id] || ''}
                      onChange={(e) =>
                        setAnswers((prev) => ({ ...prev, [q.id]: e.target.value }))
                      }
                      placeholder="Your answer..."
                      className="w-full px-3 py-2 text-sm border border-ui-cardBorder rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary"
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          <button
            type="submit"
            className="px-6 py-2.5 bg-brand-primary text-white font-medium rounded-lg hover:bg-[#033344] transition-all duration-200"
          >
            Submit Feedback
          </button>
        </form>
      </div>
    </div>
  )
}
