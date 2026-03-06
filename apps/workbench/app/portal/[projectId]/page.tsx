/**
 * Client Portal Hub — Mission Control Dashboard
 *
 * Two-column layout:
 * Left: inline action cards (questions, validations), materials, team
 * Right: contribution station grid, prototype card, activity timeline
 *
 * Floating chat bubble for general portal chat.
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import {
  Monitor, ChevronDown, ChevronUp, Swords, Palette, ShieldAlert, FileText,
  Sparkles, BookOpen, Upload, Users, UserPlus, Clock,
} from 'lucide-react'
import { Spinner } from '@/components/ui/Spinner'
import { usePortal, type PortalChatConfig } from './PortalShell'
import { ConsultantBanner } from '@/components/portal/ConsultantBanner'
import { InlineActionCard } from '@/components/portal/InlineActionCard'
import { ContributionGrid } from '@/components/portal/ContributionGrid'
import { ActivityTimeline } from '@/components/portal/ActivityTimeline'
import { StationPanel } from '@/components/portal/StationPanel'
import { apiRequest } from '@/lib/api/core'
import { getTeamMembers, inviteTeamMember } from '@/lib/api/portal'
import type { StationSlug, TeamMember, TeamInviteRequest } from '@/types/portal'

// Station metadata for StationPanel
const STATION_META: Record<StationSlug, {
  icon: React.ComponentType<{ className?: string }>
  title: string
  entityLabel: string
  greeting: string
}> = {
  competitors: {
    icon: Swords,
    title: 'Competitors & Past Tools',
    entityLabel: 'Competitive Landscape',
    greeting: "Let's talk about the tools you've used before and what else is out there. What have you tried?",
  },
  design: {
    icon: Palette,
    title: 'Design Inspiration',
    entityLabel: 'Design Preferences',
    greeting: "I'd love to hear about apps and tools you enjoy using. What stands out to you?",
  },
  constraints: {
    icon: ShieldAlert,
    title: 'Constraints & Requirements',
    entityLabel: 'Business Constraints',
    greeting: "Let's document any hard constraints — compliance, budget, technical limitations, or non-negotiables.",
  },
  documents: {
    icon: FileText,
    title: 'Supporting Documents',
    entityLabel: 'Materials',
    greeting: 'Do you have any existing documentation, screenshots, or data that would help? You can upload files above.',
  },
  ai_wishlist: {
    icon: Sparkles,
    title: 'AI & Automation Wishlist',
    entityLabel: 'AI Features',
    greeting: "What tasks would you love to automate? What would AI magic look like for your workflow?",
  },
  tribal: {
    icon: BookOpen,
    title: 'Tribal Knowledge',
    entityLabel: 'Edge Cases & Gotchas',
    greeting: "Let's capture the things only experienced people know — gotchas, edge cases, and undocumented rules.",
  },
  workflow: {
    icon: Clock,
    title: 'Workflow Discussion',
    entityLabel: 'Workflows',
    greeting: "Let's talk about this workflow. Does it match how your team actually works?",
  },
  epic: {
    icon: Monitor,
    title: 'Epic Review',
    entityLabel: 'Prototype',
    greeting: "Let's discuss what you see in the prototype. What stands out?",
  },
}

// ============================================================================
// Inline Materials Section
// ============================================================================

interface ClientDoc {
  id: string
  file_name: string
  file_size: number
  file_type: string
  description?: string
  category: string
  uploaded_at: string
}

function MaterialsSection({ projectId }: { projectId: string }) {
  const [docs, setDocs] = useState<ClientDoc[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)

  const loadDocs = useCallback(async () => {
    try {
      const data = await apiRequest<ClientDoc[]>(`/portal/projects/${projectId}/files`)
      setDocs(data)
    } catch { /* ok */ }
    finally { setLoading(false) }
  }, [projectId])

  useEffect(() => { loadDocs() }, [loadDocs])

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      await fetch(`${process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000'}/v1/portal/projects/${projectId}/files`, {
        method: 'POST',
        body: formData,
        headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}` },
      })
      await loadDocs()
    } catch { /* ok */ }
    finally { setUploading(false); e.target.value = '' }
  }

  const handleDelete = async (docId: string) => {
    try {
      await apiRequest(`/portal/files/${docId}`, { method: 'DELETE' })
      await loadDocs()
    } catch { /* ok */ }
  }

  return (
    <div className="bg-surface-card border border-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-text-muted" />
          <h3 className="text-xs font-medium text-text-muted uppercase tracking-wide">
            Materials
          </h3>
        </div>
        <label className="text-xs text-brand-primary hover:text-brand-primary-hover cursor-pointer font-medium flex items-center gap-1">
          <Upload className="w-3 h-3" />
          {uploading ? 'Uploading...' : 'Upload'}
          <input type="file" onChange={handleUpload} className="hidden" disabled={uploading} />
        </label>
      </div>

      {loading ? (
        <p className="text-xs text-text-placeholder py-2">Loading...</p>
      ) : docs.length === 0 ? (
        <p className="text-xs text-text-placeholder py-2">
          No files yet. Upload documents to share with your consultant.
        </p>
      ) : (
        <div className="space-y-2">
          {docs.slice(0, 4).map((doc) => (
            <div key={doc.id} className="flex items-center gap-2 group">
              <div className="w-7 h-7 bg-surface-subtle rounded flex items-center justify-center flex-shrink-0">
                <span className="text-[8px] font-medium text-text-muted uppercase">
                  {doc.file_type?.split('/').pop()?.slice(0, 4) || 'FILE'}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs text-text-primary truncate">{doc.file_name}</p>
                <p className="text-[10px] text-text-placeholder">
                  {(doc.file_size / 1024).toFixed(0)} KB
                </p>
              </div>
              <button
                onClick={() => handleDelete(doc.id)}
                className="text-[10px] text-red-400 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-opacity"
              >
                Remove
              </button>
            </div>
          ))}
          {docs.length > 4 && (
            <p className="text-[10px] text-text-placeholder text-center">+{docs.length - 4} more</p>
          )}
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Inline Team Section
// ============================================================================

function TeamSection({ projectId, portalRole }: { projectId: string; portalRole: string }) {
  const [members, setMembers] = useState<TeamMember[]>([])
  const [loading, setLoading] = useState(true)
  const [showInvite, setShowInvite] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviting, setInviting] = useState(false)

  useEffect(() => {
    getTeamMembers(projectId)
      .then(setMembers)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [projectId])

  const handleInvite = async () => {
    if (!inviteEmail.trim()) return
    setInviting(true)
    try {
      await inviteTeamMember(projectId, { email: inviteEmail.trim() })
      setInviteEmail('')
      setShowInvite(false)
      const data = await getTeamMembers(projectId)
      setMembers(data)
    } catch { /* ok */ }
    finally { setInviting(false) }
  }

  if (portalRole !== 'client_admin') return null

  return (
    <div className="bg-surface-card border border-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Users className="w-4 h-4 text-text-muted" />
          <h3 className="text-xs font-medium text-text-muted uppercase tracking-wide">Team</h3>
        </div>
        <button
          onClick={() => setShowInvite(!showInvite)}
          className="text-xs text-brand-primary hover:text-brand-primary-hover font-medium flex items-center gap-1"
        >
          <UserPlus className="w-3 h-3" />
          Invite
        </button>
      </div>

      {/* Inline invite */}
      {showInvite && (
        <div className="flex gap-2 mb-3">
          <input
            type="email"
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
            placeholder="Email address"
            className="flex-1 text-xs px-2 py-1.5 border border-border rounded-lg focus:ring-2 focus:ring-brand-primary-ring focus:border-brand-primary"
            onKeyDown={(e) => e.key === 'Enter' && handleInvite()}
          />
          <button
            onClick={handleInvite}
            disabled={inviting || !inviteEmail.trim()}
            className="text-xs px-3 py-1.5 bg-brand-primary text-white rounded-lg hover:bg-brand-primary-hover disabled:opacity-40"
          >
            {inviting ? '...' : 'Send'}
          </button>
        </div>
      )}

      {loading ? (
        <p className="text-xs text-text-placeholder py-2">Loading...</p>
      ) : members.length === 0 ? (
        <p className="text-xs text-text-placeholder py-2">
          No team members yet. Invite stakeholders to collaborate.
        </p>
      ) : (
        <div className="space-y-2">
          {members.slice(0, 5).map((m) => {
            const name = [m.first_name, m.last_name].filter(Boolean).join(' ') || m.email
            const pct = m.total_assignments > 0
              ? Math.round((m.completed_assignments / m.total_assignments) * 100)
              : 0
            return (
              <div key={m.user_id} className="flex items-center gap-2">
                <div className="w-6 h-6 bg-surface-subtle rounded-full flex items-center justify-center flex-shrink-0">
                  <span className="text-[9px] font-medium text-text-muted">
                    {name.charAt(0).toUpperCase()}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-text-primary truncate">{name}</p>
                </div>
                {m.total_assignments > 0 && (
                  <span className="text-[10px] text-text-placeholder flex-shrink-0">{pct}%</span>
                )}
                {m.portal_role === 'client_admin' && (
                  <span className="text-[9px] bg-purple-100 text-purple-600 px-1 py-0.5 rounded flex-shrink-0">
                    Admin
                  </span>
                )}
              </div>
            )
          })}
          {members.length > 5 && (
            <p className="text-[10px] text-text-placeholder text-center">+{members.length - 5} more</p>
          )}
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Main Page
// ============================================================================

export default function PortalHubPage() {
  const router = useRouter()
  const {
    projectId,
    portalRole,
    dashboard,
    loaded,
    infoRequests,
    refreshInfoRequests,
    validationQueue,
    refreshValidation,
    projectContext,
    refreshContext,
    setChatConfig,
  } = usePortal()

  const [activeStation, setActiveStation] = useState<StationSlug | null>(null)
  const [showCompleted, setShowCompleted] = useState(false)

  const handleDataChanged = useCallback(() => {
    refreshContext()
    refreshInfoRequests()
  }, [refreshContext, refreshInfoRequests])

  // Register page-aware chat config
  useEffect(() => {
    setChatConfig({
      station: 'tribal',
      title: 'What would you like to tackle?',
      greeting: "I can help you share details about your project. What area would you like to explore — competitors, design inspiration, constraints, AI wishlist, or something else?",
    })
    return () => setChatConfig(null)
  }, [setChatConfig])

  if (!loaded) {
    return (
      <div className="flex items-center justify-center h-full">
        <Spinner size="lg" label="Loading dashboard..." />
      </div>
    )
  }

  if (!dashboard) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <p className="text-red-600 mb-2">Failed to load dashboard</p>
          <button
            onClick={() => window.location.reload()}
            className="text-sm text-brand-primary hover:underline"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  // Split info requests
  const pendingQuestions = infoRequests.filter(
    (q) => q.status !== 'complete' && q.status !== 'skipped'
  )
  const completedQuestions = infoRequests.filter(
    (q) => q.status === 'complete' || q.status === 'skipped'
  )

  // Pending validations
  const pendingValidations = validationQueue?.items ?? []

  const { prototype_status, recent_activity } = dashboard

  return (
    <div className="h-full overflow-y-auto px-8 py-8 space-y-6">
      {/* Consultant Banner — always visible */}
      <ConsultantBanner dashboard={dashboard} projectContext={projectContext} />

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Left: Actions */}
        <div className="lg:col-span-3 space-y-4">
          {/* Pending questions */}
          {pendingQuestions.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-xs font-medium text-text-muted uppercase tracking-wide">
                Questions ({pendingQuestions.length})
              </h2>
              {pendingQuestions.slice(0, 5).map((q) => (
                <InlineActionCard
                  key={q.id}
                  type="question"
                  item={q}
                  onCompleted={() => {
                    refreshInfoRequests()
                    refreshContext()
                  }}
                />
              ))}
              {pendingQuestions.length > 5 && (
                <p className="text-xs text-text-muted text-center">
                  +{pendingQuestions.length - 5} more questions
                </p>
              )}
            </div>
          )}

          {/* Pending validations */}
          {pendingValidations.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-xs font-medium text-text-muted uppercase tracking-wide">
                Validations ({pendingValidations.length})
              </h2>
              {pendingValidations.slice(0, 5).map((v) => (
                <InlineActionCard
                  key={v.id}
                  type="validation"
                  item={v}
                  projectId={projectId}
                  onCompleted={refreshValidation}
                />
              ))}
              {pendingValidations.length > 5 && (
                <p className="text-xs text-text-muted text-center">
                  +{pendingValidations.length - 5} more validations
                </p>
              )}
            </div>
          )}

          {/* Empty state — welcoming, not dead */}
          {pendingQuestions.length === 0 && pendingValidations.length === 0 && (
            <div className="bg-surface-card border border-border rounded-lg p-6 text-center">
              <div className="w-10 h-10 bg-green-50 rounded-full flex items-center justify-center mx-auto mb-2">
                <Clock className="w-5 h-5 text-brand-primary" />
              </div>
              <p className="text-sm font-medium text-text-primary">You're all caught up</p>
              <p className="text-xs text-text-muted mt-1">
                No pending questions or validations right now. Use the contribution tiles to share more context about your project.
              </p>
            </div>
          )}

          {/* Completed items (collapsed) */}
          {completedQuestions.length > 0 && (
            <div>
              <button
                onClick={() => setShowCompleted(!showCompleted)}
                className="flex items-center gap-1 text-xs text-text-muted hover:text-text-body transition-colors"
              >
                {showCompleted ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                {completedQuestions.length} completed
              </button>
              {showCompleted && (
                <div className="mt-2 space-y-1">
                  {completedQuestions.map((q) => (
                    <div key={q.id} className="text-xs text-text-muted flex items-center gap-1.5 py-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-green-400 flex-shrink-0" />
                      {q.title}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Materials (inline) */}
          <MaterialsSection projectId={projectId} />

          {/* Team (inline, admin only) */}
          <TeamSection projectId={projectId} portalRole={portalRole} />
        </div>

        {/* Right: Contribute + Status */}
        <div className="lg:col-span-2 space-y-4">
          {/* Contribution Grid */}
          <div>
            <h2 className="text-xs font-medium text-text-muted uppercase tracking-wide mb-3">
              Contribute
            </h2>
            <ContributionGrid
              projectContext={projectContext}
              dashboard={dashboard}
              onStationOpen={setActiveStation}
            />
          </div>

          {/* Prototype Card — always visible */}
          <button
            onClick={() => router.push(`/portal/${projectId}/prototype`)}
            className="w-full bg-surface-card border border-border rounded-lg p-4 text-left hover:border-brand-primary hover:shadow-sm transition-all"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-[#0A1E2F] flex items-center justify-center flex-shrink-0">
                <Monitor className="w-5 h-5 text-white" />
              </div>
              <div>
                {prototype_status ? (
                  <>
                    <p className="text-sm font-medium text-text-primary">
                      {prototype_status.status === 'deployed' ? 'Prototype Ready' : 'Prototype'}
                    </p>
                    <p className="text-xs text-brand-primary">
                      {prototype_status.deploy_url ? 'Click to review' : prototype_status.status}
                    </p>
                  </>
                ) : (
                  <>
                    <p className="text-sm font-medium text-text-primary">Prototype</p>
                    <p className="text-xs text-text-placeholder">Coming soon — your consultant is preparing it</p>
                  </>
                )}
              </div>
            </div>
          </button>

          {/* Activity Timeline — always visible */}
          {recent_activity.length > 0 ? (
            <ActivityTimeline activities={recent_activity} />
          ) : (
            <div className="bg-surface-card border border-border rounded-lg p-4">
              <h3 className="text-xs font-medium text-text-muted uppercase tracking-wide mb-2">
                Recent Activity
              </h3>
              <p className="text-xs text-text-placeholder py-2">
                No activity yet. Actions you take here will appear in this timeline.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Station Panel */}
      {activeStation && STATION_META[activeStation] && (
        <StationPanel
          onClose={() => setActiveStation(null)}
          icon={STATION_META[activeStation].icon}
          title={STATION_META[activeStation].title}
          entityLabel={STATION_META[activeStation].entityLabel}
          progress={
            projectContext?.completion_scores?.[
              activeStation === 'ai_wishlist' || activeStation === 'constraints' || activeStation === 'epic'
                ? 'tribal'
                : (activeStation as keyof typeof projectContext.completion_scores)
            ] ?? 0
          }
          station={activeStation}
          projectId={projectId}
          chatGreeting={STATION_META[activeStation].greeting}
          onDataChanged={handleDataChanged}
        />
      )}

    </div>
  )
}
