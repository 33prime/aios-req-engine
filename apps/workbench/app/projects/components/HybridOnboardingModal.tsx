'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import {
  X,
  Send,
  Building2,
  User,
  Plus,
  Trash2,
  Rocket,
  Check,
  ChevronRight,
} from 'lucide-react'
import { useProjectCreationChat, type ChatSummaryData } from '@/lib/useProjectCreationChat'
import { launchProject } from '@/lib/api'
import type { StakeholderLaunchInput } from '@/types/workspace'

interface HybridOnboardingModalProps {
  isOpen: boolean
  onClose: () => void
  onLaunched: (response: { project_id: string; launch_id: string }) => void
}

type Phase = 'chat' | 'client_card' | 'stakeholder_card' | 'confirm' | 'launching'

const STAKEHOLDER_TYPES = [
  { value: 'champion', label: 'Champion' },
  { value: 'sponsor', label: 'Sponsor' },
  { value: 'influencer', label: 'Influencer' },
  { value: 'blocker', label: 'Blocker' },
  { value: 'end_user', label: 'End User' },
] as const

function renderMarkdown(text: string) {
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/^• (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/gs, '<ul class="list-disc ml-4 my-1">$1</ul>')
    .replace(/\n/g, '<br/>')
}

export function HybridOnboardingModal({
  isOpen,
  onClose,
  onLaunched,
}: HybridOnboardingModalProps) {
  const [phase, setPhase] = useState<Phase>('chat')
  const [input, setInput] = useState('')
  const [summary, setSummary] = useState<ChatSummaryData | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Client card state
  const [clientName, setClientName] = useState('')
  const [clientWebsite, setClientWebsite] = useState('')
  const [clientIndustry, setClientIndustry] = useState('')
  const [clientCardDone, setClientCardDone] = useState(false)

  // Stakeholder card state
  const [stakeholders, setStakeholders] = useState<StakeholderLaunchInput[]>([])
  const [sFirstName, setSFirstName] = useState('')
  const [sLastName, setSLastName] = useState('')
  const [sEmail, setSEmail] = useState('')
  const [sLinkedin, setSLinkedin] = useState('')
  const [sRole, setSRole] = useState('')
  const [sType, setSType] = useState('champion')

  const handleSummaryReady = useCallback((summaryData: ChatSummaryData) => {
    setSummary(summaryData)
    // Add a small delay so the summary message renders first
    setTimeout(() => setPhase('client_card'), 800)
  }, [])

  const {
    messages,
    isLoading,
    chatSummary,
    sendMessage,
    initializeChat,
    reset,
  } = useProjectCreationChat({
    onSummaryReady: handleSummaryReady,
  })

  useEffect(() => {
    if (isOpen) {
      initializeChat()
    }
  }, [isOpen, initializeChat])

  // Use chatSummary from hook as fallback
  useEffect(() => {
    if (chatSummary && !summary) {
      setSummary(chatSummary)
      setTimeout(() => setPhase('client_card'), 800)
    }
  }, [chatSummary, summary])

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, phase])

  const handleSend = async () => {
    if (!input.trim() || isLoading) return
    const msg = input.trim()
    setInput('')
    await sendMessage(msg)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const addStakeholder = () => {
    if (!sFirstName.trim()) return
    setStakeholders((prev) => [
      ...prev,
      {
        first_name: sFirstName.trim(),
        last_name: sLastName.trim(),
        email: sEmail.trim() || undefined,
        linkedin_url: sLinkedin.trim() || undefined,
        role: sRole.trim() || undefined,
        stakeholder_type: sType,
      },
    ])
    setSFirstName('')
    setSLastName('')
    setSEmail('')
    setSLinkedin('')
    setSRole('')
    setSType('champion')
  }

  const removeStakeholder = (idx: number) => {
    setStakeholders((prev) => prev.filter((_, i) => i !== idx))
  }

  const handleClientContinue = () => {
    setClientCardDone(true)
    setPhase('stakeholder_card')
  }

  const handleClientSkip = () => {
    setClientCardDone(true)
    setPhase('stakeholder_card')
  }

  const handleStakeholderContinue = () => {
    setPhase('confirm')
  }

  const handleLaunch = async () => {
    if (!summary) return
    setPhase('launching')

    try {
      // Build the full chat transcript from messages
      const chatTranscript = messages
        .map((m) => `${m.role === 'user' ? 'User' : 'Assistant'}: ${m.content}`)
        .join('\n\n')

      const response = await launchProject({
        project_name: summary.name,
        problem_description: `${summary.problem}\n\nTarget Users: ${summary.users}\nKey Features: ${summary.features}\nOrganizational Context: ${summary.org_fit}`,
        chat_transcript: chatTranscript,
        client_name: clientName || undefined,
        client_website: clientWebsite || undefined,
        client_industry: clientIndustry || undefined,
        stakeholders: stakeholders as any,
        auto_discovery: false,
      })

      onLaunched({
        project_id: response.project_id,
        launch_id: response.launch_id,
      })
      handleClose()
    } catch (err) {
      console.error('Launch failed:', err)
      setPhase('confirm')
    }
  }

  const handleClose = () => {
    reset()
    setPhase('chat')
    setSummary(null)
    setInput('')
    setClientName('')
    setClientWebsite('')
    setClientIndustry('')
    setClientCardDone(false)
    setStakeholders([])
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/30 backdrop-blur-md"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-2xl h-[85vh] bg-white rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-[#0A1E2F] to-[#0D2A35] px-6 py-4 flex items-center justify-between shrink-0">
          <div>
            <h2 className="text-white font-semibold text-lg">
              {phase === 'launching' ? 'Launching...' : 'New Project'}
            </h2>
            <p className="text-white/60 text-sm">
              {phase === 'chat' && "Let's get the basics down"}
              {phase === 'client_card' && 'A few more details'}
              {phase === 'stakeholder_card' && 'Key contacts'}
              {phase === 'confirm' && 'Ready to launch'}
              {phase === 'launching' && 'Setting everything up'}
            </p>
          </div>
          <button
            onClick={handleClose}
            className="text-white/60 hover:text-white p-1 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Messages area */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {/* Chat messages */}
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-[#0A1E2F] text-white'
                    : 'bg-[#F4F4F4] text-[#333333]'
                }`}
                dangerouslySetInnerHTML={{
                  __html: renderMarkdown(msg.content),
                }}
              />
            </div>
          ))}

          {/* Loading indicator */}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-[#F4F4F4] rounded-2xl px-4 py-3">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-[#999999] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 bg-[#999999] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 bg-[#999999] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}

          {/* Client Card (inline after chat) */}
          {phase === 'client_card' && !clientCardDone && (
            <div className="flex justify-start">
              <div className="bg-[#F4F4F4] rounded-2xl px-4 py-3 text-sm text-[#333333] max-w-[85%]">
                A few more details to get started.
              </div>
            </div>
          )}
          {(phase === 'client_card' || (clientCardDone && (phase === 'stakeholder_card' || phase === 'confirm'))) && (
            <div className="flex justify-start w-full">
              {clientCardDone ? (
                // Collapsed state
                <div className="bg-white border border-[#E5E5E5] rounded-xl px-4 py-3 flex items-center gap-3 max-w-[85%]">
                  <div className="w-8 h-8 rounded-full bg-[#E8F5E9] flex items-center justify-center">
                    <Check className="w-4 h-4 text-[#25785A]" />
                  </div>
                  <div className="text-sm text-[#333333]">
                    {clientName ? (
                      <span><strong>{clientName}</strong>{clientWebsite ? ` (${clientWebsite})` : ''}</span>
                    ) : (
                      <span className="text-[#999999]">Client info skipped</span>
                    )}
                  </div>
                </div>
              ) : (
                // Expanded card
                <div className="w-full max-w-md bg-white border border-[#E5E5E5] rounded-xl shadow-md p-5">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <Building2 className="w-4 h-4 text-[#666666]" />
                      <span className="font-medium text-sm text-[#333333]">Client Information</span>
                    </div>
                    <span className="text-xs text-[#999999]">1/2</span>
                  </div>
                  <div className="space-y-3">
                    <input
                      type="text"
                      placeholder="Company Name"
                      value={clientName}
                      onChange={(e) => setClientName(e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-[#E5E5E5] rounded-lg bg-[#F4F4F4] focus:outline-none focus:ring-2 focus:ring-[#3FAF7A]/20 focus:border-[#3FAF7A]"
                    />
                    <input
                      type="text"
                      placeholder="Website"
                      value={clientWebsite}
                      onChange={(e) => setClientWebsite(e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-[#E5E5E5] rounded-lg bg-[#F4F4F4] focus:outline-none focus:ring-2 focus:ring-[#3FAF7A]/20 focus:border-[#3FAF7A]"
                    />
                    <input
                      type="text"
                      placeholder="Industry"
                      value={clientIndustry}
                      onChange={(e) => setClientIndustry(e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-[#E5E5E5] rounded-lg bg-[#F4F4F4] focus:outline-none focus:ring-2 focus:ring-[#3FAF7A]/20 focus:border-[#3FAF7A]"
                    />
                  </div>
                  <div className="flex justify-between mt-4">
                    <button
                      onClick={handleClientSkip}
                      className="text-sm text-[#999999] hover:text-[#666666] px-3 py-2"
                    >
                      Skip
                    </button>
                    <button
                      onClick={handleClientContinue}
                      className="flex items-center gap-1.5 text-sm bg-[#3FAF7A] text-white px-4 py-2 rounded-lg hover:bg-[#25785A] transition-colors"
                    >
                      Continue <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Stakeholder Card */}
          {(phase === 'stakeholder_card' || phase === 'confirm') && (
            <div className="flex justify-start w-full">
              {phase === 'confirm' ? (
                // Collapsed state
                <div className="bg-white border border-[#E5E5E5] rounded-xl px-4 py-3 flex items-center gap-3 max-w-[85%]">
                  <div className="w-8 h-8 rounded-full bg-[#E8F5E9] flex items-center justify-center">
                    <Check className="w-4 h-4 text-[#25785A]" />
                  </div>
                  <div className="text-sm text-[#333333]">
                    {stakeholders.length > 0 ? (
                      <span>{stakeholders.length} stakeholder{stakeholders.length > 1 ? 's' : ''} added</span>
                    ) : (
                      <span className="text-[#999999]">No stakeholders added</span>
                    )}
                  </div>
                </div>
              ) : (
                // Expanded card
                <div className="w-full max-w-md bg-white border border-[#E5E5E5] rounded-xl shadow-md p-5">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <User className="w-4 h-4 text-[#666666]" />
                      <span className="font-medium text-sm text-[#333333]">Key Stakeholder</span>
                    </div>
                    <span className="text-xs text-[#999999]">2/2</span>
                  </div>

                  {/* Added stakeholders list */}
                  {stakeholders.length > 0 && (
                    <div className="space-y-2 mb-3">
                      {stakeholders.map((s, i) => (
                        <div
                          key={i}
                          className="flex items-center justify-between bg-[#F4F4F4] rounded-lg px-3 py-2"
                        >
                          <span className="text-sm text-[#333333]">
                            {s.first_name} {s.last_name}
                            {s.role ? ` — ${s.role}` : ''}
                          </span>
                          <button
                            onClick={() => removeStakeholder(i)}
                            className="text-[#999999] hover:text-red-500"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Add stakeholder form */}
                  <div className="space-y-2">
                    <div className="flex gap-2">
                      <input
                        type="text"
                        placeholder="First Name"
                        value={sFirstName}
                        onChange={(e) => setSFirstName(e.target.value)}
                        className="flex-1 px-3 py-2 text-sm border border-[#E5E5E5] rounded-lg bg-[#F4F4F4] focus:outline-none focus:ring-2 focus:ring-[#3FAF7A]/20 focus:border-[#3FAF7A]"
                      />
                      <input
                        type="text"
                        placeholder="Last Name"
                        value={sLastName}
                        onChange={(e) => setSLastName(e.target.value)}
                        className="flex-1 px-3 py-2 text-sm border border-[#E5E5E5] rounded-lg bg-[#F4F4F4] focus:outline-none focus:ring-2 focus:ring-[#3FAF7A]/20 focus:border-[#3FAF7A]"
                      />
                    </div>
                    <input
                      type="email"
                      placeholder="Email"
                      value={sEmail}
                      onChange={(e) => setSEmail(e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-[#E5E5E5] rounded-lg bg-[#F4F4F4] focus:outline-none focus:ring-2 focus:ring-[#3FAF7A]/20 focus:border-[#3FAF7A]"
                    />
                    <input
                      type="text"
                      placeholder="LinkedIn URL"
                      value={sLinkedin}
                      onChange={(e) => setSLinkedin(e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-[#E5E5E5] rounded-lg bg-[#F4F4F4] focus:outline-none focus:ring-2 focus:ring-[#3FAF7A]/20 focus:border-[#3FAF7A]"
                    />
                    <div className="flex gap-2">
                      <input
                        type="text"
                        placeholder="Role"
                        value={sRole}
                        onChange={(e) => setSRole(e.target.value)}
                        className="flex-1 px-3 py-2 text-sm border border-[#E5E5E5] rounded-lg bg-[#F4F4F4] focus:outline-none focus:ring-2 focus:ring-[#3FAF7A]/20 focus:border-[#3FAF7A]"
                      />
                      <select
                        value={sType}
                        onChange={(e) => setSType(e.target.value)}
                        className="px-3 py-2 text-sm border border-[#E5E5E5] rounded-lg bg-[#F4F4F4] focus:outline-none focus:ring-2 focus:ring-[#3FAF7A]/20 focus:border-[#3FAF7A]"
                      >
                        {STAKEHOLDER_TYPES.map((t) => (
                          <option key={t.value} value={t.value}>
                            {t.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <button
                      onClick={addStakeholder}
                      disabled={!sFirstName.trim()}
                      className="flex items-center gap-1.5 text-sm text-[#3FAF7A] hover:text-[#25785A] disabled:text-[#999999] px-1 py-1"
                    >
                      <Plus className="w-3.5 h-3.5" /> Add stakeholder
                    </button>
                  </div>

                  <div className="flex justify-end mt-4">
                    <button
                      onClick={handleStakeholderContinue}
                      className="flex items-center gap-1.5 text-sm bg-[#3FAF7A] text-white px-4 py-2 rounded-lg hover:bg-[#25785A] transition-colors"
                    >
                      Continue <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Launch confirmation */}
          {phase === 'confirm' && summary && (
            <div className="flex justify-start w-full">
              <div className="w-full max-w-md bg-white border border-[#E5E5E5] rounded-xl shadow-md p-5">
                <p className="text-sm text-[#333333] mb-4">
                  Everything looks great. Here&apos;s what I&apos;ll set up:
                </p>
                <ul className="space-y-1.5 text-sm text-[#666666] mb-5">
                  <li className="flex items-start gap-2">
                    <span className="text-[#999999] mt-0.5">•</span>
                    <span><strong className="text-[#333333]">Project:</strong> {summary.name}</span>
                  </li>
                  {clientName && (
                    <li className="flex items-start gap-2">
                      <span className="text-[#999999] mt-0.5">•</span>
                      <span>
                        <strong className="text-[#333333]">Client:</strong> {clientName}
                        {clientWebsite ? ` (${clientWebsite})` : ''}
                      </span>
                    </li>
                  )}
                  {stakeholders.length > 0 && (
                    <li className="flex items-start gap-2">
                      <span className="text-[#999999] mt-0.5">•</span>
                      <span>
                        <strong className="text-[#333333]">Contacts:</strong>{' '}
                        {stakeholders.map((s) => `${s.first_name} ${s.last_name}`).join(', ')}
                      </span>
                    </li>
                  )}
                </ul>
                <button
                  onClick={handleLaunch}
                  className="w-full flex items-center justify-center gap-2 bg-[#3FAF7A] text-white font-medium py-3 rounded-xl hover:bg-[#25785A] transition-colors"
                >
                  <Rocket className="w-4 h-4" /> Launch Project
                </button>
              </div>
            </div>
          )}

          {/* Launching state */}
          {phase === 'launching' && (
            <div className="flex justify-center py-8">
              <div className="text-center">
                <div className="w-12 h-12 border-3 border-[#3FAF7A] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
                <p className="text-sm text-[#666666]">Building your project...</p>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input area — only visible during chat phase */}
        {phase === 'chat' && (
          <div className="border-t border-[#E5E5E5] px-6 py-4 shrink-0">
            <div className="flex items-center gap-3">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type your response..."
                disabled={isLoading}
                className="flex-1 px-4 py-2.5 text-sm border border-[#E5E5E5] rounded-xl bg-[#F4F4F4] focus:outline-none focus:ring-2 focus:ring-[#3FAF7A]/20 focus:border-[#3FAF7A] disabled:opacity-50"
                autoFocus
              />
              <button
                onClick={handleSend}
                disabled={isLoading || !input.trim()}
                className="p-2.5 bg-[#3FAF7A] text-white rounded-xl hover:bg-[#25785A] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
