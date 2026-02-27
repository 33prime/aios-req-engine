/**
 * EvidenceTab — Entity provenance explorer
 *
 * Left panel: entity browser (features, personas, workflows, stakeholders).
 * Right panel: evidence trail (linked memory, revisions, source signals).
 */

'use client'

import { useState, useEffect } from 'react'
import { ChevronRight, FileText, Brain, History, Upload } from 'lucide-react'
import { getEntityEvidence } from '@/lib/api'
import type { IntelEvidenceResponse } from '@/types/workspace'
import { useBRDData } from '@/lib/hooks/use-api'

interface EvidenceTabProps {
  projectId: string
}

interface EntityItem {
  id: string
  name: string
  type: string
}

interface EntityGroup {
  label: string
  type: string
  items: EntityItem[]
}

export function EvidenceTab({ projectId }: EvidenceTabProps) {
  const { data: brd, isLoading: isLoadingEntities } = useBRDData(projectId, false)
  const [selectedEntity, setSelectedEntity] = useState<EntityItem | null>(null)
  const [evidence, setEvidence] = useState<IntelEvidenceResponse | null>(null)
  const [isLoadingEvidence, setIsLoadingEvidence] = useState(false)

  // Build entity groups from BRD data
  const groups: EntityGroup[] = []
  if (brd) {
    const data = brd as unknown as Record<string, unknown>
    const features = data.features as Array<{ id: string; name: string }> | undefined
    if (features?.length) {
      groups.push({
        label: 'Features',
        type: 'feature',
        items: features.map((f) => ({ id: f.id, name: f.name, type: 'feature' })),
      })
    }
    const personas = data.personas as Array<{ id: string; name: string }> | undefined
    if (personas?.length) {
      groups.push({
        label: 'Personas',
        type: 'persona',
        items: personas.map((p) => ({ id: p.id, name: p.name, type: 'persona' })),
      })
    }
    const stakeholders = data.stakeholders as Array<{ id: string; name: string }> | undefined
    if (stakeholders?.length) {
      groups.push({
        label: 'Stakeholders',
        type: 'stakeholder',
        items: stakeholders.map((s) => ({ id: s.id, name: s.name, type: 'stakeholder' })),
      })
    }
  }

  // Load evidence when entity is selected
  useEffect(() => {
    if (!selectedEntity) {
      setEvidence(null)
      return
    }
    setIsLoadingEvidence(true)
    getEntityEvidence(projectId, selectedEntity.type, selectedEntity.id)
      .then(setEvidence)
      .catch(() => setEvidence(null))
      .finally(() => setIsLoadingEvidence(false))
  }, [projectId, selectedEntity])

  if (isLoadingEntities) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-brand-primary" />
      </div>
    )
  }

  if (groups.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-sm text-[#666666]">No entities to explore.</p>
        <p className="text-xs text-text-placeholder mt-1">Create features, personas, or workflows first.</p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-3 gap-6 min-h-[400px]">
      {/* Entity Browser (left) */}
      <div className="col-span-1 space-y-4">
        {groups.map((group) => (
          <div key={group.type}>
            <h5 className="text-[11px] font-semibold text-text-body uppercase tracking-wide mb-2">
              {group.label} ({group.items.length})
            </h5>
            <div className="space-y-1">
              {group.items.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setSelectedEntity(item)}
                  className={`w-full text-left flex items-center gap-2 px-3 py-2 rounded-lg text-[12px] transition-colors ${
                    selectedEntity?.id === item.id
                      ? 'bg-[#E8F5E9] text-[#25785A] font-medium'
                      : 'text-[#666666] hover:bg-[#F4F4F4] hover:text-text-body'
                  }`}
                >
                  <ChevronRight className="w-3 h-3 shrink-0" />
                  <span className="truncate">{item.name}</span>
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Evidence Trail (right) */}
      <div className="col-span-2">
        {!selectedEntity ? (
          <div className="flex items-center justify-center h-full text-sm text-text-placeholder">
            Select an entity to view its evidence trail
          </div>
        ) : isLoadingEvidence ? (
          <div className="flex items-center justify-center h-full">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-brand-primary" />
          </div>
        ) : evidence ? (
          <div className="space-y-5">
            {/* Entity header */}
            <div>
              <p className="text-[11px] font-semibold text-text-placeholder uppercase tracking-wide">
                {evidence.entity_type}
              </p>
              <h4 className="text-base font-semibold text-text-body">
                {evidence.entity_name || selectedEntity.name}
              </h4>
            </div>

            {/* Linked Memory */}
            {evidence.linked_memory.length > 0 && (
              <div>
                <h5 className="text-[11px] font-semibold text-text-body uppercase tracking-wide mb-2 flex items-center gap-1.5">
                  <Brain className="w-3.5 h-3.5" />
                  Linked Memory ({evidence.linked_memory.length})
                </h5>
                <div className="space-y-1.5">
                  {evidence.linked_memory.map((m) => (
                    <div key={m.id} className="bg-[#F4F4F4] rounded-lg px-3 py-2">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className={`text-[9px] font-semibold uppercase ${
                          m.node_type === 'fact' ? 'text-emerald-600' :
                          m.node_type === 'belief' ? 'text-[#0A1E2F]' : 'text-gray-500'
                        }`}>
                          {m.node_type}
                        </span>
                        {m.consultant_status && (
                          <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded ${
                            m.consultant_status === 'confirmed'
                              ? 'bg-[#E8F5E9] text-[#25785A]'
                              : 'bg-gray-100 text-gray-500'
                          }`}>
                            {m.consultant_status}
                          </span>
                        )}
                        {m.node_type !== 'fact' && (
                          <span className="text-[9px] text-text-placeholder">
                            {Math.round(m.confidence * 100)}%
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-text-body">{m.summary}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Revisions */}
            {evidence.revisions.length > 0 && (
              <div>
                <h5 className="text-[11px] font-semibold text-text-body uppercase tracking-wide mb-2 flex items-center gap-1.5">
                  <History className="w-3.5 h-3.5" />
                  Revisions ({evidence.revisions.length})
                </h5>
                <div className="space-y-1.5">
                  {evidence.revisions.map((r, i) => (
                    <div key={r.id} className="flex items-start gap-2">
                      <div className="w-1.5 h-1.5 rounded-full bg-brand-primary mt-1.5 shrink-0" />
                      <div className="min-w-0">
                        <p className="text-[11px] text-text-body">
                          {r.field_name ? `${r.field_name} updated` : `Revision v${evidence.revisions.length - i}`}
                        </p>
                        <p className="text-[10px] text-text-placeholder">
                          {new Date(r.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Source Signals */}
            {evidence.source_signals.length > 0 && (
              <div>
                <h5 className="text-[11px] font-semibold text-text-body uppercase tracking-wide mb-2 flex items-center gap-1.5">
                  <Upload className="w-3.5 h-3.5" />
                  Source Signals ({evidence.source_signals.length})
                </h5>
                <div className="space-y-1.5">
                  {evidence.source_signals.map((s) => (
                    <div key={s.id} className="bg-[#F4F4F4] rounded-lg px-3 py-2">
                      <p className="text-[11px] text-text-body">
                        {s.title || s.signal_type || 'Signal'}
                      </p>
                      <p className="text-[10px] text-text-placeholder">
                        {s.signal_type && <span className="mr-2">{s.signal_type}</span>}
                        {new Date(s.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Empty state */}
            {evidence.linked_memory.length === 0 && evidence.revisions.length === 0 && evidence.source_signals.length === 0 && (
              <div className="text-center py-8">
                <p className="text-sm text-[#666666]">No evidence trail for this entity yet.</p>
              </div>
            )}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-sm text-text-placeholder">
            Failed to load evidence
          </div>
        )}
      </div>
    </div>
  )
}
