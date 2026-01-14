/**
 * NextStepsTab Component
 *
 * Clean, action-oriented interface for client outreach
 * - Minimalist summary with AI recommendation
 * - Two-column layout: Email vs Meeting topics
 * - Expandable details for when you need them
 */

'use client'

import React, { useState, useEffect } from 'react'
import {
  listConfirmations,
  updateConfirmationStatus,
  getConfirmationsSummary,
  generateConfirmationEmail,
  generateMeetingAgenda,
  getPortalConfig,
} from '@/lib/api'
import type { Confirmation } from '@/types/api'
import { Mail, Calendar, Lightbulb, Copy, X, Loader2, ChevronDown, ChevronUp, Check, Trash2 } from 'lucide-react'
import ClientPortalSection from '../ClientPortalSection'
import { DiscoveryPrepSection } from '../discovery-prep'

interface NextStepsTabProps {
  projectId: string
  projectName?: string
}

interface ConfirmationSummary {
  total: number
  by_method: { email: number; meeting: number }
  by_priority: { high: number; medium: number; low: number }
  by_kind: Record<string, any[]>
  recommendation: string
}

// Helper to extract a short topic from the confirmation
function getShortTopic(confirmation: Confirmation): string {
  // Use title but strip "Confirm: " prefix if present
  const title = confirmation.title || ''
  return title.replace(/^Confirm:\s*/i, '')
}

