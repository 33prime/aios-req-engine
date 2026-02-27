'use client'

import { useState, useEffect } from 'react'
import { Loader2, Sparkles } from 'lucide-react'
import { Modal } from '@/components/ui/Modal'
import { DesignCard } from './DesignCard'
import { getDesignProfile } from '@/lib/api'
import type {
  DesignProfile,
  DesignSelection,
  DesignTokens,
  BrandData,
} from '@/types/prototype'

interface DesignSelectionModalProps {
  isOpen: boolean
  onClose: () => void
  onGenerate: (selection: DesignSelection) => void
  projectId: string
  isGenerating: boolean
}

/** Build DesignTokens from brand data for the "Match Current Brand" card. */
function brandToTokens(brand: BrandData): DesignTokens {
  const colors = brand.brand_colors || []
  const chars = brand.design_characteristics
  return {
    primary_color: colors[0] || '#000000',
    secondary_color: colors[1] || '#f5f5f5',
    accent_color: colors[2] || colors[0] || '#3b82f6',
    font_heading: brand.typography?.heading_font || 'Inter',
    font_body: brand.typography?.body_font || 'Inter',
    spacing: chars?.spacing || 'balanced',
    corners: chars?.corners || 'slightly-rounded',
    style_direction: chars?.overall_feel
      ? `Match client brand: ${chars.overall_feel} feel with ${chars.visual_weight || 'medium'} visual weight`
      : 'Match client brand identity',
    logo_url: brand.logo_url || undefined,
  }
}

export function DesignSelectionModal({
  isOpen,
  onClose,
  onGenerate,
  projectId,
  isGenerating,
}: DesignSelectionModalProps) {
  const [profile, setProfile] = useState<DesignProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  // Fetch design profile on mount
  useEffect(() => {
    if (!isOpen) return

    let cancelled = false
    setLoading(true)

    getDesignProfile(projectId)
      .then((data) => {
        if (cancelled) return
        setProfile(data)
        // Auto-select brand if available
        if (data.brand_available && data.brand) {
          setSelectedId('brand_match')
        }
      })
      .catch(() => {
        if (!cancelled) setProfile(null)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [isOpen, projectId])

  // Reset selection when modal closes
  useEffect(() => {
    if (!isOpen) {
      setSelectedId(null)
      setProfile(null)
    }
  }, [isOpen])

  const handleGenerate = () => {
    if (!selectedId || !profile) return

    let selection: DesignSelection

    if (selectedId === 'brand_match' && profile.brand) {
      selection = {
        option_id: 'brand_match',
        tokens: brandToTokens(profile.brand),
        source: 'brand',
      }
    } else {
      const generic = profile.generic_styles.find((s) => s.id === selectedId)
      if (!generic) return
      selection = {
        option_id: generic.id,
        tokens: generic.tokens,
        source: 'generic',
      }
    }

    onGenerate(selection)
  }

  const footer = (
    <>
      <button
        onClick={onClose}
        disabled={isGenerating}
        className="px-4 py-2 text-sm font-medium text-text-body bg-surface-subtle hover:bg-border rounded-lg transition-colors disabled:opacity-50"
      >
        Cancel
      </button>
      <button
        onClick={handleGenerate}
        disabled={!selectedId || isGenerating}
        className="px-5 py-2 text-sm font-medium text-white bg-brand-primary hover:bg-[#25785A] rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
      >
        {isGenerating ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Generating...
          </>
        ) : (
          <>
            <Sparkles className="w-4 h-4" />
            Generate Prototype
          </>
        )}
      </button>
    </>
  )

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Choose a Design Direction"
      size="xl"
      footer={footer}
    >
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-brand-primary" />
          <span className="ml-2 text-sm text-text-placeholder">Loading design options...</span>
        </div>
      ) : !profile ? (
        <div className="text-center py-8">
          <p className="text-sm text-text-placeholder">
            Could not load design options. You can still generate with default styles.
          </p>
        </div>
      ) : (
        <div className="space-y-6 max-h-[60vh] overflow-y-auto pr-1">
          {/* Brand match card */}
          {profile.brand_available && profile.brand && (
            <div>
              <p className="text-sm font-medium text-text-body mb-2">
                Based on your client&apos;s brand:
              </p>
              <DesignCard
                id="brand_match"
                label="Match Current Brand"
                description={`Use the colors, fonts, and style extracted from the client's website`}
                colors={profile.brand.brand_colors.slice(0, 5)}
                isSelected={selectedId === 'brand_match'}
                onSelect={() => setSelectedId('brand_match')}
                logoUrl={profile.brand.logo_url}
                source={profile.brand.logo_url ? undefined : 'Website analysis'}
              />
            </div>
          )}

          {/* Design inspirations */}
          {profile.design_inspirations.length > 0 && (
            <div>
              <p className="text-sm font-medium text-text-body mb-2">
                From your discovery:
              </p>
              <div className="grid grid-cols-2 gap-3">
                {profile.design_inspirations.map((insp) => (
                  <div
                    key={insp.id}
                    className="p-3 border border-border rounded-lg bg-gray-50"
                  >
                    <p className="text-sm font-medium text-text-body">{insp.name}</p>
                    {insp.description && (
                      <p className="text-xs text-text-placeholder mt-0.5">{insp.description}</p>
                    )}
                    <p className="text-xs text-text-placeholder italic mt-1">
                      {insp.source === 'competitor_ref' ? 'Design reference' : 'Discovery data'}
                    </p>
                  </div>
                ))}
              </div>
              {profile.suggested_style && (
                <p className="text-xs text-text-placeholder mt-2 italic">
                  Suggested style: <strong>{profile.suggested_style}</strong>
                  {profile.style_source && ` — ${profile.style_source}`}
                </p>
              )}
            </div>
          )}

          {/* Generic styles */}
          <div>
            <p className="text-sm font-medium text-text-body mb-2">
              {profile.brand_available || profile.design_inspirations.length > 0
                ? 'Or choose a style:'
                : 'Choose a style:'}
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
              {profile.generic_styles.map((style) => (
                <DesignCard
                  key={style.id}
                  id={style.id}
                  label={style.label}
                  description={style.description}
                  colors={style.preview_colors}
                  isSelected={selectedId === style.id}
                  onSelect={() => setSelectedId(style.id)}
                  size="sm"
                />
              ))}
            </div>
          </div>
        </div>
      )}
    </Modal>
  )
}
