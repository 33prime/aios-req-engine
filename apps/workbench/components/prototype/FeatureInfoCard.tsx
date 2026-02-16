'use client'

import { useState } from 'react'
import type { FeatureOverlay, OverlayContent, TourStep, FeatureGap } from '@/types/prototype'

interface FeatureInfoCardProps {
  overlay: FeatureOverlay | null
  tourStep: TourStep | null
}

type InfoTab = 'overview' | 'impact' | 'gaps'

const TAB_CONFIG: { key: InfoTab; label: string }[] = [
  { key: 'overview', label: 'Overview' },
  { key: 'impact', label: 'Impact' },
  { key: 'gaps', label: 'Gaps' },
]

const CONFIDENCE_COLORS: Record<string, string> = {
  high: 'bg-emerald-400',
  medium: 'bg-brand-accent',
  low: 'bg-red-400',
}

const IMPL_STATUS_STYLES: Record<string, string> = {
  functional: 'bg-emerald-100 text-emerald-800',
  partial: 'bg-amber-100 text-amber-800',
  placeholder: 'bg-gray-100 text-gray-600',
}

const AREA_STYLES: Record<string, string> = {
  business_rules: 'bg-ui-background text-ui-bodyText',
  data_handling: 'bg-ui-background text-ui-bodyText',
  user_flow: 'bg-ui-background text-ui-bodyText',
  permissions: 'bg-ui-background text-ui-bodyText',
  integration: 'bg-ui-background text-ui-bodyText',
}

function confidenceLevel(score: number): string {
  if (score >= 0.7) return 'high'
  if (score >= 0.4) return 'medium'
  return 'low'
}

/**
 * Tabbed feature info card shown in the right panel during prototype review.
 * Displays rich context about the current feature from overlay data.
 *
 * Tabs:
 * - Overview: spec vs code delta, implementation status, confidence
 * - Impact: personas affected, value path position, downstream risk
 * - Gaps: exactly 3 focused gap questions with requirement area badges
 */