export function NextStepsTab({ projectId, projectName = 'Project' }: NextStepsTabProps) {
  const [confirmations, setConfirmations] = useState<Confirmation[]>([])
  const [loading, setLoading] = useState(true)
  const [summary, setSummary] = useState<ConfirmationSummary | null>(null)
  const [showDetails, setShowDetails] = useState(false)
  const [updating, setUpdating] = useState<string | null>(null)
  const [portalEnabled, setPortalEnabled] = useState(false)

  // Generation state
  const [generating, setGenerating] = useState<'email' | 'meeting' | null>(null)
  const [generatedEmail, setGeneratedEmail] = useState<{ subject: string; body: string } | null>(null)
  const [generatedAgenda, setGeneratedAgenda] = useState<any | null>(null)

  // Load data on mount
  useEffect(() => {
    loadData()
  }, [projectId])

  const loadData = async () => {
    try {
      setLoading(true)
      const [confData, summaryData, portalConfig] = await Promise.all([
        listConfirmations(projectId),
        getConfirmationsSummary(projectId),
        getPortalConfig(projectId).catch(() => ({ portal_enabled: false })),
      ])
      setConfirmations(confData.confirmations)
      setSummary(summaryData)
      setPortalEnabled(portalConfig.portal_enabled)
    } catch (error) {
      console.error('Failed to load data:', error)
    } finally {
      setLoading(false)
    }
  }

  // Split confirmations by suggested method
  const emailItems = confirmations.filter(c => c.suggested_method === 'email' && c.status === 'open')
  const meetingItems = confirmations.filter(c => c.suggested_method === 'meeting' && c.status === 'open')

  // Generate handlers
  const handleGenerateEmail = async () => {
    try {
      setGenerating('email')
      const result = await generateConfirmationEmail(projectId)
      setGeneratedEmail({ subject: result.subject, body: result.body })
    } catch (error) {
      console.error('Failed to generate email:', error)
      alert('Failed to generate email.')
    } finally {
      setGenerating(null)
    }
  }

  const handleGenerateMeetingAgenda = async () => {
    try {
      setGenerating('meeting')
      const result = await generateMeetingAgenda(projectId)
      setGeneratedAgenda(result)
    } catch (error) {
      console.error('Failed to generate meeting agenda:', error)
      alert('Failed to generate meeting agenda.')
    } finally {
      setGenerating(null)
    }
  }

  const handleCopyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      alert('Copied to clipboard!')
    } catch (error) {
      console.error('Failed to copy:', error)
    }
  }

  const handleResolve = async (confirmationId: string) => {
    try {
      setUpdating(confirmationId)
      await updateConfirmationStatus(confirmationId, 'resolved', {
        type: 'consultant_review',
        ref: 'confirmed',
        note: 'Resolved by consultant',
      })
      await loadData()
    } catch (error) {
      console.error('Failed to resolve:', error)
      alert('Failed to resolve item')
    } finally {
      setUpdating(null)
    }
  }

  const handleDismiss = async (confirmationId: string) => {
    try {
      setUpdating(confirmationId)
      await updateConfirmationStatus(confirmationId, 'dismissed', {
        type: 'consultant_decision',
        ref: 'not_relevant',
        note: 'Dismissed by consultant',
      })
      await loadData()
    } catch (error) {
      console.error('Failed to dismiss:', error)
      alert('Failed to dismiss item')
    } finally {
      setUpdating(null)
    }
  }

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-3" />
          <p className="text-gray-500">Loading...</p>
        </div>
      </div>
    )
  }

  // Empty state
  if (!summary || summary.total === 0) {
    return (
      <>
        {/* Client Portal Section - Always show */}
        <div className="p-6 max-w-4xl mx-auto mb-6">
          <ClientPortalSection projectId={projectId} projectName={projectName} />
        </div>

        {/* Discovery Prep Section */}
        <div className="p-6 max-w-4xl mx-auto mb-6">
          <DiscoveryPrepSection
            projectId={projectId}
            projectName={projectName}
            portalEnabled={portalEnabled}
          />
        </div>

        <div className="p-8">
          <div className="max-w-xl mx-auto text-center py-12">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Check className="w-8 h-8 text-green-600" />
            </div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">No client input needed</h2>
            <p className="text-gray-500">
              All items have been confirmed or don't require client review right now.
            </p>
          </div>
        </div>
      </>
    )
  }

  return (
    <>
      {/* Client Portal Section */}
      <div className="p-6 max-w-4xl mx-auto mb-6">
        <ClientPortalSection projectId={projectId} projectName={projectName} />
      </div>

      {/* Discovery Prep Section */}
      <div className="max-w-4xl mx-auto mb-6 px-6">
        <DiscoveryPrepSection
          projectId={projectId}
          projectName={projectName}
          portalEnabled={portalEnabled}
        />
      </div>

      <div className="p-6 max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-2">
            <h1 className="text-2xl font-semibold text-gray-900">Ready for Client Outreach</h1>
            <span className="text-sm text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
              {summary.total} item{summary.total !== 1 ? 's' : ''}
            </span>
          </div>

          {/* AI Recommendation */}
          <div className="flex items-start gap-3 mt-4 p-4 bg-blue-50 border border-blue-100 rounded-lg">
            <Lightbulb className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
            <p className="text-blue-800">{summary.recommendation}</p>
          </div>
        </div>

        {/* Two Column Layout */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          {/* Email Column */}
          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            <div className="p-4 bg-gray-50 border-b border-gray-200">
              <div className="flex items-center gap-2">
                <Mail className="w-5 h-5 text-gray-600" />
                <h3 className="font-medium text-gray-900">Email</h3>
                <span className="text-sm text-gray-500 ml-auto">
                  {emailItems.length} question{emailItems.length !== 1 ? 's' : ''}
                </span>
              </div>
            </div>

            <div className="p-4">
              {emailItems.length === 0 ? (
                <p className="text-gray-400 text-sm italic">No items for email</p>
              ) : (
                <ul className="space-y-2 mb-4">
                  {emailItems.map(item => (
                    <li key={item.id} className="flex items-start gap-2">
                      <span className="w-1.5 h-1.5 bg-blue-400 rounded-full mt-2 flex-shrink-0" />
                      <span className="text-gray-700 text-sm">{getShortTopic(item)}</span>
                    </li>
                  ))}
                </ul>
              )}

              <button
                onClick={handleGenerateEmail}
                disabled={generating !== null || emailItems.length === 0}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-white border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {generating === 'email' ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Mail className="w-4 h-4" />
                )}
                Draft Email
              </button>
            </div>
          </div>

          {/* Meeting Column */}
          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            <div className="p-4 bg-gray-50 border-b border-gray-200">
              <div className="flex items-center gap-2">
                <Calendar className="w-5 h-5 text-gray-600" />
                <h3 className="font-medium text-gray-900">Meeting</h3>
                <span className="text-sm text-gray-500 ml-auto">
                  {meetingItems.length} topic{meetingItems.length !== 1 ? 's' : ''}
                </span>
              </div>
            </div>

            <div className="p-4">
              {meetingItems.length === 0 ? (
                <p className="text-gray-400 text-sm italic">No items for meeting</p>
              ) : (
                <ul className="space-y-2 mb-4">
                  {meetingItems.map(item => (
                    <li key={item.id} className="flex items-start gap-2">
                      <span className="w-1.5 h-1.5 bg-purple-400 rounded-full mt-2 flex-shrink-0" />
                      <span className="text-gray-700 text-sm">{getShortTopic(item)}</span>
                    </li>
                  ))}
                </ul>
              )}

              <button
                onClick={handleGenerateMeetingAgenda}
                disabled={generating !== null || meetingItems.length === 0}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {generating === 'meeting' ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Calendar className="w-4 h-4" />
                )}
                Plan Meeting
              </button>
            </div>
          </div>
        </div>

        {/* Expandable Details */}
        <div className="border border-gray-200 rounded-lg overflow-hidden">
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="w-full flex items-center justify-between p-4 bg-gray-50 hover:bg-gray-100 transition-colors"
          >
            <span className="text-sm font-medium text-gray-600">
              View detailed items ({confirmations.filter(c => c.status === 'open').length})
            </span>
            {showDetails ? (
              <ChevronUp className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            )}
          </button>

          {showDetails && (
            <div className="divide-y divide-gray-100">
              {confirmations.filter(c => c.status === 'open').map(item => (
                <div key={item.id} className="p-4 hover:bg-gray-50">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-xs font-medium px-2 py-0.5 rounded ${
                          item.suggested_method === 'email'
                            ? 'bg-blue-100 text-blue-700'
                            : 'bg-purple-100 text-purple-700'
                        }`}>
                          {item.suggested_method}
                        </span>
                        <span className={`text-xs font-medium px-2 py-0.5 rounded ${
                          item.priority === 'high'
                            ? 'bg-red-100 text-red-700'
                            : item.priority === 'medium'
                            ? 'bg-yellow-100 text-yellow-700'
                            : 'bg-gray-100 text-gray-600'
                        }`}>
                          {item.priority}
                        </span>
                        <span className="text-xs text-gray-400">{item.kind}</span>
                      </div>

                      <h4 className="font-medium text-gray-900 mb-1">{item.title}</h4>

                      <p className="text-sm text-gray-600 mb-2">{item.ask}</p>

                      {item.why && (
                        <p className="text-xs text-gray-500">
                          <strong>Why:</strong> {item.why}
                        </p>
                      )}
                    </div>

                    <div className="flex items-center gap-2 flex-shrink-0">
                      <button
                        onClick={() => handleResolve(item.id)}
                        disabled={updating === item.id}
                        className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors disabled:opacity-50"
                        title="Mark as resolved"
                      >
                        {updating === item.id ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Check className="w-4 h-4" />
                        )}
                      </button>
                      <button
                        onClick={() => handleDismiss(item.id)}
                        disabled={updating === item.id}
                        className="p-2 text-gray-400 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
                        title="Dismiss"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Generated Email Modal */}
      {generatedEmail && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl max-w-2xl w-full max-h-[85vh] overflow-hidden shadow-xl">
            <div className="p-5 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                    <Mail className="w-5 h-5 text-blue-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">Email Draft</h3>
                    <p className="text-sm text-gray-500">Ready to copy and send</p>
                  </div>
                </div>
                <button
                  onClick={() => setGeneratedEmail(null)}
                  className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="p-5 overflow-y-auto max-h-[calc(85vh-180px)]">
              <div className="mb-5">
                <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Subject</label>
                <p className="bg-gray-50 p-3 rounded-lg font-medium text-gray-900">{generatedEmail.subject}</p>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Body</label>
                <pre className="bg-gray-50 p-4 rounded-lg whitespace-pre-wrap font-sans text-sm text-gray-700 leading-relaxed">{generatedEmail.body}</pre>
              </div>
            </div>

            <div className="p-5 border-t border-gray-200 bg-gray-50 flex justify-end gap-3">
              <button
                onClick={() => setGeneratedEmail(null)}
                className="px-4 py-2 text-gray-600 hover:bg-gray-200 rounded-lg transition-colors"
              >
                Close
              </button>
              <button
                onClick={() => handleCopyToClipboard(`Subject: ${generatedEmail.subject}\n\n${generatedEmail.body}`)}
                className="flex items-center gap-2 px-5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <Copy className="w-4 h-4" />
                Copy to Clipboard
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Generated Meeting Agenda Modal */}
      {generatedAgenda && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl max-w-2xl w-full max-h-[85vh] overflow-hidden shadow-xl">
            <div className="p-5 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center">
                    <Calendar className="w-5 h-5 text-purple-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">Meeting Agenda</h3>
                    <p className="text-sm text-gray-500">{generatedAgenda.duration_estimate}</p>
                  </div>
                </div>
                <button
                  onClick={() => setGeneratedAgenda(null)}
                  className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="p-5 overflow-y-auto max-h-[calc(85vh-180px)]">
              <h4 className="font-semibold text-gray-900 text-lg mb-4">{generatedAgenda.title}</h4>

              {generatedAgenda.pre_read && (
                <div className="mb-5 p-4 bg-amber-50 border border-amber-200 rounded-lg">
                  <p className="text-xs font-medium text-amber-700 uppercase tracking-wide mb-1">Pre-read for client</p>
                  <p className="text-sm text-amber-800">{generatedAgenda.pre_read}</p>
                </div>
              )}

              <div className="space-y-3">
                {generatedAgenda.agenda?.map((item: any, idx: number) => (
                  <div key={idx} className="flex gap-4 p-4 bg-gray-50 rounded-lg">
                    <div className="w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center flex-shrink-0">
                      <span className="text-sm font-semibold text-purple-700">{idx + 1}</span>
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-1">
                        <h5 className="font-medium text-gray-900">{item.topic}</h5>
                        <span className="text-xs text-gray-500 bg-white px-2 py-1 rounded">
                          {item.time_minutes} min
                        </span>
                      </div>
                      {item.description && (
                        <p className="text-sm text-gray-600">{item.description}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="p-5 border-t border-gray-200 bg-gray-50 flex justify-end gap-3">
              <button
                onClick={() => setGeneratedAgenda(null)}
                className="px-4 py-2 text-gray-600 hover:bg-gray-200 rounded-lg transition-colors"
              >
                Close
              </button>
              <button
                onClick={() => {
                  const agendaText = `${generatedAgenda.title}\nDuration: ${generatedAgenda.duration_estimate}\n\n${generatedAgenda.pre_read ? `Pre-read: ${generatedAgenda.pre_read}\n\n` : ''}Agenda:\n${generatedAgenda.agenda?.map((item: any, idx: number) => `${idx + 1}. ${item.topic} (${item.time_minutes} min)\n   ${item.description || ''}`).join('\n\n')}`
                  handleCopyToClipboard(agendaText)
                }}
                className="flex items-center gap-2 px-5 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
              >
                <Copy className="w-4 h-4" />
                Copy to Clipboard
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
