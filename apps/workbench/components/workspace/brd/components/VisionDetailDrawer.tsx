'use client'

import { useState, useEffect } from 'react'
import {
  X,
  Eye,
  Clock,
  Sparkles,
  FileText,
  TrendingUp,
  Lightbulb,
  Pencil,
} from 'lucide-react'
import { getVisionDetail, updateProjectVision } from '@/lib/api'
import { formatDate } from '@/lib/date-utils'
import type { VisionDetailData, VisionAnalysis, RevisionEntry } from '@/types/workspace'

type TabId = 'current' | 'evolution' | 'sources'

interface VisionDetailDrawerProps {
  projectId: string
  initialVision?: string | null
  onClose: () => void
  onVisionUpdated?: (vision: string) => void
}

const TABS: { id: TabId; label: string; icon: typeof Eye }[] = [
  { id: 'current', label: 'Current', icon: Eye },
  { id: 'evolution', label: 'Evolution', icon: Clock },
  { id: 'sources', label: 'Sources', icon: FileText },
]

const CLARITY_DIMENSIONS: { key: keyof Pick<VisionAnalysis, 'conciseness' | 'measurability' | 'completeness' | 'alignment'>; label: string; icon: typeof TrendingUp }[] = [
  { key: 'conciseness', label: 'Conciseness', icon: TrendingUp },
  { key: 'measurability', label: 'Measurability', icon: TrendingUp },
  { key: 'completeness', label: 'Completeness', icon: TrendingUp },
  { key: 'alignment', label: 'Feature Alignment', icon: TrendingUp },
]

function ScoreBar({ label, score }: { label: string; score: number }) {
  const percent = Math.round(score * 100)
  const color = percent >= 80 ? '#25785A' : percent >= 60 ? '#3FAF7A' : '#999999'

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-[12px] text-[#666666]">{label}</span>
        <span className="text-[12px] font-medium" style={{ color }}>
          {percent}%
        </span>
      </div>
      <div className="h-2 bg-[#F0F0F0] rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${percent}%`, backgroundColor: color }}
        />
      </div>
    </div>
  )
}

export function VisionDetailDrawer({
  projectId,
  initialVision,
  onClose,
  onVisionUpdated,
}: VisionDetailDrawerProps) {
  const [activeTab, setActiveTab] = useState<TabId>('current')
  const [detail, setDetail] = useState<VisionDetailData | null>(null)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(initialVision || '')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getVisionDetail(projectId)
      .then((data) => {
        if (!cancelled) {
          setDetail(data)
          setDraft(data.vision || '')
        }
      })
      .catch((err) => {
        console.error('Failed to load vision detail:', err)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [projectId])

  const handleSave = async () => {
    setSaving(true)
    try {
      await updateProjectVision(projectId, draft)
      onVisionUpdated?.(draft)
      setEditing(false)
      // Reload to get fresh analysis
      const data = await getVisionDetail(projectId)
      setDetail(data)
    } catch (err) {
      console.error('Failed to update vision:', err)
    } finally {
      setSaving(false)
    }
  }

  const analysis = detail?.vision_analysis || null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 z-40 transition-opacity"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-[560px] max-w-full bg-white shadow-xl z-50 flex flex-col animate-slide-in-right">
        {/* Header */}
        <div className="flex-shrink-0 border-b border-[#E5E5E5] px-6 py-4">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3 min-w-0 flex-1">
              <div className="w-8 h-8 rounded-full bg-[#0A1E2F] flex items-center justify-center flex-shrink-0 mt-0.5">
                <Eye className="w-4 h-4 text-white" />
              </div>
              <div className="min-w-0">
                <p className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-1">
                  Vision Statement
                </p>
                <h2 className="text-[15px] font-semibold text-[#333333] leading-snug">
                  Product Vision
                </h2>
                {detail?.vision_updated_at && (
                  <p className="text-[11px] text-[#999999] mt-1">
                    Last updated {formatDate(detail.vision_updated_at)}
                  </p>
                )}
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors flex-shrink-0"
            >
              <X className="w-4 h-4 text-[#999999]" />
            </button>
          </div>

          {/* Tabs */}
          <div className="flex gap-1 mt-4">
            {TABS.map((tab) => {
              const Icon = tab.icon
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium rounded-lg transition-colors ${
                    activeTab === tab.id
                      ? 'bg-[#E8F5E9] text-[#25785A]'
                      : 'text-[#999999] hover:text-[#666666] hover:bg-[#F0F0F0]'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {tab.label}
                </button>
              )
            })}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[#3FAF7A]" />
            </div>
          ) : (
            <>
              {activeTab === 'current' && (
                <CurrentTab
                  detail={detail}
                  analysis={analysis}
                  editing={editing}
                  draft={draft}
                  saving={saving}
                  onDraftChange={setDraft}
                  onEdit={() => { setDraft(detail?.vision || ''); setEditing(true) }}
                  onSave={handleSave}
                  onCancel={() => { setEditing(false); setDraft(detail?.vision || '') }}
                />
              )}
              {activeTab === 'evolution' && (
                <EvolutionTab revisions={detail?.revisions || []} />
              )}
              {activeTab === 'sources' && (
                <SourcesTab />
              )}
            </>
          )}
        </div>
      </div>
    </>
  )
}