export default function FeatureInfoCard({ overlay, tourStep }: FeatureInfoCardProps) {
  const [activeTab, setActiveTab] = useState<InfoTab>('overview')

  if (!overlay?.overlay_content) {
    return (
      <div className="p-4 text-center">
        <div className="w-10 h-10 mx-auto mb-2 rounded-full bg-ui-background flex items-center justify-center">
          <span className="text-ui-supportText text-lg">i</span>
        </div>
        <p className="text-xs text-ui-supportText">
          {tourStep ? 'Loading feature data...' : 'Click a feature or start the tour to see details'}
        </p>
      </div>
    )
  }

  const content = overlay.overlay_content
  const gapsCount = content.gaps?.length ?? 0

  return (
    <div className="flex flex-col h-full">
      {/* Feature header */}
      <div className="px-4 pt-3 pb-2 border-b border-ui-cardBorder">
        <div className="flex items-start justify-between gap-2 mb-2">
          <h3 className="text-sm font-semibold text-ui-headingDark leading-tight">
            {content.feature_name}
          </h3>
          <StatusBadge status={content.status} />
        </div>
        {tourStep?.vpStepLabel && (
          <div className="flex items-center gap-1.5 mb-2">
            <span className="w-1.5 h-1.5 rounded-full bg-brand-primary" />
            <span className="text-[11px] text-brand-primary font-medium">{tourStep.vpStepLabel}</span>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-0.5">
          {TAB_CONFIG.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors relative ${
                activeTab === key
                  ? 'bg-brand-primary/10 text-brand-primary'
                  : 'text-ui-supportText hover:text-ui-bodyText hover:bg-ui-background'
              }`}
            >
              {label}
              {key === 'gaps' && gapsCount > 0 && (
                <span className="ml-1 px-1 py-px bg-brand-primary text-white text-[9px] rounded-full">
                  {gapsCount}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
        {activeTab === 'overview' && <OverviewTab content={content} tourStep={tourStep} />}
        {activeTab === 'impact' && <ImpactTab content={content} />}
        {activeTab === 'gaps' && <GapsTab content={content} />}
      </div>
    </div>
  )
}

// =============================================================================
// Status Badge
// =============================================================================

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    understood: 'bg-emerald-100 text-emerald-800',
    partial: 'bg-amber-100 text-amber-800',
    unknown: 'bg-gray-100 text-gray-600',
  }
  return (
    <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full whitespace-nowrap ${styles[status] || styles.unknown}`}>
      {status}
    </span>
  )
}

// =============================================================================
// Overview Tab — spec vs code delta
// =============================================================================

function OverviewTab({ content, tourStep }: { content: OverlayContent; tourStep: TourStep | null }) {
  const overview = content.overview

  return (
    <div className="space-y-4">
      {/* Confidence + role */}
      <div className="flex items-center gap-3">
        <div className="flex-1">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[11px] text-ui-supportText">Confidence</span>
            <span className="text-[11px] font-medium text-ui-bodyText">{Math.round(content.confidence * 100)}%</span>
          </div>
          <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${CONFIDENCE_COLORS[confidenceLevel(content.confidence)]}`}
              style={{ width: `${content.confidence * 100}%` }}
            />
          </div>
        </div>
        {tourStep && (
          <span className={`text-[10px] font-medium px-2 py-0.5 rounded ${
            tourStep.featureRole === 'core'
              ? 'bg-brand-primary/10 text-brand-primary'
              : tourStep.featureRole === 'supporting'
                ? 'bg-brand-accent/10 text-brand-accent'
                : 'bg-gray-100 text-gray-500'
          }`}>
            {tourStep.featureRole}
          </span>
        )}
      </div>

      {/* Implementation status */}
      {overview?.implementation_status && (
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-ui-supportText">Implementation:</span>
          <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${IMPL_STATUS_STYLES[overview.implementation_status] || IMPL_STATUS_STYLES.placeholder}`}>
            {overview.implementation_status}
          </span>
        </div>
      )}

      {/* Spec summary */}
      {overview?.spec_summary && (
        <Section title="What AIOS says">
          <p className="text-xs text-ui-bodyText leading-relaxed">{overview.spec_summary}</p>
        </Section>
      )}

      {/* Prototype summary */}
      {overview?.prototype_summary && (
        <Section title="What code does">
          <p className="text-xs text-ui-bodyText leading-relaxed">{overview.prototype_summary}</p>
        </Section>
      )}

      {/* Delta */}
      {overview?.delta && overview.delta.length > 0 && (
        <Section title="Gaps between spec & code">
          <ul className="space-y-1">
            {overview.delta.map((d, i) => (
              <li key={i} className="text-xs text-ui-bodyText flex items-start gap-1.5">
                <span className="text-brand-primary mt-0.5">&#x2022;</span>{d}
              </li>
            ))}
          </ul>
        </Section>
      )}
    </div>
  )
}

// =============================================================================
// Impact Tab — personas, value path, downstream risk
// =============================================================================

