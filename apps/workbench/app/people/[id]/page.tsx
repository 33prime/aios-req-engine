'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams, useSearchParams, useRouter } from 'next/navigation'
import { Loader2 } from 'lucide-react'
import { getStakeholder, getStakeholderIntelligence, analyzeStakeholder, deleteStakeholder, updateStakeholder } from '@/lib/api'
import type { StakeholderDetail, StakeholderIntelligenceProfile } from '@/types/workspace'
import { AppSidebar } from '@/components/workspace/AppSidebar'
import { StakeholderHeader } from './components/StakeholderHeader'
import { StakeholderProfile } from './components/StakeholderProfile'
import { StakeholderEvidenceTab } from './components/StakeholderEvidenceTab'
import { StakeholderEditModal } from './components/StakeholderEditModal'

export default function PersonDetailPage() {
  const params = useParams()
  const searchParams = useSearchParams()
  const router = useRouter()
  const stakeholderId = params.id as string
  const projectId = searchParams.get('project_id') || ''

  const [stakeholder, setStakeholder] = useState<StakeholderDetail | null>(null)
  const [intelligence, setIntelligence] = useState<StakeholderIntelligenceProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [showEdit, setShowEdit] = useState(false)
  const [showEvidence, setShowEvidence] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!stakeholderId || !projectId) return
    setLoading(true)

    Promise.all([
      getStakeholder(projectId, stakeholderId, true),
      getStakeholderIntelligence(projectId, stakeholderId).catch(() => null),
    ])
      .then(([data, intel]) => {
        setStakeholder(data)
        setIntelligence(intel)
        setError(null)
      })
      .catch((err) => {
        console.error('Failed to load stakeholder:', err)
        setError('Failed to load stakeholder details')
      })
      .finally(() => setLoading(false))
  }, [stakeholderId, projectId])

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  const handleAnalyze = useCallback(async () => {
    if (!projectId || !stakeholderId || analyzing) return
    setAnalyzing(true)

    try {
      await analyzeStakeholder(projectId, stakeholderId)

      let elapsed = 0
      let lastScore: number | null = null
      let stableCount = 0

      pollRef.current = setInterval(async () => {
        elapsed += 5000
        try {
          const updated = await getStakeholderIntelligence(projectId, stakeholderId)
          if (updated) {
            setIntelligence(updated)

            if (lastScore !== null && updated.profile_completeness === lastScore) {
              stableCount++
            } else {
              stableCount = 0
            }
            lastScore = updated.profile_completeness

            getStakeholder(projectId, stakeholderId, true)
              .then(setStakeholder)
              .catch(() => {})

            if (stableCount >= 2) {
              if (pollRef.current) clearInterval(pollRef.current)
              pollRef.current = null
              setAnalyzing(false)
              return
            }
          }
        } catch {
          // Keep polling on transient errors
        }

        if (elapsed >= 120000) {
          if (pollRef.current) clearInterval(pollRef.current)
          pollRef.current = null
          setAnalyzing(false)
        }
      }, 5000)
    } catch (err) {
      console.error('Failed to trigger analysis:', err)
      setAnalyzing(false)
    }
  }, [projectId, stakeholderId, analyzing])

  const handleDelete = async () => {
    if (!projectId || !stakeholderId) return
    try {
      await deleteStakeholder(projectId, stakeholderId)
      router.push('/people')
    } catch (err) {
      console.error('Failed to delete stakeholder:', err)
    }
  }

  const handleEdit = async (data: Record<string, string>) => {
    await updateStakeholder(projectId, stakeholderId, data)
    // Show analyzing briefly — PATCH triggers re-enrichment for relevant fields
    setAnalyzing(true)
    setTimeout(async () => {
      try {
        const [updated, intel] = await Promise.all([
          getStakeholder(projectId, stakeholderId, true),
          getStakeholderIntelligence(projectId, stakeholderId).catch(() => null),
        ])
        setStakeholder(updated)
        setIntelligence(intel)
      } finally {
        setAnalyzing(false)
      }
    }, 5000)
  }

  const sidebarWidth = sidebarCollapsed ? 64 : 224

  if (!projectId && !loading) {
    return (
      <>
        <AppSidebar
          isCollapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        />
        <div
          className="min-h-screen bg-[#F4F4F4] flex items-center justify-center transition-all duration-300"
          style={{ marginLeft: sidebarWidth }}
        >
          <div className="text-center">
            <p className="text-[14px] text-[#666] mb-3">No project context — open this person from a project or client page.</p>
            <button
              onClick={() => router.push('/people')}
              className="px-6 py-3 text-[13px] font-medium text-white bg-brand-primary rounded-xl hover:bg-brand-primary-hover transition-colors"
            >
              Back to People
            </button>
          </div>
        </div>
      </>
    )
  }

  if (loading) {
    return (
      <>
        <AppSidebar
          isCollapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        />
        <div
          className="min-h-screen bg-[#F4F4F4] flex items-center justify-center transition-all duration-300"
          style={{ marginLeft: sidebarWidth }}
        >
          <div className="text-center">
            <Loader2 className="w-8 h-8 text-brand-primary animate-spin mx-auto mb-3" />
            <p className="text-[13px] text-[#999]">Loading stakeholder...</p>
          </div>
        </div>
      </>
    )
  }

  if (error || !stakeholder) {
    return (
      <>
        <AppSidebar
          isCollapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        />
        <div
          className="min-h-screen bg-[#F4F4F4] flex items-center justify-center transition-all duration-300"
          style={{ marginLeft: sidebarWidth }}
        >
          <div className="text-center">
            <p className="text-[14px] text-[#666] mb-3">{error || 'Stakeholder not found'}</p>
            <button
              onClick={() => router.push('/people')}
              className="px-6 py-3 text-[13px] font-medium text-white bg-brand-primary rounded-xl hover:bg-[#25785A] transition-colors"
            >
              Back to People
            </button>
          </div>
        </div>
      </>
    )
  }

  return (
    <>
      <AppSidebar
        isCollapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
      />
      <div
        className="min-h-screen bg-[#F4F4F4] transition-all duration-300"
        style={{ marginLeft: sidebarWidth }}
      >
        <div className="max-w-[1200px] mx-auto px-6 py-6">
          <StakeholderHeader
            stakeholder={stakeholder}
            onBack={() => router.push('/people')}
            completeness={intelligence?.profile_completeness}
            analyzing={analyzing}
            onAnalyze={handleAnalyze}
            onEdit={() => setShowEdit(true)}
            onDelete={handleDelete}
          />

          <StakeholderProfile
            stakeholder={stakeholder}
            intelligence={intelligence}
            projectId={projectId}
          />

          {/* Evidence & Provenance — collapsible */}
          <div className="mt-6">
            <button
              onClick={() => setShowEvidence(!showEvidence)}
              className="inline-flex items-center gap-1.5 text-[12px] font-medium text-[#999] hover:text-[#666] transition-colors"
            >
              <span className="text-[10px]">{showEvidence ? '▼' : '▶'}</span>
              Evidence & Provenance
            </button>
            {showEvidence && (
              <div className="mt-4">
                <StakeholderEvidenceTab projectId={projectId} stakeholderId={stakeholderId} />
              </div>
            )}
          </div>

          {stakeholder && (
            <StakeholderEditModal
              open={showEdit}
              onClose={() => setShowEdit(false)}
              onSave={handleEdit}
              stakeholder={stakeholder}
            />
          )}
        </div>
      </div>
    </>
  )
}