// ============================================================================
// Current Tab
// ============================================================================

function CurrentTab({
  detail,
  analysis,
  editing,
  draft,
  saving,
  onDraftChange,
  onEdit,
  onSave,
  onCancel,
}: {
  detail: VisionDetailData | null
  analysis: VisionAnalysis | null
  editing: boolean
  draft: string
  saving: boolean
  onDraftChange: (val: string) => void
  onEdit: () => void
  onSave: () => void
  onCancel: () => void
}) {
  return (
    <div className="space-y-6">
      {/* Vision Text */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-[13px] font-semibold text-[#333333]">Vision Statement</h3>
          {!editing && (
            <button
              onClick={onEdit}
              className="inline-flex items-center gap-1 text-[11px] text-[#999999] hover:text-[#3FAF7A] transition-colors"
            >
              <Pencil className="w-3 h-3" />
              Edit
            </button>
          )}
        </div>
        {editing ? (
          <div className="space-y-3">
            <textarea
              value={draft}
              onChange={(e) => onDraftChange(e.target.value)}
              className="w-full p-3 text-[14px] text-[#333333] border border-[#E5E5E5] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#3FAF7A]/30 focus:border-[#3FAF7A] resize-y min-h-[100px]"
              placeholder="Describe the product vision..."
              autoFocus
            />
            <div className="flex items-center gap-2">
              <button
                onClick={onSave}
                disabled={saving}
                className="px-3 py-1.5 text-[12px] font-medium text-white bg-[#3FAF7A] rounded-xl hover:bg-[#25785A] transition-colors disabled:opacity-50"
              >
                {saving ? 'Saving...' : 'Save'}
              </button>
              <button
                onClick={onCancel}
                className="px-3 py-1.5 text-[12px] font-medium text-[#666666] bg-white border border-[#E5E5E5] rounded-xl hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
            </div>
            <p className="text-[11px] text-[#999999]">
              Saving will trigger an AI clarity analysis (~3 seconds).
            </p>
          </div>
        ) : (
          <div className="bg-[#F9F9F9] rounded-xl p-4">
            {detail?.vision ? (
              <p className="text-[14px] text-[#333333] leading-relaxed">{detail.vision}</p>
            ) : (
              <p className="text-[13px] text-[#999999] italic">
                No vision statement yet. Click Edit to add one.
              </p>
            )}
          </div>
        )}
      </div>

      {/* Clarity Analysis */}
      {analysis && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="w-4 h-4 text-[#3FAF7A]" />
            <h3 className="text-[13px] font-semibold text-[#333333]">Clarity Analysis</h3>
            <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${
              analysis.overall_score >= 0.8
                ? 'bg-[#E8F5E9] text-[#25785A]'
                : analysis.overall_score >= 0.6
                  ? 'bg-[#E8F5E9] text-[#3FAF7A]'
                  : 'bg-[#F0F0F0] text-[#999999]'
            }`}>
              {Math.round(analysis.overall_score * 100)}% overall
            </span>
          </div>

          {/* Score Bars */}
          <div className="space-y-3 mb-4">
            {CLARITY_DIMENSIONS.map((dim) => (
              <ScoreBar
                key={dim.key}
                label={dim.label}
                score={analysis[dim.key]}
              />
            ))}
          </div>

          {/* Summary */}
          {analysis.summary && (
            <div className="bg-[#F9F9F9] rounded-xl p-3 mb-4">
              <p className="text-[13px] text-[#666666] leading-relaxed">{analysis.summary}</p>
            </div>
          )}

          {/* Suggestions */}
          {analysis.suggestions && analysis.suggestions.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <Lightbulb className="w-3.5 h-3.5 text-[#3FAF7A]" />
                <h4 className="text-[12px] font-medium text-[#333333]">Improvement Suggestions</h4>
              </div>
              <ul className="space-y-2">
                {analysis.suggestions.map((suggestion, i) => (
                  <li key={i} className="flex items-start gap-2 text-[13px] text-[#666666]">
                    <span className="w-5 h-5 rounded-full bg-[#F0F0F0] flex items-center justify-center text-[10px] font-medium text-[#999999] flex-shrink-0 mt-0.5">
                      {i + 1}
                    </span>
                    {suggestion}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Feature Count Context */}
      {detail && detail.total_features > 0 && (
        <div className="bg-[#F9F9F9] rounded-xl p-3">
          <div className="flex items-center gap-2 text-[12px] text-[#666666]">
            <FileText className="w-3.5 h-3.5 text-[#999999]" />
            <span>
              Vision evaluated against <strong>{detail.total_features}</strong> feature{detail.total_features !== 1 ? 's' : ''} in this project.
            </span>
          </div>
        </div>
      )}

      {/* No analysis yet */}
      {!analysis && detail?.vision && (
        <div className="bg-[#F9F9F9] rounded-xl p-4 text-center">
          <Sparkles className="w-5 h-5 text-[#999999] mx-auto mb-2" />
          <p className="text-[13px] text-[#999999]">
            Clarity analysis not yet available. Edit and save the vision to trigger analysis.
          </p>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Evolution Tab
// ============================================================================

function EvolutionTab({ revisions }: { revisions: RevisionEntry[] }) {
  if (revisions.length === 0) {
    return (
      <div className="text-center py-12">
        <Clock className="w-6 h-6 text-[#999999] mx-auto mb-2" />
        <p className="text-[13px] text-[#999999]">No revision history yet.</p>
        <p className="text-[11px] text-[#999999] mt-1">Edit the vision to start tracking changes.</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <h3 className="text-[13px] font-semibold text-[#333333]">Vision Evolution</h3>
      <div className="relative">
        {/* Timeline line */}
        <div className="absolute left-3 top-2 bottom-2 w-px bg-[#E5E5E5]" />

        <div className="space-y-4">
          {revisions.map((rev, i) => (
            <div key={i} className="flex gap-3 relative">
              {/* Dot */}
              <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 z-10 ${
                i === 0 ? 'bg-[#3FAF7A]' : 'bg-[#E5E5E5]'
              }`}>
                <span className={`text-[9px] font-bold ${i === 0 ? 'text-white' : 'text-[#999999]'}`}>
                  {rev.revision_number}
                </span>
              </div>

              {/* Content */}
              <div className="flex-1 bg-white rounded-xl border border-[#E5E5E5] p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[11px] font-medium text-[#333333]">
                    Revision {rev.revision_number}
                  </span>
                  <span className="text-[10px] text-[#999999]">
                    {formatDate(rev.created_at)}
                  </span>
                </div>
                <p className="text-[12px] text-[#666666]">{rev.diff_summary}</p>
                {rev.revision_type && (
                  <span className="inline-block mt-1.5 text-[10px] px-1.5 py-0.5 rounded bg-[#F0F0F0] text-[#999999]">
                    {rev.revision_type}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// Sources Tab (placeholder MVP)
// ============================================================================

function SourcesTab() {
  return (
    <div className="text-center py-12">
      <FileText className="w-6 h-6 text-[#999999] mx-auto mb-2" />
      <p className="text-[13px] text-[#999999]">Evidence sources coming soon.</p>
      <p className="text-[11px] text-[#999999] mt-1">
        This will show signal citations that contributed to the vision statement.
      </p>
    </div>
  )
}