function ImpactTab({ content }: { content: OverlayContent }) {
  const impact = content.impact

  return (
    <div className="space-y-4">
      {/* Personas affected */}
      {impact?.personas_affected && impact.personas_affected.length > 0 && (
        <Section title="Personas Affected">
          <div className="space-y-2">
            {impact.personas_affected.map((p, i) => (
              <div key={i} className="bg-ui-background rounded-lg p-2.5">
                <span className="text-xs font-medium text-ui-headingDark">{p.name}</span>
                <p className="text-xs text-ui-bodyText mt-1">{p.how_affected}</p>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Value path position */}
      {impact?.value_path_position && (
        <Section title="Value Path Position">
          <div className="bg-brand-primary/5 rounded-lg p-3 border border-brand-primary/10">
            <span className="text-xs font-medium text-brand-primary">{impact.value_path_position}</span>
          </div>
        </Section>
      )}

      {/* Downstream risk */}
      {impact?.downstream_risk && (
        <Section title="Downstream Risk">
          <div className="bg-amber-50 rounded-lg p-2.5 border border-amber-100">
            <p className="text-xs text-amber-800">{impact.downstream_risk}</p>
          </div>
        </Section>
      )}

      {(!impact?.personas_affected?.length && !impact?.value_path_position && !impact?.downstream_risk) && (
        <div className="text-center py-6">
          <p className="text-xs text-ui-supportText">Impact analysis not yet available for this feature.</p>
        </div>
      )}
    </div>
  )
}

// =============================================================================
// Gaps Tab — exactly 3 focused questions
// =============================================================================

function GapsTab({ content }: { content: OverlayContent }) {
  const gaps = content.gaps || []

  return (
    <div className="space-y-4">
      {/* Confidence bar */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <span className="text-[11px] text-ui-supportText">Feature Confidence</span>
          <span className="text-[11px] font-medium text-ui-bodyText">{Math.round(content.confidence * 100)}%</span>
        </div>
        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${CONFIDENCE_COLORS[confidenceLevel(content.confidence)]}`}
            style={{ width: `${content.confidence * 100}%` }}
          />
        </div>
      </div>

      {/* Gap cards */}
      {gaps.length > 0 && (
        <Section title={`Gap Questions (${gaps.length})`}>
          <div className="space-y-2.5">
            {gaps.map((gap, i) => (
              <GapCard key={i} gap={gap} index={i + 1} />
            ))}
          </div>
        </Section>
      )}

      {gaps.length === 0 && (
        <div className="text-center py-6">
          <p className="text-xs text-ui-supportText">No gap questions for this feature.</p>
        </div>
      )}
    </div>
  )
}

function GapCard({ gap, index }: { gap: FeatureGap; index: number }) {
  return (
    <div className="bg-ui-background rounded-lg p-3">
      <div className="flex items-start gap-2">
        <span className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold flex-shrink-0 bg-brand-primary text-white">
          {index}
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-xs text-ui-bodyText leading-relaxed">{gap.question}</p>
          {gap.why_it_matters && (
            <p className="text-[11px] text-ui-supportText mt-1.5 italic">{gap.why_it_matters}</p>
          )}
          <span className={`text-[10px] mt-1.5 inline-block px-1.5 py-0.5 rounded ${AREA_STYLES[gap.requirement_area] || AREA_STYLES.business_rules}`}>
            {gap.requirement_area.replace('_', ' ')}
          </span>
        </div>
      </div>
    </div>
  )
}

// =============================================================================
// Standalone Tabs — for embedding in ReviewPanel without the full card header
// =============================================================================

export function FeatureInfoTabs({ content, tourStep }: { content: OverlayContent; tourStep: TourStep | null }) {
  const [activeTab, setActiveTab] = useState<InfoTab>('overview')
  const gapsCount = content.gaps?.length ?? 0

  return (
    <div>
      <div className="flex gap-0.5 px-3 pt-2 pb-1.5">
        {TAB_CONFIG.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`px-2 py-1 text-[11px] font-medium rounded-md transition-colors ${
              activeTab === key
                ? 'bg-brand-primary/10 text-brand-primary'
                : 'text-ui-supportText hover:text-ui-bodyText hover:bg-ui-background'
            }`}
          >
            {label}
            {key === 'gaps' && gapsCount > 0 && (
              <span className="ml-1 px-1 py-px bg-brand-primary text-white text-[9px] rounded-full">
                {gapsCount}
              </span>
            )}
          </button>
        ))}
      </div>
      <div className="px-3 pb-3">
        {activeTab === 'overview' && <OverviewTab content={content} tourStep={tourStep} />}
        {activeTab === 'impact' && <ImpactTab content={content} />}
        {activeTab === 'gaps' && <GapsTab content={content} />}
      </div>
    </div>
  )
}

// =============================================================================
// Shared Section Component
// =============================================================================

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h4 className="text-[11px] font-semibold text-ui-headingDark uppercase tracking-wide mb-2">{title}</h4>
      {children}
    </div>
  )
}
