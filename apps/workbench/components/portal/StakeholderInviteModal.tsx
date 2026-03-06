'use client'

import { useState } from 'react'
import { X, Send, Users, UserPlus } from 'lucide-react'
import { shareWithStakeholder } from '@/lib/api/portal'

interface StakeholderInviteModalProps {
  projectId: string
  sessionId: string
  onClose: () => void
}

export function StakeholderInviteModal({
  sessionId,
  onClose,
}: StakeholderInviteModalProps) {
  const [mode, setMode] = useState<'new'>('new')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [email, setEmail] = useState('')
  const [focusQuestion, setFocusQuestion] = useState('')
  const [sending, setSending] = useState(false)
  const [sent, setSent] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async () => {
    if (!email.trim()) return
    setSending(true)
    setError(null)

    try {
      await shareWithStakeholder(sessionId, {
        email: email.trim(),
        first_name: firstName.trim() || undefined,
        last_name: lastName.trim() || undefined,
        focus_question: focusQuestion.trim() || undefined,
      })
      setSent(true)
    } catch (err) {
      setError((err as Error).message || 'Failed to send invite')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h2 className="text-base font-semibold text-text-primary">Share with a Colleague</h2>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-surface-subtle transition-colors text-text-muted"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="px-6 py-4">
          {sent ? (
            <div className="text-center py-6">
              <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-green-50 flex items-center justify-center">
                <Send className="w-5 h-5 text-green-600" />
              </div>
              <h3 className="text-sm font-semibold text-text-primary mb-1">Invite Sent!</h3>
              <p className="text-xs text-text-muted">
                They&apos;ll receive an email with a link to explore the prototype.
              </p>
              <button
                onClick={onClose}
                className="mt-4 px-4 py-2 text-sm font-medium text-brand-primary hover:bg-brand-primary/5 rounded-lg transition-colors"
              >
                Done
              </button>
            </div>
          ) : (
            <>
              {/* Add someone new */}
              <div className="space-y-3">
                <div className="flex gap-2">
                  <div className="flex-1">
                    <label className="text-[11px] font-medium text-text-muted uppercase tracking-wide">First Name</label>
                    <input
                      value={firstName}
                      onChange={(e) => setFirstName(e.target.value)}
                      placeholder="Jane"
                      className="w-full mt-1 px-3 py-2 text-sm border border-border rounded-lg focus:ring-2 focus:ring-brand-primary-ring focus:border-brand-primary"
                    />
                  </div>
                  <div className="flex-1">
                    <label className="text-[11px] font-medium text-text-muted uppercase tracking-wide">Last Name</label>
                    <input
                      value={lastName}
                      onChange={(e) => setLastName(e.target.value)}
                      placeholder="Smith"
                      className="w-full mt-1 px-3 py-2 text-sm border border-border rounded-lg focus:ring-2 focus:ring-brand-primary-ring focus:border-brand-primary"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-[11px] font-medium text-text-muted uppercase tracking-wide">Email *</label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="jane@company.com"
                    className="w-full mt-1 px-3 py-2 text-sm border border-border rounded-lg focus:ring-2 focus:ring-brand-primary-ring focus:border-brand-primary"
                  />
                </div>

                <div>
                  <label className="text-[11px] font-medium text-text-muted uppercase tracking-wide">What should they focus on?</label>
                  <textarea
                    value={focusQuestion}
                    onChange={(e) => setFocusQuestion(e.target.value)}
                    placeholder="e.g., Does the reporting dashboard match how you'd use it?"
                    rows={2}
                    className="w-full mt-1 px-3 py-2 text-sm border border-border rounded-lg focus:ring-2 focus:ring-brand-primary-ring focus:border-brand-primary resize-none"
                  />
                </div>
              </div>

              {error && (
                <p className="mt-2 text-xs text-red-500">{error}</p>
              )}

              <button
                onClick={handleSubmit}
                disabled={!email.trim() || sending}
                className="w-full mt-4 px-4 py-2.5 bg-brand-primary text-white text-sm font-medium rounded-xl hover:bg-brand-primary-hover transition-all disabled:opacity-50"
              >
                {sending ? 'Sending...' : 'Send Invite'}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
