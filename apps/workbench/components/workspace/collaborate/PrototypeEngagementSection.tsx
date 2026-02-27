'use client'

import { useState } from 'react'
import { Layers, ChevronDown, ChevronRight, Sparkles, ExternalLink } from 'lucide-react'
import { useCollaborationHistory } from '@/lib/hooks/use-api'

interface PrototypeEngagementSectionProps {
  projectId: string
}

export function PrototypeEngagementSection({ projectId }: PrototypeEngagementSectionProps) {
  const [isOpen, setIsOpen] = useState(false)
  const { data: history } = useCollaborationHistory(projectId)

  // Extract prototype-related touchpoints as session proxies
  const protoTouchpoints = (history?.touchpoints ?? []).filter(
    tp => tp.type === 'prototype_review' || tp.type === 'feedback_session'
  )

  return (
    <div className="bg-white rounded-2xl border border-border shadow-sm overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-surface-page transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <Layers className="w-4 h-4 text-brand-primary" />
          <span className="text-[11px] uppercase tracking-wider text-text-placeholder font-semibold">
            Prototype Engagement
          </span>
          {protoTouchpoints.length > 0 && (
            <span className="px-1.5 py-0.5 bg-brand-primary-light text-[#25785A] text-[10px] font-bold rounded-full min-w-[18px] text-center">
              {protoTouchpoints.length}
            </span>
          )}
        </div>
        {isOpen ? <ChevronDown className="w-4 h-4 text-text-placeholder" /> : <ChevronRight className="w-4 h-4 text-text-placeholder" />}
      </button>

      {isOpen && (
        <div className="px-5 pb-4 space-y-3">
          {protoTouchpoints.length === 0 ? (
            <div className="text-center py-4">
              <Layers className="w-8 h-8 mx-auto mb-2 text-border" />
              <p className="text-[12px] text-text-placeholder">No prototype sessions yet</p>
              <p className="text-[11px] text-[#CCCCCC] mt-1">
                Sessions will appear here after running prototype reviews
              </p>
            </div>
          ) : (
            <>
              {/* Sessions list */}
              <div className="space-y-2">
                {protoTouchpoints.map((tp, i) => (
                  <div key={tp.id} className="bg-surface-muted rounded-lg p-3 flex items-center justify-between">
                    <div className="flex items-center gap-3 min-w-0">
                      <span className="text-[11px] font-medium text-text-placeholder flex-shrink-0">
                        #{tp.sequence_number}
                      </span>
                      <span className="text-sm text-text-body truncate">{tp.title}</span>
                      <span className="text-[11px] text-text-placeholder flex-shrink-0">
                        {tp.completed_at
                          ? new Date(tp.completed_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                          : 'In progress'
                        }
                      </span>
                    </div>
                    <button className="text-[11px] text-brand-primary hover:text-[#25785A] font-medium flex items-center gap-1 flex-shrink-0">
                      View
                      <ExternalLink className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>

              {/* Summary stats */}
              {history && (
                <div className="bg-brand-primary-light rounded-xl p-4 border border-brand-primary/15">
                  <div className="flex items-center gap-2 mb-2">
                    <Sparkles className="w-4 h-4 text-brand-primary" />
                    <span className="text-[12px] font-medium text-text-body">Engagement Summary</span>
                  </div>
                  <p className="text-[12px] text-[#666666]">
                    {history.total_features_extracted} features extracted across {protoTouchpoints.length} session{protoTouchpoints.length > 1 ? 's' : ''}
                    {history.total_items_confirmed > 0 && `, ${history.total_items_confirmed} items confirmed`}
                  </p>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
