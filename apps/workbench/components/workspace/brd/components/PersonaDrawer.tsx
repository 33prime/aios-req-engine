'use client'

import { useState } from 'react'
import {
  X,
  Users,
  FileText,
  Target,
  AlertTriangle,
  Check,
  Info,
  Puzzle,
} from 'lucide-react'
import { BRDStatusBadge } from './StatusBadge'
import { ConfirmActions } from './ConfirmActions'
import type {
  PersonaBRDSummary,
  StakeholderBRDSummary,
  FeatureBRDSummary,
} from '@/types/workspace'

type TabId = 'profile' | 'validation' | 'evidence'

interface PersonaDrawerProps {
  persona: PersonaBRDSummary
  projectId: string
  stakeholders?: StakeholderBRDSummary[]
  features?: FeatureBRDSummary[]
  onClose: () => void
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
}

const TABS: { id: TabId; label: string; icon: typeof FileText }[] = [
  { id: 'profile', label: 'Profile', icon: Users },
  { id: 'validation', label: 'Validation', icon: Check },
  { id: 'evidence', label: 'Evidence', icon: FileText },
]

export function PersonaDrawer({
  persona,
  projectId,
  stakeholders = [],
  features = [],
  onClose,
  onConfirm,
  onNeedsReview,
}: PersonaDrawerProps) {
  const [activeTab, setActiveTab] = useState<TabId>('profile')

  // Find stakeholders that match this persona's role
  const matchedStakeholders = stakeholders.filter(
    (s) => s.role && persona.role && s.role.toLowerCase() === persona.role.toLowerCase()
  )

  const hasVoice = matchedStakeholders.length > 0

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
              {/* Navy circle with Users icon */}
              <div className="w-8 h-8 rounded-full bg-[#0A1E2F] flex items-center justify-center flex-shrink-0 mt-0.5">
                <Users className="w-4 h-4 text-white" />
              </div>
              <div className="min-w-0">
                <p className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-1">
                  Persona
                </p>
                <h2 className="text-[15px] font-semibold text-[#333333] line-clamp-2 leading-snug">
                  {persona.name}
                </h2>
                <div className="flex items-center gap-2 mt-1.5">
                  {persona.role && (
                    <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[#F0F0F0] text-[#666666]">
                      {persona.role}
                    </span>
                  )}
                  {persona.canvas_role === 'primary' && (
                    <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[#E8F5E9] text-[#25785A]">
                      Primary
                    </span>
                  )}
                  {persona.canvas_role === 'secondary' && (
                    <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[#F0F0F0] text-[#666666]">
                      Secondary
                    </span>
                  )}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <BRDStatusBadge status={persona.confirmation_status} />
              <button
                onClick={onClose}
                className="p-1.5 rounded-md text-[#999999] hover:text-[#666666] hover:bg-[#F0F0F0] transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Confirm/Review actions */}
          <div className="mt-3">
            <ConfirmActions
              status={persona.confirmation_status}
              onConfirm={() => onConfirm('persona', persona.id)}
              onNeedsReview={() => onNeedsReview('persona', persona.id)}
              size="md"
            />
          </div>

          {/* Tabs */}
          <div className="flex gap-0 mt-4 -mb-4 border-b-0">
            {TABS.map((tab) => {
              const TabIcon = tab.icon
              const isActive = activeTab === tab.id
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-1.5 px-3 py-2 text-[12px] font-medium border-b-2 transition-colors ${
                    isActive
                      ? 'border-[#3FAF7A] text-[#25785A]'
                      : 'border-transparent text-[#999999] hover:text-[#666666]'
                  }`}
                >
                  <TabIcon className="w-3.5 h-3.5" />
                  {tab.label}
                  {tab.id === 'validation' && !hasVoice && (
                    <span className="ml-1 text-[10px] bg-[#F0F0F0] text-[#666666] px-1.5 py-0.5 rounded-full">
                      !
                    </span>
                  )}
                </button>
              )
            })}
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {activeTab === 'profile' && (
            <ProfileTab persona={persona} features={features} />
          )}
          {activeTab === 'validation' && (
            <ValidationTab
              persona={persona}
              stakeholders={stakeholders}
              matchedStakeholders={matchedStakeholders}
              hasVoice={hasVoice}
            />
          )}
          {activeTab === 'evidence' && <EvidenceTab />}
        </div>
      </div>
    </>
  )
}

// ============================================================================
// Profile Tab
// ============================================================================

function ProfileTab({
  persona,
  features,
}: {
  persona: PersonaBRDSummary
  features: FeatureBRDSummary[]
}) {
  return (
    <div className="space-y-6">
      {/* Role & Description */}
      <div>
        <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2">
          Overview
        </h4>
        <div className="border border-[#E5E5E5] rounded-xl px-4 py-3">
          {persona.role && (
            <div className="mb-2">
              <span className="text-[12px] font-medium text-[#999999]">Role: </span>
              <span className="text-[13px] text-[#333333]">{persona.role}</span>
            </div>
          )}
          {persona.persona_type && (
            <div className="mb-2">
              <span className="text-[12px] font-medium text-[#999999]">Type: </span>
              <span className="text-[13px] text-[#333333] capitalize">{persona.persona_type}</span>
            </div>
          )}
          {persona.description ? (
            <p className="text-[13px] text-[#333333] leading-relaxed">
              {persona.description}
            </p>
          ) : (
            <p className="text-[12px] text-[#999999] italic">
              No description available. Process more signals to build this persona profile.
            </p>
          )}
        </div>
      </div>

      {/* Goals */}
      <div>
        <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2 flex items-center gap-1.5">
          <Target className="w-3.5 h-3.5" />
          Goals
        </h4>
        {persona.goals && persona.goals.length > 0 ? (
          <div className="border border-[#E5E5E5] rounded-xl overflow-hidden">
            {persona.goals.map((goal, i) => (
              <div
                key={i}
                className="flex items-start gap-2.5 px-4 py-2.5 border-b border-[#F0F0F0] last:border-0"
              >
                <Target className="w-3.5 h-3.5 mt-0.5 text-[#3FAF7A] flex-shrink-0" />
                <span className="text-[13px] text-[#333333] leading-relaxed">{goal}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="border border-dashed border-[#E5E5E5] rounded-xl px-4 py-3">
            <p className="text-[12px] text-[#999999] italic">
              No goals identified yet. Goals will be extracted from signals mentioning this persona.
            </p>
          </div>
        )}
      </div>

      {/* Pain Points */}
      <div>
        <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2 flex items-center gap-1.5">
          <AlertTriangle className="w-3.5 h-3.5" />
          Pain Points
        </h4>
        {persona.pain_points && persona.pain_points.length > 0 ? (
          <div className="border border-[#E5E5E5] rounded-xl overflow-hidden">
            {persona.pain_points.map((pain, i) => (
              <div
                key={i}
                className="flex items-start gap-2.5 px-4 py-2.5 border-b border-[#F0F0F0] last:border-0"
              >
                <AlertTriangle className="w-3.5 h-3.5 mt-0.5 text-[#999999] flex-shrink-0" />
                <span className="text-[13px] text-[#333333] leading-relaxed">{pain}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="border border-dashed border-[#E5E5E5] rounded-xl px-4 py-3">
            <p className="text-[12px] text-[#999999] italic">
              No pain points identified yet. Pain points will be extracted from signals mentioning this persona.
            </p>
          </div>
        )}
      </div>

      {/* Linked Features */}
      <div>
        <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2 flex items-center gap-1.5">
          <Puzzle className="w-3.5 h-3.5" />
          Linked Features
          {features.length > 0 && (
            <span className="text-[10px] bg-[#F0F0F0] text-[#666666] px-1.5 py-0.5 rounded-full ml-1">
              {features.length}
            </span>
          )}
        </h4>
        {features.length > 0 ? (
          <div className="border border-[#E5E5E5] rounded-xl overflow-hidden">
            {features.map((feature) => {
              const isConfirmed =
                feature.confirmation_status === 'confirmed_consultant' ||
                feature.confirmation_status === 'confirmed_client'
              return (
                <div
                  key={feature.id}
                  className="flex items-center gap-2.5 px-4 py-2.5 border-b border-[#F0F0F0] last:border-0"
                >
                  <Puzzle className="w-3.5 h-3.5 text-[#999999] flex-shrink-0" />
                  <span className="text-[13px] text-[#333333] font-medium flex-1 truncate">
                    {feature.name}
                  </span>
                  {feature.category && (
                    <span className="text-[10px] text-[#999999] bg-[#F0F0F0] px-1.5 py-0.5 rounded">
                      {feature.category}
                    </span>
                  )}
                  {isConfirmed && (
                    <Check className="w-3.5 h-3.5 text-[#3FAF7A] flex-shrink-0" />
                  )}
                </div>
              )
            })}
          </div>
        ) : (
          <div className="border border-dashed border-[#E5E5E5] rounded-xl px-4 py-3">
            <p className="text-[12px] text-[#999999] italic">
              No features linked to this persona yet.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

// ============================================================================
// Validation Tab
// ============================================================================

function ValidationTab({
  persona,
  stakeholders,
  matchedStakeholders,
  hasVoice,
}: {
  persona: PersonaBRDSummary
  stakeholders: StakeholderBRDSummary[]
  matchedStakeholders: StakeholderBRDSummary[]
  hasVoice: boolean
}) {
  const totalStakeholders = stakeholders.length

  return (
    <div className="space-y-6">
      {/* Missing Voice Alert */}
      {!hasVoice && (
        <div className="flex items-start gap-2.5 bg-[#F4F4F4] border border-[#E5E5E5] rounded-xl px-4 py-3">
          <Info className="w-4 h-4 mt-0.5 text-[#999999] flex-shrink-0" />
          <div>
            <p className="text-[13px] font-medium text-[#333333] mb-1">Missing Voice</p>
            <p className="text-[12px] text-[#666666] leading-relaxed">
              No real stakeholders mapped to this persona. Consider interviewing someone who matches this role.
            </p>
          </div>
        </div>
      )}

      {/* Matched Stakeholders */}
      <div>
        <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2 flex items-center gap-1.5">
          <Users className="w-3.5 h-3.5" />
          Matched Stakeholders
          {matchedStakeholders.length > 0 && (
            <span className="text-[10px] bg-[#F0F0F0] text-[#666666] px-1.5 py-0.5 rounded-full ml-1">
              {matchedStakeholders.length}
            </span>
          )}
        </h4>
        {matchedStakeholders.length > 0 ? (
          <div className="border border-[#E5E5E5] rounded-xl overflow-hidden">
            {matchedStakeholders.map((s) => (
              <div
                key={s.id}
                className="flex items-center gap-2.5 px-4 py-2.5 border-b border-[#F0F0F0] last:border-0"
              >
                <Users className="w-3.5 h-3.5 text-[#999999] flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <span className="text-[13px] text-[#333333] font-medium">{s.name}</span>
                  {s.role && (
                    <span className="text-[11px] text-[#999999] ml-2">{s.role}</span>
                  )}
                </div>
                {s.stakeholder_type && (
                  <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[#F0F0F0] text-[#666666]">
                    {s.stakeholder_type}
                  </span>
                )}
                {s.influence_level && (
                  <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[#F0F0F0] text-[#666666]">
                    {s.influence_level}
                  </span>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="border border-dashed border-[#E5E5E5] rounded-xl px-4 py-3">
            <p className="text-[12px] text-[#999999] italic">
              No stakeholders with a matching role found.
            </p>
          </div>
        )}
      </div>

      {/* Stakeholder Coverage Summary */}
      <div>
        <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2">
          Stakeholder Coverage
        </h4>
        <div className="border border-[#E5E5E5] rounded-xl px-4 py-3">
          <div className="grid grid-cols-3 gap-3">
            <div className="text-center">
              <p className="text-[18px] font-bold text-[#333333]">{totalStakeholders}</p>
              <p className="text-[10px] text-[#999999] uppercase">Total</p>
            </div>
            <div className="text-center">
              <p className={`text-[18px] font-bold ${matchedStakeholders.length > 0 ? 'text-[#3FAF7A]' : 'text-[#999999]'}`}>
                {matchedStakeholders.length}
              </p>
              <p className="text-[10px] text-[#999999] uppercase">Matched</p>
            </div>
            <div className="text-center">
              <p className={`text-[18px] font-bold ${!hasVoice ? 'text-[#999999]' : 'text-[#25785A]'}`}>
                {hasVoice ? 'Yes' : 'No'}
              </p>
              <p className="text-[10px] text-[#999999] uppercase">Has Voice</p>
            </div>
          </div>

          {/* Coverage bar */}
          {totalStakeholders > 0 && (
            <div className="mt-3 pt-3 border-t border-[#F0F0F0]">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[11px] text-[#666666]">Role Match Rate</span>
                <span className="text-[11px] font-medium text-[#333333]">
                  {matchedStakeholders.length}/{totalStakeholders}
                </span>
              </div>
              <div className="h-2 bg-[#F0F0F0] rounded-full overflow-hidden">
                <div
                  className="h-full bg-[#3FAF7A] rounded-full transition-all"
                  style={{ width: `${(matchedStakeholders.length / totalStakeholders) * 100}%` }}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// Evidence Tab
// ============================================================================

function EvidenceTab() {
  return (
    <div className="text-center py-8">
      <FileText className="w-8 h-8 text-[#E5E5E5] mx-auto mb-3" />
      <p className="text-[13px] text-[#666666] mb-1">Evidence sources available through signal analysis</p>
      <p className="text-[12px] text-[#999999]">
        Process signals referencing this persona to build an evidence trail.
      </p>
    </div>
  )
}
