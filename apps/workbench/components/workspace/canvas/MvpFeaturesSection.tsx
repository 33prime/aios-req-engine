'use client'

import { Package } from 'lucide-react'
import type { FeatureBRDSummary } from '@/types/workspace'

interface MvpFeaturesSectionProps {
  features: FeatureBRDSummary[]
  onFeatureClick?: (feature: FeatureBRDSummary) => void
}

function StatusBadge({ status }: { status?: string | null }) {
  if (!status) return null
  const isConfirmed = status === 'confirmed_consultant' || status === 'confirmed_client'
  return (
    <span className={`px-1.5 py-0.5 text-[10px] font-medium rounded ${
      isConfirmed
        ? 'bg-[#E8F5E9] text-[#25785A]'
        : status === 'needs_client'
          ? 'bg-[#F0F0F0] text-[#666666]'
          : 'bg-gray-50 text-text-placeholder'
    }`}>
      {isConfirmed ? 'Confirmed' : status === 'needs_client' ? 'Needs Review' : 'AI Generated'}
    </span>
  )
}

export function MvpFeaturesSection({ features, onFeatureClick }: MvpFeaturesSectionProps) {
  const confirmedCount = features.filter(
    (f) => f.confirmation_status === 'confirmed_consultant' || f.confirmation_status === 'confirmed_client'
  ).length

  const progressPct = features.length > 0 ? Math.round((confirmedCount / features.length) * 100) : 0

  return (
    <section>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Package className="w-4 h-4 text-brand-primary" />
          <h2 className="text-[16px] font-semibold text-text-body">MVP Features</h2>
          <span className="text-[12px] text-text-placeholder">
            {features.length} must-have {features.length === 1 ? 'feature' : 'features'}
          </span>
        </div>
        {features.length > 0 && (
          <span className="text-[12px] font-medium text-[#666666]">
            {confirmedCount}/{features.length} confirmed
          </span>
        )}
      </div>

      {/* Progress bar */}
      {features.length > 0 && (
        <div className="flex items-center gap-2 mb-4">
          <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-brand-primary rounded-full transition-all duration-300"
              style={{ width: `${progressPct}%` }}
            />
          </div>
          <span className="text-[11px] text-text-placeholder w-10 text-right">{progressPct}%</span>
        </div>
      )}

      {features.length === 0 ? (
        <div className="bg-white rounded-2xl shadow-md border border-border px-6 py-8 text-center">
          <Package className="w-8 h-8 text-text-placeholder mx-auto mb-3" />
          <p className="text-[13px] text-[#666666]">
            No must-have features defined yet. Set feature priorities in BRD View.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {features.map((feature) => (
            <div
              key={feature.id}
              className={`bg-white rounded-2xl shadow-md border border-border px-5 py-4 ${
                onFeatureClick ? 'cursor-pointer hover:border-brand-primary/40 transition-colors' : ''
              }`}
              onClick={onFeatureClick ? () => onFeatureClick(feature) : undefined}
              role={onFeatureClick ? 'button' : undefined}
              tabIndex={onFeatureClick ? 0 : undefined}
              onKeyDown={onFeatureClick ? (e) => { if (e.key === 'Enter' || e.key === ' ') onFeatureClick(feature) } : undefined}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-[14px] font-semibold text-text-body">{feature.name}</span>
                    <StatusBadge status={feature.confirmation_status} />
                  </div>
                  {feature.description && (
                    <p className="text-[12px] text-[#666666] mt-1 line-clamp-2">{feature.description}</p>
                  )}
                </div>
              </div>

              {/* Category + VP step link */}
              <div className="flex items-center gap-2 mt-2 flex-wrap">
                {feature.category && (
                  <span className="px-1.5 py-0.5 text-[10px] font-medium bg-[#F0F0F0] text-[#666666] rounded-lg">
                    {feature.category}
                  </span>
                )}
                {feature.vp_step_id && (
                  <span className="text-[10px] text-text-placeholder">Mapped to workflow step</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
