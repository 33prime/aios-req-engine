'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import {
  X,
  Rocket,
  Building2,
  Users,
  FileText,
  Check,
  Plus,
  Trash2,
  Globe,
  Linkedin,
  ChevronRight,
  ChevronLeft,
  Search,
  ToggleLeft,
  ToggleRight,
} from 'lucide-react'
import { listClients, launchProject } from '@/lib/api'
import type {
  ClientSummary,
  ProjectLaunchResponse,
  StakeholderLaunchInput,
} from '@/types/workspace'

interface ProjectLaunchWizardProps {
  isOpen: boolean
  onClose: () => void
  onLaunched: (response: ProjectLaunchResponse) => void
}

const STAKEHOLDER_TYPES = [
  { value: 'champion', label: 'Champion' },
  { value: 'sponsor', label: 'Sponsor' },
  { value: 'influencer', label: 'Influencer' },
  { value: 'blocker', label: 'Blocker' },
  { value: 'end_user', label: 'End User' },
] as const

const STEPS = [
  { label: 'Project', icon: FileText },
  { label: 'Client', icon: Building2 },
  { label: 'Contact', icon: Users },
  { label: 'Launch', icon: Rocket },
]

type ClientMode = 'skip' | 'existing' | 'new'

export function ProjectLaunchWizard({ isOpen, onClose, onLaunched }: ProjectLaunchWizardProps) {
  const [step, setStep] = useState(0)
  const [launching, setLaunching] = useState(false)

  // Step 1: Project
  const [projectName, setProjectName] = useState('')
  const [problemDescription, setProblemDescription] = useState('')

  // Step 2: Client
  const [clientMode, setClientMode] = useState<ClientMode>('skip')
  const [clientSearch, setClientSearch] = useState('')
  const [clientResults, setClientResults] = useState<ClientSummary[]>([])
  const [selectedClient, setSelectedClient] = useState<ClientSummary | null>(null)
  const [newClientName, setNewClientName] = useState('')
  const [newClientWebsite, setNewClientWebsite] = useState('')
  const [newClientIndustry, setNewClientIndustry] = useState('')
  const [searchLoading, setSearchLoading] = useState(false)

  // Step 3: Stakeholders
  const [stakeholders, setStakeholders] = useState<StakeholderLaunchInput[]>([])
  const [sFirstName, setSFirstName] = useState('')
  const [sLastName, setSLastName] = useState('')
  const [sEmail, setSEmail] = useState('')
  const [sLinkedin, setSLinkedin] = useState('')
  const [sRole, setSRole] = useState('')
  const [sType, setSType] = useState('champion')

  // Step 4: Launch
  const [autoDiscovery, setAutoDiscovery] = useState(false)

  const searchTimeout = useRef<NodeJS.Timeout | null>(null)

  // Client search debounce
  useEffect(() => {
    if (clientMode !== 'existing' || clientSearch.length < 2) {
      setClientResults([])
      return
    }
    if (searchTimeout.current) clearTimeout(searchTimeout.current)
    searchTimeout.current = setTimeout(async () => {
      setSearchLoading(true)
      try {
        const res = await listClients({ search: clientSearch, limit: 5 })
        setClientResults(res.clients || [])
      } catch {
        setClientResults([])
      } finally {
        setSearchLoading(false)
      }
    }, 300)
    return () => {
      if (searchTimeout.current) clearTimeout(searchTimeout.current)
    }
  }, [clientSearch, clientMode])

  const resetForm = useCallback(() => {
    setStep(0)
    setProjectName('')
    setProblemDescription('')
    setClientMode('skip')
    setClientSearch('')
    setClientResults([])
    setSelectedClient(null)
    setNewClientName('')
    setNewClientWebsite('')
    setNewClientIndustry('')
    setStakeholders([])
    setSFirstName('')
    setSLastName('')
    setSEmail('')
    setSLinkedin('')
    setSRole('')
    setSType('champion')
    setAutoDiscovery(false)
    setLaunching(false)
  }, [])

  const handleClose = useCallback(() => {
    if (launching) return
    resetForm()
    onClose()
  }, [launching, resetForm, onClose])

  const canProceed = (): boolean => {
    if (step === 0) return projectName.trim().length > 0
    if (step === 1) {
      if (clientMode === 'existing') return !!selectedClient
      if (clientMode === 'new') return newClientName.trim().length > 0
      return true
    }
    return true
  }

  const addStakeholder = () => {
    if (!sFirstName.trim() || !sLastName.trim()) return
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

  const getClientWebsite = (): string | undefined => {
    if (clientMode === 'existing') return selectedClient?.website || undefined
    if (clientMode === 'new') return newClientWebsite || undefined
    return undefined
  }

  const hasLinkedin = stakeholders.some((s) => s.linkedin_url)

  const handleLaunch = async () => {
    setLaunching(true)
    try {
      const payload: Parameters<typeof launchProject>[0] = {
        project_name: projectName.trim(),
        problem_description: problemDescription.trim() || undefined,
        auto_discovery: autoDiscovery,
        stakeholders: stakeholders.length > 0 ? stakeholders : undefined,
      }
      if (clientMode === 'existing' && selectedClient) {
        payload.client_id = selectedClient.id
      } else if (clientMode === 'new' && newClientName.trim()) {
        payload.client_name = newClientName.trim()
        payload.client_website = newClientWebsite.trim() || undefined
        payload.client_industry = newClientIndustry.trim() || undefined
      }
      const response = await launchProject(payload)
      resetForm()
      onLaunched(response)
    } catch (e) {
      console.error('Launch failed:', e)
      setLaunching(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50">
      <div
        className="fixed inset-0 bg-black/30 backdrop-blur-md flex items-center justify-center p-4"
        onClick={handleClose}
      >
        <div
          className="bg-[#F4F4F4] rounded-2xl shadow-2xl max-w-2xl w-full max-h-[85vh] flex flex-col overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="relative bg-gradient-to-r from-[#0A1E2F] to-[#0D2A35] px-6 py-4 text-white flex-shrink-0">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-white/10 backdrop-blur-sm flex items-center justify-center">
                  <Rocket className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-[16px] font-bold">Launch New Project</h2>
                  <p className="text-[12px] text-white/60">Step {step + 1} of 4</p>
                </div>
              </div>
              <button
                onClick={handleClose}
                className="text-white/70 hover:text-white transition-colors p-1.5"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Step indicator */}
          <div className="px-6 py-4 flex items-center justify-center gap-2 flex-shrink-0">
            {STEPS.map((s, i) => {
              const Icon = s.icon
              const isDone = i < step
              const isCurrent = i === step
              return (
                <div key={s.label} className="flex items-center gap-2">
                  {i > 0 && (
                    <div
                      className={`w-8 h-[2px] ${isDone ? 'bg-brand-primary' : 'bg-border'}`}
                    />
                  )}
                  <div className="flex flex-col items-center gap-1">
                    <div
                      className={`w-8 h-8 rounded-full flex items-center justify-center text-[12px] font-semibold transition-all ${
                        isDone
                          ? 'bg-brand-primary text-white'
                          : isCurrent
                            ? 'bg-brand-primary-light text-brand-primary border-2 border-brand-primary'
                            : 'bg-border text-text-placeholder'
                      }`}
                    >
                      {isDone ? <Check className="w-4 h-4" /> : <Icon className="w-4 h-4" />}
                    </div>
                    <span
                      className={`text-[11px] font-medium ${
                        isDone || isCurrent ? 'text-text-body' : 'text-text-placeholder'
                      }`}
                    >
                      {s.label}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>

          {/* Step content */}
          <div className="flex-1 overflow-y-auto px-6 pb-4">
            <div className="bg-white rounded-2xl shadow-md border border-border p-6">
              {step === 0 && <StepProject
                projectName={projectName}
                setProjectName={setProjectName}
                problemDescription={problemDescription}
                setProblemDescription={setProblemDescription}
              />}
              {step === 1 && <StepClient
                clientMode={clientMode}
                setClientMode={setClientMode}
                clientSearch={clientSearch}
                setClientSearch={setClientSearch}
                clientResults={clientResults}
                selectedClient={selectedClient}
                setSelectedClient={setSelectedClient}
                setClientResults={setClientResults}
                searchLoading={searchLoading}
                newClientName={newClientName}
                setNewClientName={setNewClientName}
                newClientWebsite={newClientWebsite}
                setNewClientWebsite={setNewClientWebsite}
                newClientIndustry={newClientIndustry}
                setNewClientIndustry={setNewClientIndustry}
              />}
              {step === 2 && <StepStakeholder
                stakeholders={stakeholders}
                sFirstName={sFirstName}
                setSFirstName={setSFirstName}
                sLastName={sLastName}
                setSLastName={setSLastName}
                sEmail={sEmail}
                setSEmail={setSEmail}
                sLinkedin={sLinkedin}
                setSLinkedin={setSLinkedin}
                sRole={sRole}
                setSRole={setSRole}
                sType={sType}
                setSType={setSType}
                addStakeholder={addStakeholder}
                removeStakeholder={removeStakeholder}
              />}
              {step === 3 && <StepSummary
                projectName={projectName}
                problemDescription={problemDescription}
                clientMode={clientMode}
                selectedClient={selectedClient}
                newClientName={newClientName}
                newClientWebsite={newClientWebsite}
                stakeholders={stakeholders}
                hasLinkedin={hasLinkedin}
                clientWebsite={getClientWebsite()}
                autoDiscovery={autoDiscovery}
                setAutoDiscovery={setAutoDiscovery}
              />}
            </div>
          </div>

          {/* Footer nav */}
          <div className="px-6 py-4 flex items-center justify-between border-t border-border flex-shrink-0 bg-white">
            {step > 0 ? (
              <button
                onClick={() => setStep((s) => s - 1)}
                className="flex items-center gap-1.5 text-[14px] text-[#666666] hover:text-text-body transition-colors"
                disabled={launching}
              >
                <ChevronLeft className="w-4 h-4" />
                Back
              </button>
            ) : (
              <div />
            )}
            {step < 3 ? (
              <button
                onClick={() => setStep((s) => s + 1)}
                disabled={!canProceed()}
                className="flex items-center gap-1.5 bg-brand-primary text-white rounded-xl px-6 py-2.5 text-[14px] font-semibold hover:bg-[#25785A] transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Next Step
                <ChevronRight className="w-4 h-4" />
              </button>
            ) : (
              <button
                onClick={handleLaunch}
                disabled={launching}
                className="flex items-center gap-2 bg-brand-primary text-white rounded-xl px-8 py-2.5 text-[16px] font-semibold hover:bg-[#25785A] transition-colors disabled:opacity-60"
              >
                {launching ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Launching...
                  </>
                ) : (
                  <>
                    <Rocket className="w-4 h-4" />
                    Launch Project
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// =============================================================================
// Step 1: Project
// =============================================================================

function StepProject({
  projectName,
  setProjectName,
  problemDescription,
  setProblemDescription,
}: {
  projectName: string
  setProjectName: (v: string) => void
  problemDescription: string
  setProblemDescription: (v: string) => void
}) {
  return (
    <div className="space-y-5">
      <div>
        <label className="block text-[13px] font-medium text-text-body mb-1.5">
          Project Name
        </label>
        <input
          type="text"
          value={projectName}
          onChange={(e) => setProjectName(e.target.value)}
          placeholder="What are you building?"
          className="w-full text-[20px] font-semibold text-text-body placeholder-[#CCCCCC] bg-[#F4F4F4] border border-border rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary transition-colors"
          autoFocus
        />
      </div>
      <div>
        <label className="block text-[13px] font-medium text-text-body mb-1.5">
          Problem Description
        </label>
        <textarea
          value={problemDescription}
          onChange={(e) => setProblemDescription(e.target.value)}
          placeholder="Paste meeting notes, project brief, or describe the problem..."
          rows={6}
          className="w-full text-[14px] text-text-body placeholder-[#CCCCCC] bg-[#F4F4F4] border border-border rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary transition-colors resize-none"
        />
        <p className="text-[13px] text-text-placeholder mt-1.5">
          The more context you share, the better the AI extracts features, personas, and value paths.
        </p>
      </div>
    </div>
  )
}

// =============================================================================
// Step 2: Client
// =============================================================================

function StepClient({
  clientMode,
  setClientMode,
  clientSearch,
  setClientSearch,
  clientResults,
  selectedClient,
  setSelectedClient,
  setClientResults,
  searchLoading,
  newClientName,
  setNewClientName,
  newClientWebsite,
  setNewClientWebsite,
  newClientIndustry,
  setNewClientIndustry,
}: {
  clientMode: ClientMode
  setClientMode: (v: ClientMode) => void
  clientSearch: string
  setClientSearch: (v: string) => void
  clientResults: ClientSummary[]
  selectedClient: ClientSummary | null
  setSelectedClient: (v: ClientSummary | null) => void
  setClientResults: (v: ClientSummary[]) => void
  searchLoading: boolean
  newClientName: string
  setNewClientName: (v: string) => void
  newClientWebsite: string
  setNewClientWebsite: (v: string) => void
  newClientIndustry: string
  setNewClientIndustry: (v: string) => void
}) {
  const modes: { value: ClientMode; label: string; desc: string }[] = [
    { value: 'skip', label: 'Skip for now', desc: 'Add a client later from the workspace' },
    { value: 'existing', label: 'Existing Client', desc: 'Search your client database' },
    { value: 'new', label: 'New Client', desc: 'Create a new client profile' },
  ]

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        {modes.map((m) => (
          <button
            key={m.value}
            onClick={() => {
              setClientMode(m.value)
              setSelectedClient(null)
            }}
            className={`p-4 rounded-xl border-2 text-left transition-all ${
              clientMode === m.value
                ? 'border-brand-primary bg-[#E8F5E9]/30'
                : 'border-border hover:border-[#CCCCCC]'
            }`}
          >
            <p className="text-[14px] font-semibold text-text-body">{m.label}</p>
            <p className="text-[12px] text-text-placeholder mt-1">{m.desc}</p>
          </button>
        ))}
      </div>

      {clientMode === 'existing' && (
        <div className="space-y-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-placeholder" />
            <input
              type="text"
              value={clientSearch}
              onChange={(e) => setClientSearch(e.target.value)}
              placeholder="Search clients by name..."
              className="w-full text-[14px] text-text-body placeholder-[#CCCCCC] bg-[#F4F4F4] border border-border rounded-xl pl-10 pr-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary"
              autoFocus
            />
          </div>
          {searchLoading && (
            <p className="text-[13px] text-text-placeholder">Searching...</p>
          )}
          {clientResults.length > 0 && (
            <div className="space-y-1 max-h-40 overflow-y-auto">
              {clientResults.map((c) => (
                <button
                  key={c.id}
                  onClick={() => {
                    setSelectedClient(c)
                    setClientSearch(c.name)
                    setClientResults([])
                  }}
                  className={`w-full text-left px-4 py-2.5 rounded-lg transition-colors ${
                    selectedClient?.id === c.id
                      ? 'bg-[#E8F5E9] border border-brand-primary/30'
                      : 'hover:bg-[#F4F4F4]'
                  }`}
                >
                  <p className="text-[14px] font-medium text-text-body">{c.name}</p>
                  {c.industry && (
                    <p className="text-[12px] text-text-placeholder">{c.industry}</p>
                  )}
                </button>
              ))}
            </div>
          )}
          {selectedClient && (
            <div className="flex items-center gap-2 bg-[#E8F5E9] rounded-lg px-3 py-2">
              <Check className="w-4 h-4 text-brand-primary" />
              <span className="text-[13px] font-medium text-[#25785A]">
                {selectedClient.name}
              </span>
              {selectedClient.website && (
                <span className="text-[12px] text-text-placeholder">{selectedClient.website}</span>
              )}
            </div>
          )}
        </div>
      )}

      {clientMode === 'new' && (
        <div className="space-y-3">
          <div>
            <label className="block text-[13px] font-medium text-text-body mb-1">
              Client Name *
            </label>
            <input
              type="text"
              value={newClientName}
              onChange={(e) => setNewClientName(e.target.value)}
              placeholder="Acme Corp"
              className="w-full text-[14px] text-text-body placeholder-[#CCCCCC] bg-[#F4F4F4] border border-border rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-[13px] font-medium text-text-body mb-1">
              Website
            </label>
            <div className="relative">
              <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-placeholder" />
              <input
                type="text"
                value={newClientWebsite}
                onChange={(e) => setNewClientWebsite(e.target.value)}
                placeholder="https://acme.com"
                className="w-full text-[14px] text-text-body placeholder-[#CCCCCC] bg-[#F4F4F4] border border-border rounded-xl pl-10 pr-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary"
              />
            </div>
            <p className="text-[12px] text-text-placeholder mt-1">
              Adding a website lets us auto-enrich the company profile — competitors, tech stack, market position.
            </p>
          </div>
          <div>
            <label className="block text-[13px] font-medium text-text-body mb-1">
              Industry
            </label>
            <input
              type="text"
              value={newClientIndustry}
              onChange={(e) => setNewClientIndustry(e.target.value)}
              placeholder="e.g. Financial Services, Healthcare"
              className="w-full text-[14px] text-text-body placeholder-[#CCCCCC] bg-[#F4F4F4] border border-border rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary"
            />
          </div>
        </div>
      )}
    </div>
  )
}

// =============================================================================
// Step 3: Stakeholder
// =============================================================================

function StepStakeholder({
  stakeholders,
  sFirstName,
  setSFirstName,
  sLastName,
  setSLastName,
  sEmail,
  setSEmail,
  sLinkedin,
  setSLinkedin,
  sRole,
  setSRole,
  sType,
  setSType,
  addStakeholder,
  removeStakeholder,
}: {
  stakeholders: StakeholderLaunchInput[]
  sFirstName: string
  setSFirstName: (v: string) => void
  sLastName: string
  setSLastName: (v: string) => void
  sEmail: string
  setSEmail: (v: string) => void
  sLinkedin: string
  setSLinkedin: (v: string) => void
  sRole: string
  setSRole: (v: string) => void
  sType: string
  setSType: (v: string) => void
  addStakeholder: () => void
  removeStakeholder: (idx: number) => void
}) {
  return (
    <div className="space-y-5">
      {/* Added stakeholders */}
      {stakeholders.length > 0 && (
        <div className="space-y-2">
          <p className="text-[13px] font-medium text-text-body">
            Added ({stakeholders.length})
          </p>
          {stakeholders.map((s, i) => (
            <div
              key={i}
              className="flex items-center justify-between bg-[#F4F4F4] rounded-lg px-3 py-2"
            >
              <div className="flex items-center gap-2">
                <span className="text-[14px] font-medium text-text-body">
                  {s.first_name} {s.last_name}
                </span>
                {s.role && (
                  <span className="text-[12px] text-text-placeholder">{s.role}</span>
                )}
                <span className="text-[11px] bg-[#E8F5E9] text-[#25785A] px-2 py-0.5 rounded-full">
                  {s.stakeholder_type || 'champion'}
                </span>
                {s.linkedin_url && (
                  <Linkedin className="w-3.5 h-3.5 text-text-placeholder" />
                )}
              </div>
              <button
                onClick={() => removeStakeholder(i)}
                className="text-text-placeholder hover:text-red-500 transition-colors p-1"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Form */}
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-[13px] font-medium text-text-body mb-1">
              First Name *
            </label>
            <input
              type="text"
              value={sFirstName}
              onChange={(e) => setSFirstName(e.target.value)}
              placeholder="Jane"
              className="w-full text-[14px] text-text-body placeholder-[#CCCCCC] bg-[#F4F4F4] border border-border rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary"
            />
          </div>
          <div>
            <label className="block text-[13px] font-medium text-text-body mb-1">
              Last Name *
            </label>
            <input
              type="text"
              value={sLastName}
              onChange={(e) => setSLastName(e.target.value)}
              placeholder="Smith"
              className="w-full text-[14px] text-text-body placeholder-[#CCCCCC] bg-[#F4F4F4] border border-border rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary"
            />
          </div>
        </div>

        <div>
          <label className="block text-[13px] font-medium text-text-body mb-1">
            Email
          </label>
          <input
            type="email"
            value={sEmail}
            onChange={(e) => setSEmail(e.target.value)}
            placeholder="jane@acme.com"
            className="w-full text-[14px] text-text-body placeholder-[#CCCCCC] bg-[#F4F4F4] border border-border rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary"
          />
        </div>

        <div>
          <label className="block text-[13px] font-medium text-text-body mb-1">
            LinkedIn URL
          </label>
          <div className="relative">
            <Linkedin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-placeholder" />
            <input
              type="text"
              value={sLinkedin}
              onChange={(e) => setSLinkedin(e.target.value)}
              placeholder="https://linkedin.com/in/janesmith"
              className="w-full text-[14px] text-text-body placeholder-[#CCCCCC] bg-[#F4F4F4] border border-border rounded-xl pl-10 pr-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary"
            />
          </div>
          <p className="text-[12px] text-text-placeholder mt-1">
            A LinkedIn profile lets us build a rich intelligence profile — decision authority, org influence, professional context.
          </p>
        </div>

        <div>
          <label className="block text-[13px] font-medium text-text-body mb-1">
            Role
          </label>
          <input
            type="text"
            value={sRole}
            onChange={(e) => setSRole(e.target.value)}
            placeholder="VP of Operations"
            className="w-full text-[14px] text-text-body placeholder-[#CCCCCC] bg-[#F4F4F4] border border-border rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary"
          />
        </div>

        <div>
          <label className="block text-[13px] font-medium text-text-body mb-1.5">
            Type
          </label>
          <div className="flex flex-wrap gap-2">
            {STAKEHOLDER_TYPES.map((t) => (
              <button
                key={t.value}
                onClick={() => setSType(t.value)}
                className={`px-3 py-1.5 rounded-full text-[13px] font-medium transition-all ${
                  sType === t.value
                    ? 'bg-brand-primary text-white'
                    : 'bg-[#F0F0F0] text-[#666666] hover:bg-border'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={addStakeholder}
          disabled={!sFirstName.trim() || !sLastName.trim()}
          className="flex items-center gap-1.5 text-[14px] font-medium text-brand-primary hover:text-[#25785A] disabled:text-[#CCCCCC] disabled:cursor-not-allowed transition-colors mt-2"
        >
          <Plus className="w-4 h-4" />
          Add Stakeholder
        </button>
      </div>

      {stakeholders.length === 0 && (
        <p className="text-[13px] text-text-placeholder text-center pt-2">
          You can skip this step and add stakeholders later from the workspace.
        </p>
      )}
    </div>
  )
}

// =============================================================================
// Step 4: Launch Summary
// =============================================================================

function StepSummary({
  projectName,
  problemDescription,
  clientMode,
  selectedClient,
  newClientName,
  newClientWebsite,
  stakeholders,
  hasLinkedin,
  clientWebsite,
  autoDiscovery,
  setAutoDiscovery,
}: {
  projectName: string
  problemDescription: string
  clientMode: ClientMode
  selectedClient: ClientSummary | null
  newClientName: string
  newClientWebsite: string
  stakeholders: StakeholderLaunchInput[]
  hasLinkedin: boolean
  clientWebsite?: string
  autoDiscovery: boolean
  setAutoDiscovery: (v: boolean) => void
}) {
  const clientLabel =
    clientMode === 'existing'
      ? selectedClient?.name || 'Selected client'
      : clientMode === 'new'
        ? newClientName
        : null

  const pipelineSteps = [
    {
      label: 'Signal Processing',
      active: !!problemDescription.trim(),
      inactive: 'No project description provided',
    },
    {
      label: 'Client Enrichment',
      active: !!clientWebsite,
      inactive: 'No website provided',
    },
    {
      label: 'Stakeholder Intelligence',
      active: hasLinkedin,
      inactive: 'No LinkedIn profiles provided',
    },
    {
      label: 'Foundation Analysis',
      active: !!problemDescription.trim(),
      inactive: 'Requires signal processing',
    },
    {
      label: 'Discovery Readiness',
      active: !!problemDescription.trim(),
      inactive: 'Requires foundation',
    },
    {
      label: 'Discovery Research',
      active: autoDiscovery,
      inactive: autoDiscovery ? 'If readiness score >= 60' : 'Auto-discovery off',
      cost: autoDiscovery ? '~$1.00' : undefined,
    },
  ]

  return (
    <div className="space-y-5">
      {/* Review cards */}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-[#F4F4F4] rounded-xl p-3">
          <div className="flex items-center gap-2 mb-1.5">
            <FileText className="w-4 h-4 text-brand-primary" />
            <span className="text-[12px] font-semibold text-[#666666] uppercase">Project</span>
          </div>
          <p className="text-[14px] font-semibold text-text-body truncate">{projectName}</p>
          {problemDescription && (
            <p className="text-[12px] text-text-placeholder mt-1 line-clamp-2">
              {problemDescription.slice(0, 80)}...
            </p>
          )}
        </div>

        <div className="bg-[#F4F4F4] rounded-xl p-3">
          <div className="flex items-center gap-2 mb-1.5">
            <Building2 className="w-4 h-4 text-brand-primary" />
            <span className="text-[12px] font-semibold text-[#666666] uppercase">Client</span>
          </div>
          {clientLabel ? (
            <>
              <p className="text-[14px] font-semibold text-text-body truncate">{clientLabel}</p>
              {(clientWebsite || newClientWebsite) && (
                <p className="text-[12px] text-text-placeholder mt-1 truncate">
                  {clientWebsite || newClientWebsite}
                </p>
              )}
            </>
          ) : (
            <p className="text-[13px] text-text-placeholder">None — skip</p>
          )}
        </div>

        <div className="bg-[#F4F4F4] rounded-xl p-3">
          <div className="flex items-center gap-2 mb-1.5">
            <Users className="w-4 h-4 text-brand-primary" />
            <span className="text-[12px] font-semibold text-[#666666] uppercase">Stakeholders</span>
          </div>
          {stakeholders.length > 0 ? (
            <>
              <p className="text-[14px] font-semibold text-text-body">
                {stakeholders.length} contact{stakeholders.length !== 1 ? 's' : ''}
              </p>
              <p className="text-[12px] text-text-placeholder mt-1 truncate">
                {stakeholders.map((s) => s.first_name).join(', ')}
              </p>
            </>
          ) : (
            <p className="text-[13px] text-text-placeholder">None — skip</p>
          )}
        </div>
      </div>

      {/* Pipeline preview */}
      <div>
        <p className="text-[13px] font-semibold text-text-body mb-3">Pipeline Steps</p>
        <div className="space-y-2">
          {pipelineSteps.map((ps) => (
            <div key={ps.label} className="flex items-center gap-3">
              <div
                className={`w-2 h-2 rounded-full flex-shrink-0 ${
                  ps.active ? 'bg-brand-primary' : 'bg-border'
                }`}
              />
              <span
                className={`text-[14px] ${
                  ps.active ? 'text-text-body font-medium' : 'text-text-placeholder'
                }`}
              >
                {ps.label}
              </span>
              {!ps.active && (
                <span className="text-[12px] text-[#CCCCCC]">{ps.inactive}</span>
              )}
              {ps.cost && (
                <span className="text-[12px] text-text-placeholder ml-auto">{ps.cost}</span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Auto-discovery toggle */}
      <div className="flex items-start gap-3 bg-[#F4F4F4] rounded-xl p-4">
        <button
          onClick={() => setAutoDiscovery(!autoDiscovery)}
          className="flex-shrink-0 mt-0.5"
        >
          {autoDiscovery ? (
            <ToggleRight className="w-8 h-5 text-brand-primary" />
          ) : (
            <ToggleLeft className="w-8 h-5 text-[#CCCCCC]" />
          )}
        </button>
        <div>
          <p className="text-[14px] font-medium text-text-body">
            Auto-run discovery research
          </p>
          <p className="text-[12px] text-text-placeholder mt-0.5">
            Runs if readiness score {'>'}= 60. Estimated cost: ~$1.00
          </p>
        </div>
      </div>
    </div>
  )
}
