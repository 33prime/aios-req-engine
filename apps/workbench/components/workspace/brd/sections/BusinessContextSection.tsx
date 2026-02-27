'use client'

import { useState, useMemo } from 'react'
import { Building2, AlertTriangle, Target, Eye, Pencil, Sparkles, Loader2, Check, X } from 'lucide-react'
import { BusinessDriverDetailDrawer } from '../components/BusinessDriverDetailDrawer'
import { DriverContainer } from '../components/DriverContainer'
import { DriverItemRow } from '../components/DriverItemRow'
import { enhanceVision } from '@/lib/api'
import type { BRDWorkspaceData, BusinessDriver, SectionScore, StakeholderBRDSummary } from '@/types/workspace'

interface BusinessContextSectionProps {
  data: BRDWorkspaceData['business_context']
  projectId: string
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
  onConfirmAll: (entityType: string, ids: string[]) => void
  onUpdateVision: (vision: string) => void
  onUpdateBackground: (background: string) => void
  onStatusClick?: (entityType: string, entityId: string, entityName: string, status?: string | null) => void
  sectionScore?: SectionScore | null
  onOpenVisionDetail?: () => void
  onOpenBackgroundDetail?: () => void
  stakeholders?: StakeholderBRDSummary[]
}

const SHOW_MAX_DRIVERS = 6

// ============================================================================
// Main Section
// ============================================================================

