'use client'

import { useState, useEffect } from 'react'
import { X, FileText, Link2, Trash2, Sparkles, ExternalLink, Loader2 } from 'lucide-react'
import type { KnowledgeItem } from '@/types/workspace'
import { generateProcessDocument } from '@/lib/api'

interface ClientProject {
  id: string
  name: string
}

interface KnowledgeItemDetailDrawerProps {
  item: KnowledgeItem
  category: 'business_processes' | 'sops' | 'tribal_knowledge'
  onClose: () => void
  onDelete?: (itemId: string) => void
  clientId?: string
  clientProjects?: ClientProject[]
  onProcessDocGenerated?: () => void
}

const CATEGORY_LABELS: Record<string, string> = {
  business_processes: 'Business Process',
  sops: 'SOP / Standard',
  tribal_knowledge: 'Tribal Knowledge',
}

const SOURCE_LABELS: Record<string, string> = {
  signal: 'Signal Extraction',
  stakeholder: 'Stakeholder',
  ai_inferred: 'AI Inferred',
  manual: 'Manual Entry',
}

const CONFIDENCE_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  high: { bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]', label: 'High Confidence' },
  medium: { bg: 'bg-[#F0F0F0]', text: 'text-[#666]', label: 'Medium Confidence' },
  low: { bg: 'bg-[#F0F0F0]', text: 'text-[#999]', label: 'Low Confidence' },
}

type TabId = 'overview' | 'evidence' | 'related'

