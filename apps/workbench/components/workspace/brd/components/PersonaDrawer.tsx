'use client'

import { useState } from 'react'
import {
  Users,
  FileText,
  Target,
  AlertTriangle,
  Check,
  Info,
  Puzzle,
} from 'lucide-react'
import { DrawerShell, type DrawerTab } from '@/components/ui/DrawerShell'
import { EmptyState } from '@/components/ui/EmptyState'
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

  const tabs: DrawerTab[] = [
    { id: 'profile', label: 'Profile', icon: Users },
    {
      id: 'validation',
      label: 'Validation',
      icon: Check,
      badge: !hasVoice ? (
        <span className="ml-1 text-[10px] bg-[#F0F0F0] text-[#666666] px-1.5 py-0.5 rounded-full">!</span>
      ) : undefined,
    },
    { id: 'evidence', label: 'Evidence', icon: FileText },
  ]

  return (
    <DrawerShell
      onClose={onClose}
      icon={Users}
      entityLabel="Persona"
      title={persona.name}
      headerExtra={
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
      }
      headerRight={<BRDStatusBadge status={persona.confirmation_status} />}
      headerActions={
        <ConfirmActions
          status={persona.confirmation_status}
          onConfirm={() => onConfirm('persona', persona.id)}
          onNeedsReview={() => onNeedsReview('persona', persona.id)}
          size="md"
        />
      }
      tabs={tabs}
      activeTab={activeTab}
      onTabChange={(id) => setActiveTab(id as TabId)}
    >
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
    </DrawerShell>
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
        <h4 className="text-[11px] font-medium text-text-placeholder uppercase tracking-wide mb-2">
          Overview
        </h4>
        <div className="border border-border rounded-xl px-4 py-3">
          {persona.role && (
            <div className="mb-2">
              <span className="text-[12px] font-medium text-text-placeholder">Role: </span>
              <span className="text-[13px] text-text-body">{persona.role}</span>
            </div>
          )}
          {persona.persona_type && (
            <div className="mb-2">
              <span className="text-[12px] font-medium text-text-placeholder">Type: </span>
              <span className="text-[13px] text-text-body capitalize">{persona.persona_type}</span>
            </div>
          )}
          {persona.description ? (
            <p className="text-[13px] text-text-body leading-relaxed">
              {persona.description}
            </p>
          ) : (
            <p className="text-[12px] text-text-placeholder italic">
              No description available. Process more signals to build this persona profile.
            </p>
          )}
        </div>
      </div>

      {/* Goals */}
      <div>
        <h4 className="text-[11px] font-medium text-text-placeholder uppercase tracking-wide mb-2 flex items-center gap-1.5">
          <Target className="w-3.5 h-3.5" />
          Goals
        </h4>
        {persona.goals && persona.goals.length > 0 ? (
          <div className="border border-border rounded-xl overflow-hidden">
            {persona.goals.map((goal, i) => (
              <div
                key={i}
                className="flex items-start gap-2.5 px-4 py-2.5 border-b border-[#F0F0F0] last:border-0"
              >
                <Target className="w-3.5 h-3.5 mt-0.5 text-brand-primary flex-shrink-0" />
                <span className="text-[13px] text-text-body leading-relaxed">{goal}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="border border-dashed border-border rounded-xl px-4 py-3">
            <p className="text-[12px] text-text-placeholder italic">
              No goals identified yet. Goals will be extracted from signals mentioning this persona.
            </p>
          </div>
        )}
      </div>

      {/* Pain Points */}
      <div>
        <h4 className="text-[11px] font-medium text-text-placeholder uppercase tracking-wide mb-2 flex items-center gap-1.5">
          <AlertTriangle className="w-3.5 h-3.5" />
          Pain Points
        </h4>
        {persona.pain_points && persona.pain_points.length > 0 ? (
          <div className="border border-border rounded-xl overflow-hidden">
            {persona.pain_points.map((pain, i) => (
              <div
                key={i}
                className="flex items-start gap-2.5 px-4 py-2.5 border-b border-[#F0F0F0] last:border-0"
              >
                <AlertTriangle className="w-3.5 h-3.5 mt-0.5 text-text-placeholder flex-shrink-0" />
                <span className="text-[13px] text-text-body leading-relaxed">{pain}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="border border-dashed border-border rounded-xl px-4 py-3">
            <p className="text-[12px] text-text-placeholder italic">
              No pain points identified yet. Pain points will be extracted from signals mentioning this persona.
            </p>
          </div>
        )}
      </div>

      {/* Linked Features */}
      <div>
        <h4 className="text-[11px] font-medium text-text-placeholder uppercase tracking-wide mb-2 flex items-center gap-1.5">
          <Puzzle className="w-3.5 h-3.5" />
          Linked Features
          {features.length > 0 && (
            <span className="text-[10px] bg-[#F0F0F0] text-[#666666] px-1.5 py-0.5 rounded-full ml-1">
              {features.length}
            </span>
          )}
        </h4>
        {features.length > 0 ? (
          <div className="border border-border rounded-xl overflow-hidden">
            {features.map((feature) => {
              const isConfirmed =
                feature.confirmation_status === 'confirmed_consultant' ||
                feature.confirmation_status === 'confirmed_client'
              return (
                <div
                  key={feature.id}
                  className="flex items-center gap-2.5 px-4 py-2.5 border-b border-[#F0F0F0] last:border-0"
                >
                  <Puzzle className="w-3.5 h-3.5 text-text-placeholder flex-shrink-0" />
                  <span className="text-[13px] text-text-body font-medium flex-1 truncate">
                    {feature.name}
                  </span>
                  {feature.category && (
                    <span className="text-[10px] text-text-placeholder bg-[#F0F0F0] px-1.5 py-0.5 rounded">
                      {feature.category}
                    </span>
                  )}
                  {isConfirmed && (
                    <Check className="w-3.5 h-3.5 text-brand-primary flex-shrink-0" />
                  )}
                </div>
              )
            })}
          </div>
        ) : (
          <div className="border border-dashed border-border rounded-xl px-4 py-3">
            <p className="text-[12px] text-text-placeholder italic">
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
        <div className="flex items-start gap-2.5 bg-[#F4F4F4] border border-border rounded-xl px-4 py-3">
          <Info className="w-4 h-4 mt-0.5 text-text-placeholder flex-shrink-0" />
          <div>
            <p className="text-[13px] font-medium text-text-body mb-1">Missing Voice</p>
            <p className="text-[12px] text-[#666666] leading-relaxed">
              No real stakeholders mapped to this persona. Consider interviewing someone who matches this role.
            </p>
          </div>
        </div>
      )}

      {/* Matched Stakeholders */}
      <div>
        <h4 className="text-[11px] font-medium text-text-placeholder uppercase tracking-wide mb-2 flex items-center gap-1.5">
          <Users className="w-3.5 h-3.5" />
          Matched Stakeholders
          {matchedStakeholders.length > 0 && (
            <span className="text-[10px] bg-[#F0F0F0] text-[#666666] px-1.5 py-0.5 rounded-full ml-1">
              {matchedStakeholders.length}
            </span>
          )}
        </h4>
        {matchedStakeholders.length > 0 ? (
          <div className="border border-border rounded-xl overflow-hidden">
            {matchedStakeholders.map((s) => (
              <div
                key={s.id}
                className="flex items-center gap-2.5 px-4 py-2.5 border-b border-[#F0F0F0] last:border-0"
              >
                <Users className="w-3.5 h-3.5 text-text-placeholder flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <span className="text-[13px] text-text-body font-medium">{s.name}</span>
                  {s.role && (
                    <span className="text-[11px] text-text-placeholder ml-2">{s.role}</span>
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
          <div className="border border-dashed border-border rounded-xl px-4 py-3">
            <p className="text-[12px] text-text-placeholder italic">
              No stakeholders with a matching role found.
            </p>
          </div>
        )}
      </div>

      {/* Stakeholder Coverage Summary */}
      <div>
        <h4 className="text-[11px] font-medium text-text-placeholder uppercase tracking-wide mb-2">
          Stakeholder Coverage
        </h4>
        <div className="border border-border rounded-xl px-4 py-3">
          <div className="grid grid-cols-3 gap-3">
            <div className="text-center">
              <p className="text-[18px] font-bold text-text-body">{totalStakeholders}</p>
              <p className="text-[10px] text-text-placeholder uppercase">Total</p>
            </div>
            <div className="text-center">
              <p className={`text-[18px] font-bold ${matchedStakeholders.length > 0 ? 'text-brand-primary' : 'text-text-placeholder'}`}>
                {matchedStakeholders.length}
              </p>
              <p className="text-[10px] text-text-placeholder uppercase">Matched</p>
            </div>
            <div className="text-center">
              <p className={`text-[18px] font-bold ${!hasVoice ? 'text-text-placeholder' : 'text-[#25785A]'}`}>
                {hasVoice ? 'Yes' : 'No'}
              </p>
              <p className="text-[10px] text-text-placeholder uppercase">Has Voice</p>
            </div>
          </div>

          {/* Coverage bar */}
          {totalStakeholders > 0 && (
            <div className="mt-3 pt-3 border-t border-[#F0F0F0]">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[11px] text-[#666666]">Role Match Rate</span>
                <span className="text-[11px] font-medium text-text-body">
                  {matchedStakeholders.length}/{totalStakeholders}
                </span>
              </div>
              <div className="h-2 bg-[#F0F0F0] rounded-full overflow-hidden">
                <div
                  className="h-full bg-brand-primary rounded-full transition-all"
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
    <EmptyState
      icon={<FileText className="w-8 h-8 text-border" />}
      title="Evidence sources available through signal analysis"
      description="Process signals referencing this persona to build an evidence trail."
    />
  )
}