export function BusinessContextSection({
  data,
  projectId,
  onConfirm,
  onNeedsReview,
  onConfirmAll,
  onUpdateVision,
  onUpdateBackground,
  onStatusClick,
  sectionScore,
  onOpenVisionDetail,
  onOpenBackgroundDetail,
  stakeholders = [],
}: BusinessContextSectionProps) {
  const [editingVision, setEditingVision] = useState(false)
  const [visionDraft, setVisionDraft] = useState(data.vision || '')
  const [editingBackground, setEditingBackground] = useState(false)
  const [backgroundDraft, setBackgroundDraft] = useState(data.background || '')
  const [showAllGoals, setShowAllGoals] = useState(false)
  const [showAllPains, setShowAllPains] = useState(false)
  const [selectedDriver, setSelectedDriver] = useState<{ id: string; type: 'pain' | 'goal' | 'kpi'; data: BusinessDriver } | null>(null)

  // Which driver row is expanded inline (only one at a time)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  // Vision AI Enhance state
  const [showEnhanceMenu, setShowEnhanceMenu] = useState(false)
  const [aiSuggestion, setAiSuggestion] = useState<string | null>(null)
  const [isEnhancing, setIsEnhancing] = useState(false)
  const [enhancementError, setEnhancementError] = useState<string | null>(null)

  const handleEnhanceVision = async (type: string) => {
    setShowEnhanceMenu(false)
    setIsEnhancing(true)
    setEnhancementError(null)
    setAiSuggestion(null)
    try {
      const result = await enhanceVision(projectId, type)
      setAiSuggestion(result.suggestion)
    } catch (err) {
      setEnhancementError(err instanceof Error ? err.message : 'Enhancement failed')
    } finally {
      setIsEnhancing(false)
    }
  }

  const handleAcceptSuggestion = () => {
    if (aiSuggestion) {
      onUpdateVision(aiSuggestion)
      setAiSuggestion(null)
    }
  }

  const handleEditSuggestion = () => {
    if (aiSuggestion) {
      setVisionDraft(aiSuggestion)
      setEditingVision(true)
      setAiSuggestion(null)
    }
  }

  const handleSaveVision = () => {
    onUpdateVision(visionDraft)
    setEditingVision(false)
  }

  const handleSaveBackground = () => {
    onUpdateBackground(backgroundDraft)
    setEditingBackground(false)
  }

  const confirmedPains = data.pain_points.filter(
    (p) => p.confirmation_status === 'confirmed_consultant' || p.confirmation_status === 'confirmed_client'
  ).length
  const confirmedGoals = data.goals.filter(
    (g) => g.confirmation_status === 'confirmed_consultant' || g.confirmation_status === 'confirmed_client'
  ).length
  // Sort goals + pains by relatability_score descending (built into container)
  const sortedPains = useMemo(
    () => [...data.pain_points].sort((a, b) => (b.relatability_score ?? 0) - (a.relatability_score ?? 0)),
    [data.pain_points]
  )
  const sortedGoals = useMemo(
    () => [...data.goals].sort((a, b) => (b.relatability_score ?? 0) - (a.relatability_score ?? 0)),
    [data.goals]
  )

  const visibleGoals = showAllGoals ? sortedGoals : sortedGoals.slice(0, SHOW_MAX_DRIVERS)
  const visiblePains = showAllPains ? sortedPains : sortedPains.slice(0, SHOW_MAX_DRIVERS)

  return (
    <section id="brd-section-business-context" className="space-y-8">
      {/* Background */}
      <div>
        <h2 className="text-lg font-semibold text-text-body mb-3 flex items-center gap-2">
          <Building2 className="w-5 h-5 text-text-placeholder" />
          What drove the need for this solution
        </h2>
        <div className="bg-white rounded-2xl shadow-md border border-border p-5">
          {editingBackground ? (
            <div className="space-y-3">
              <textarea
                value={backgroundDraft}
                onChange={(e) => setBackgroundDraft(e.target.value)}
                className="w-full p-3 text-[14px] text-text-body border border-border rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-primary/30 focus:border-brand-primary resize-y min-h-[80px]"
                placeholder="What drove the need for this solution..."
                autoFocus
              />
              <div className="flex items-center gap-2">
                <button
                  onClick={handleSaveBackground}
                  className="px-3 py-1.5 text-[12px] font-medium text-white bg-brand-primary rounded-xl hover:bg-[#25785A] transition-colors"
                >
                  Save
                </button>
                <button
                  onClick={() => { setEditingBackground(false); setBackgroundDraft(data.background || '') }}
                  className="px-3 py-1.5 text-[12px] font-medium text-[#666666] bg-white border border-border rounded-xl hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="group">
              {data.company_name && (
                <p className="text-[14px] font-medium text-text-body mb-1">
                  {data.company_name}
                  {data.industry && (
                    <span className="text-[#666666] font-normal"> &mdash; {data.industry}</span>
                  )}
                </p>
              )}
              {data.background ? (
                <p className="text-[14px] text-[#666666] leading-relaxed">{data.background}</p>
              ) : (
                <p className="text-[13px] text-text-placeholder italic">No background description yet. Click to add one.</p>
              )}
              <div className="mt-2 flex items-center gap-3 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={() => { setBackgroundDraft(data.background || ''); setEditingBackground(true) }}
                  className="inline-flex items-center gap-1 text-[12px] text-text-placeholder hover:text-brand-primary transition-colors"
                >
                  <Pencil className="w-3 h-3" />
                  Edit
                </button>
                {onOpenBackgroundDetail && (
                  <button
                    onClick={onOpenBackgroundDetail}
                    className="text-[11px] text-text-placeholder hover:text-brand-primary transition-colors"
                  >
                    View Details →
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Vision */}
      <div>
        <h2 className="text-lg font-semibold text-text-body mb-3 flex items-center gap-2">
          <Eye className="w-5 h-5 text-text-placeholder" />
          Vision
        </h2>
        <div className="bg-white rounded-2xl shadow-md border border-border p-5">
          {editingVision ? (
            <div className="space-y-3">
              <textarea
                value={visionDraft}
                onChange={(e) => setVisionDraft(e.target.value)}
                className="w-full p-3 text-[14px] text-text-body border border-border rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-primary/30 focus:border-brand-primary resize-y min-h-[80px]"
                placeholder="Describe the product vision..."
                autoFocus
              />
              <div className="flex items-center gap-2">
                <button
                  onClick={handleSaveVision}
                  className="px-3 py-1.5 text-[12px] font-medium text-white bg-brand-primary rounded-xl hover:bg-[#25785A] transition-colors"
                >
                  Save
                </button>
                <button
                  onClick={() => { setEditingVision(false); setVisionDraft(data.vision || '') }}
                  className="px-3 py-1.5 text-[12px] font-medium text-[#666666] bg-white border border-border rounded-xl hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="group">
              {data.vision ? (
                <p className="text-[14px] text-[#666666] leading-relaxed">{data.vision}</p>
              ) : (
                <p className="text-[13px] text-text-placeholder italic">No vision statement yet. Click to add one.</p>
              )}
              <div className="mt-2 flex items-center gap-3 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={() => { setVisionDraft(data.vision || ''); setEditingVision(true) }}
                  className="inline-flex items-center gap-1 text-[12px] text-text-placeholder hover:text-brand-primary transition-colors"
                >
                  <Pencil className="w-3 h-3" />
                  Edit
                </button>
                {data.vision && (
                  <div className="relative">
                    <button
                      onClick={() => setShowEnhanceMenu(!showEnhanceMenu)}
                      className="inline-flex items-center gap-1 text-[12px] text-text-placeholder hover:text-brand-primary transition-colors"
                    >
                      <Sparkles className="w-3 h-3" />
                      AI Enhance
                    </button>
                    {showEnhanceMenu && (
                      <div className="absolute left-0 top-full mt-1 w-48 bg-white border border-border rounded-xl shadow-lg z-10 py-1">
                        {[
                          { key: 'enhance', label: 'Enhance' },
                          { key: 'simplify', label: 'Simplify' },
                          { key: 'metrics', label: 'Add Metrics' },
                          { key: 'professional', label: 'Make Professional' },
                        ].map((opt) => (
                          <button
                            key={opt.key}
                            onClick={() => handleEnhanceVision(opt.key)}
                            className="w-full text-left px-3 py-2 text-[12px] text-text-body hover:bg-[#E8F5E9] transition-colors"
                          >
                            {opt.label}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}
                {onOpenVisionDetail && (
                  <button
                    onClick={onOpenVisionDetail}
                    className="text-[11px] text-text-placeholder hover:text-brand-primary transition-colors"
                  >
                    View Details →
                  </button>
                )}
              </div>

              {/* AI Enhancement loading/result */}
              {isEnhancing && (
                <div className="mt-3 p-3 border border-border rounded-xl bg-[#F4F4F4]">
                  <div className="flex items-center gap-2 text-[12px] text-[#666666]">
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-brand-primary" />
                    Generating suggestion...
                  </div>
                </div>
              )}
              {enhancementError && (
                <div className="mt-3 p-3 border border-red-200 rounded-xl bg-red-50">
                  <p className="text-[12px] text-red-600">{enhancementError}</p>
                </div>
              )}
              {aiSuggestion && (
                <div className="mt-3 p-4 border border-brand-primary/30 rounded-xl bg-[#E8F5E9]/30">
                  <p className="text-[11px] font-medium text-[#25785A] uppercase tracking-wide mb-2">AI Suggestion</p>
                  <p className="text-[14px] text-text-body leading-relaxed">{aiSuggestion}</p>
                  <div className="mt-3 flex items-center gap-2">
                    <button
                      onClick={handleAcceptSuggestion}
                      className="inline-flex items-center gap-1 px-3 py-1.5 text-[12px] font-medium text-white bg-brand-primary rounded-xl hover:bg-[#25785A] transition-colors"
                    >
                      <Check className="w-3 h-3" />
                      Accept
                    </button>
                    <button
                      onClick={handleEditSuggestion}
                      className="inline-flex items-center gap-1 px-3 py-1.5 text-[12px] font-medium text-[#666666] bg-white border border-border rounded-xl hover:bg-gray-50 transition-colors"
                    >
                      <Pencil className="w-3 h-3" />
                      Edit
                    </button>
                    <button
                      onClick={() => setAiSuggestion(null)}
                      className="inline-flex items-center gap-1 px-3 py-1.5 text-[12px] font-medium text-text-placeholder hover:text-[#666666] transition-colors"
                    >
                      <X className="w-3 h-3" />
                      Dismiss
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Business Goals — Action Queue pattern */}
      <DriverContainer
        icon={Target}
        title="BUSINESS GOALS"
        count={data.goals.length}
        confirmedCount={confirmedGoals}
        onConfirmAll={() => onConfirmAll('business_driver', data.goals.map(g => g.id))}
      >
        {data.goals.length === 0 ? (
          <p className="px-5 py-4 text-[13px] text-text-placeholder italic">No business goals identified yet</p>
        ) : (
          <>
            {visibleGoals.map((goal) => (
              <DriverItemRow
                key={goal.id}
                driver={goal}
                driverType="goal"
                isExpanded={expandedId === goal.id}
                onToggle={() => setExpandedId(expandedId === goal.id ? null : goal.id)}
                onDrawerOpen={() => setSelectedDriver({ id: goal.id, type: 'goal', data: goal })}
                onConfirm={() => onConfirm('business_driver', goal.id)}
                onNeedsReview={() => onNeedsReview('business_driver', goal.id)}
                onStatusClick={onStatusClick ? () => onStatusClick('business_driver', goal.id, goal.description.slice(0, 60), goal.confirmation_status) : undefined}
              />
            ))}
            {sortedGoals.length > SHOW_MAX_DRIVERS && (
              <button
                onClick={() => setShowAllGoals(!showAllGoals)}
                className="w-full px-4 py-2.5 text-[12px] font-medium text-brand-primary hover:bg-surface-page transition-colors border-t border-[#F0F0F0]"
              >
                {showAllGoals ? 'Show less' : `Show all ${sortedGoals.length} goals`}
              </button>
            )}
          </>
        )}
      </DriverContainer>

      {/* Business Pain Points — Action Queue pattern */}
      <DriverContainer
        icon={AlertTriangle}
        title="BUSINESS PAIN POINTS"
        count={data.pain_points.length}
        confirmedCount={confirmedPains}
        onConfirmAll={() => onConfirmAll('business_driver', data.pain_points.map(p => p.id))}
      >
        {data.pain_points.length === 0 ? (
          <p className="px-5 py-4 text-[13px] text-text-placeholder italic">No pain points identified yet</p>
        ) : (
          <>
            {visiblePains.map((pain) => (
              <DriverItemRow
                key={pain.id}
                driver={pain}
                driverType="pain"
                isExpanded={expandedId === pain.id}
                onToggle={() => setExpandedId(expandedId === pain.id ? null : pain.id)}
                onDrawerOpen={() => setSelectedDriver({ id: pain.id, type: 'pain', data: pain })}
                onConfirm={() => onConfirm('business_driver', pain.id)}
                onNeedsReview={() => onNeedsReview('business_driver', pain.id)}
                onStatusClick={onStatusClick ? () => onStatusClick('business_driver', pain.id, pain.description.slice(0, 60), pain.confirmation_status) : undefined}
              />
            ))}
            {sortedPains.length > SHOW_MAX_DRIVERS && (
              <button
                onClick={() => setShowAllPains(!showAllPains)}
                className="w-full px-4 py-2.5 text-[12px] font-medium text-brand-primary hover:bg-surface-page transition-colors border-t border-[#F0F0F0]"
              >
                {showAllPains ? 'Show less' : `Show all ${sortedPains.length} pain points`}
              </button>
            )}
          </>
        )}
      </DriverContainer>

      {/* Detail Drawer */}
      {selectedDriver && (
        <BusinessDriverDetailDrawer
          driverId={selectedDriver.id}
          driverType={selectedDriver.type}
          projectId={projectId}
          initialData={selectedDriver.data}
          stakeholders={stakeholders}
          onClose={() => setSelectedDriver(null)}
          onConfirm={onConfirm}
          onNeedsReview={onNeedsReview}
        />
      )}
    </section>
  )
}