export function KnowledgeItemDetailDrawer({
  item,
  category,
  onClose,
  onDelete,
  clientId,
  clientProjects,
  onProcessDocGenerated,
}: KnowledgeItemDetailDrawerProps) {
  const [activeTab, setActiveTab] = useState<TabId>('overview')
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [existingDocId, setExistingDocId] = useState<string | null>(null)
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null)
  const [showProjectPicker, setShowProjectPicker] = useState(false)

  const conf = CONFIDENCE_STYLES[item.confidence] || CONFIDENCE_STYLES.medium
  const tabs: { id: TabId; label: string }[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'evidence', label: 'Evidence' },
    { id: 'related', label: 'Related' },
  ]

  const projects = clientProjects || []

  // Auto-select project if only one
  useEffect(() => {
    if (projects.length === 1) {
      setSelectedProjectId(projects[0].id)
    }
  }, [projects])

  const canGenerate = category === 'business_processes' || category === 'sops'

  const handleGenerate = async (projectId: string) => {
    setGenerating(true)
    setShowProjectPicker(false)
    try {
      const doc = await generateProcessDocument({
        project_id: projectId,
        client_id: clientId,
        source_kb_category: category,
        source_kb_item_id: item.id,
      })
      setExistingDocId(doc.id)
      onProcessDocGenerated?.()
    } catch (err: unknown) {
      // If 409, doc already exists
      if (err && typeof err === 'object' && 'message' in err) {
        const msg = (err as { message: string }).message
        if (msg.includes('409') || msg.includes('already exists')) {
          // Try to find the existing doc
          console.warn('Process doc already exists for this KB item')
        }
      }
      console.error('Failed to generate process document:', err)
    } finally {
      setGenerating(false)
    }
  }

  const handleGenerateClick = () => {
    if (selectedProjectId) {
      handleGenerate(selectedProjectId)
    } else if (projects.length > 1) {
      setShowProjectPicker(true)
    }
  }

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/20 z-40" onClick={onClose} />

      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-[560px] max-w-[90vw] bg-white shadow-xl z-50 flex flex-col">
        {/* Header */}
        <div className="flex items-start justify-between px-6 py-5 border-b border-border">
          <div className="flex-1 min-w-0 mr-4">
            <p className="text-[14px] font-semibold text-[#333] line-clamp-2 leading-snug">
              {item.text}
            </p>
            <div className="flex items-center gap-2 mt-2">
              <span className="px-2 py-0.5 text-[10px] font-medium text-[#666] bg-[#F0F0F0] rounded-md">
                {CATEGORY_LABELS[category] || category}
              </span>
              <span className="px-2 py-0.5 text-[10px] font-medium text-[#666] bg-[#F0F0F0] rounded-md">
                {SOURCE_LABELS[item.source] || item.source}
              </span>
              <span className={`px-2 py-0.5 text-[10px] font-medium rounded-md ${conf.bg} ${conf.text}`}>
                {conf.label}
              </span>
            </div>
          </div>
          <button onClick={onClose} className="p-1 text-[#999] hover:text-[#666] transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="border-b border-border px-6">
          <div className="flex gap-5">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`py-2.5 text-[12px] font-medium border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'text-brand-primary border-brand-primary'
                    : 'text-[#999] border-transparent hover:text-[#666]'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {activeTab === 'overview' && (
            <div className="space-y-5">
              {/* Full Text */}
              <div>
                <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide mb-1.5">Content</p>
                <p className="text-[13px] text-[#333] leading-relaxed">{item.text}</p>
              </div>

              {/* Sub-category */}
              {item.category && (
                <div>
                  <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide mb-1">Category</p>
                  <span className="px-2 py-0.5 text-[11px] text-[#666] bg-[#F0F0F0] rounded-md">
                    {item.category}
                  </span>
                </div>
              )}

              {/* Source Detail */}
              {item.source_detail && (
                <div>
                  <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide mb-1">Source Detail</p>
                  <p className="text-[13px] text-[#666]">{item.source_detail}</p>
                </div>
              )}

              {/* Stakeholder Attribution */}
              {item.stakeholder_name && (
                <div>
                  <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide mb-1">Attributed To</p>
                  <p className="text-[13px] text-[#333] font-medium">{item.stakeholder_name}</p>
                </div>
              )}

              {/* Confidence */}
              <div>
                <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide mb-1">Confidence Level</p>
                <span className={`px-2.5 py-1 text-[12px] font-medium rounded-lg ${conf.bg} ${conf.text}`}>
                  {conf.label}
                </span>
              </div>

              {/* Capture Date */}
              {item.captured_at && (
                <div>
                  <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide mb-1">Captured</p>
                  <p className="text-[13px] text-[#666]">
                    {new Date(item.captured_at).toLocaleDateString('en-US', {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'evidence' && (
            <div className="space-y-4">
              {item.source_signal_id ? (
                <div className="bg-[#F4F4F4] rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <FileText className="w-4 h-4 text-[#666]" />
                    <p className="text-[12px] font-semibold text-[#333]">Source Signal</p>
                  </div>
                  <p className="text-[12px] text-[#666]">
                    Signal ID: <span className="font-mono text-[11px]">{item.source_signal_id}</span>
                  </p>
                  {item.source_detail && (
                    <p className="text-[12px] text-[#666] mt-1">{item.source_detail}</p>
                  )}
                </div>
              ) : (
                <div className="text-center py-8">
                  <FileText className="w-6 h-6 text-[#CCC] mx-auto mb-2" />
                  <p className="text-[13px] text-[#666]">No linked signal evidence</p>
                  <p className="text-[12px] text-[#999] mt-1">
                    {item.source === 'manual' ? 'This item was manually entered' : 'Source signal not tracked'}
                  </p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'related' && (
            <div className="space-y-4">
              {item.related_entity_ids && item.related_entity_ids.length > 0 ? (
                <div>
                  <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide mb-2">Linked Entities</p>
                  <div className="space-y-1.5">
                    {item.related_entity_ids.map((entityId) => (
                      <div key={entityId} className="flex items-center gap-2 bg-[#F4F4F4] rounded-lg px-3 py-2">
                        <Link2 className="w-3.5 h-3.5 text-[#999]" />
                        <span className="text-[12px] text-[#666] font-mono">{entityId.slice(0, 8)}...</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="text-center py-8">
                  <Link2 className="w-6 h-6 text-[#CCC] mx-auto mb-2" />
                  <p className="text-[13px] text-[#666]">No related entities</p>
                  <p className="text-[12px] text-[#999] mt-1">
                    This item hasn&apos;t been linked to features, workflows, or data entities yet
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="border-t border-border px-6 py-4">
          <div className="flex items-center justify-between">
            {/* Generate / View Process Doc */}
            {canGenerate && projects.length > 0 && (
              <div className="flex-1">
                {existingDocId ? (
                  <button
                    onClick={() => onProcessDocGenerated?.()}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-[#25785A] bg-[#E8F5E9] rounded-lg hover:bg-[#D0EDD9] transition-colors"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    View Document
                  </button>
                ) : generating ? (
                  <div className="flex items-center gap-2 text-[12px] text-[#666]">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    Generating document...
                  </div>
                ) : showProjectPicker ? (
                  <div className="space-y-2">
                    <p className="text-[11px] text-[#999]">Select project for context:</p>
                    <div className="flex flex-wrap gap-1.5">
                      {projects.map((p) => (
                        <button
                          key={p.id}
                          onClick={() => handleGenerate(p.id)}
                          className="px-2.5 py-1 text-[11px] font-medium text-[#666] bg-[#F0F0F0] rounded-lg hover:bg-[#E8F5E9] hover:text-[#25785A] transition-colors"
                        >
                          {p.name}
                        </button>
                      ))}
                    </div>
                  </div>
                ) : (
                  <button
                    onClick={handleGenerateClick}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-white bg-brand-primary rounded-lg hover:bg-[#25785A] transition-colors"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    Generate Document
                  </button>
                )}
              </div>
            )}

            {/* Delete */}
            {onDelete && (
              <div>
                {confirmDelete ? (
                  <div className="flex items-center gap-3">
                    <p className="text-[12px] text-[#666]">Delete?</p>
                    <button
                      onClick={() => setConfirmDelete(false)}
                      className="px-3 py-1.5 text-[12px] text-[#666] hover:text-[#333] transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => onDelete(item.id)}
                      className="px-3 py-1.5 text-[12px] font-medium text-red-600 bg-red-50 rounded-lg hover:bg-red-100 transition-colors"
                    >
                      Confirm
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setConfirmDelete(true)}
                    className="flex items-center gap-1.5 text-[12px] text-[#999] hover:text-red-500 transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    Delete
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
