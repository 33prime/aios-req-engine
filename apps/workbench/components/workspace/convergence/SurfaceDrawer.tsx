'use client'

import { useState } from 'react'
import { X, Users, Target, GitBranch, MessageCircle } from 'lucide-react'
import type { SolutionSurface, SurfaceExperience } from '@/types/workspace'

// ══════════════════════════════════════════════════════════
// Color helpers
// ══════════════════════════════════════════════════════════

const OC_COLORS = [
  '#3FAF7A', '#044159', '#C49A1A', '#0A1E2F', '#2D6B4A', '#6B4A2D',
]
const PERSONA_PALETTE = ['#3FAF7A', '#044159', '#0A1E2F', '#2D6B4A', '#C49A1A']
const pColorMap: Record<string, string> = {}
let pcIdx = 0
function getPersonaColor(name: string) {
  if (!pColorMap[name]) { pColorMap[name] = PERSONA_PALETTE[pcIdx % PERSONA_PALETTE.length]; pcIdx++ }
  return pColorMap[name]
}

// ══════════════════════════════════════════════════════════
// Props
// ══════════════════════════════════════════════════════════

interface Outcome {
  id: string
  title: string
  horizon: string
  strength_score: number
  actors: Array<{ persona_name: string }>
}

interface SurfaceDrawerProps {
  projectId: string
  surfaceId: string | null
  surfaces: SolutionSurface[]
  outcomes: Outcome[]
  onClose: () => void
}

type DrawerTab = 'experience' | 'detail' | 'chat'

// ══════════════════════════════════════════════════════════
// Component
// ══════════════════════════════════════════════════════════

export function SurfaceDrawer({ projectId, surfaceId, surfaces, outcomes, onClose }: SurfaceDrawerProps) {
  const [tab, setTab] = useState<DrawerTab>('experience')

  const surface = surfaceId ? surfaces.find(s => s.id === surfaceId) : null
  const isOpen = !!surface

  return (
    <div className={`flex-shrink-0 transition-all duration-250 ease-in-out overflow-hidden ${isOpen ? 'w-[430px]' : 'w-0'}`}
      style={{ boxShadow: isOpen ? '-4px 0 24px rgba(0,0,0,0.08)' : 'none' }}
    >
      {surface && (
        <div className="w-[430px] h-full bg-white flex flex-col border-l border-[#E5E5E5]">
          {/* Header */}
          <div className="px-[18px] py-4 border-b border-[#E5E5E5] flex items-start gap-3 flex-shrink-0">
            <div className="w-8 h-8 rounded-lg bg-[rgba(0,0,0,0.02)] border border-[#E5E5E5] flex items-center justify-center gap-[2px] flex-shrink-0">
              <div className="w-[3px] h-[3px] rounded-full bg-[rgba(220,80,80,0.3)]" />
              <div className="w-[3px] h-[3px] rounded-full bg-[rgba(212,180,50,0.4)]" />
              <div className="w-[3px] h-[3px] rounded-full bg-[rgba(63,175,122,0.35)]" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-[14px] font-bold text-[#1D1D1F] leading-[1.3]">{surface.title}</span>
                {surface.horizon !== 'h1' && (
                  <span className={`text-[8px] font-bold px-[5px] py-[1px] rounded ${
                    surface.horizon === 'h2' ? 'bg-[rgba(4,65,89,0.06)] text-[#044159]' : 'bg-[rgba(196,154,26,0.06)] text-[#C49A1A]'
                  }`}>
                    {surface.horizon.toUpperCase()}
                  </span>
                )}
              </div>
              <div className="text-[10px] text-[#A0AEC0] font-mono mt-0.5">{surface.route}</div>
            </div>
            <button onClick={onClose} className="p-1 rounded text-[#A0AEC0] hover:text-[#1D1D1F] hover:bg-[#F3F4F6] transition-colors flex-shrink-0">
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Tabs */}
          <div className="flex border-b border-[#E5E5E5] flex-shrink-0">
            {(['experience', 'detail', 'chat'] as const).map(t => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`flex-1 py-2 text-[10px] font-semibold text-center border-b-2 transition-colors ${
                  tab === t ? 'text-[#3FAF7A] border-[#3FAF7A]' : 'text-[#A0AEC0] border-transparent hover:text-[#7B7B7B]'
                }`}
              >
                {t === 'experience' ? 'Experience' : t === 'detail' ? 'Detail' : 'Chat'}
              </button>
            ))}
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto px-[18px] py-[14px]">
            {tab === 'experience' && <ExperienceTab experience={surface.experience as SurfaceExperience} />}
            {tab === 'detail' && (
              <DetailTab
                surface={surface}
                surfaces={surfaces}
                outcomes={outcomes}
              />
            )}
            {tab === 'chat' && <ChatTab surfaceTitle={surface.title} />}
          </div>

          {/* Footer */}
          <div className="px-[18px] py-3 border-t border-[#E5E5E5] flex gap-2 flex-shrink-0">
            <button className="text-[10px] font-semibold px-3 py-[6px] rounded-md border border-[#E5E5E5] text-[#7B7B7B] hover:border-[#3FAF7A] hover:text-[#25785A] hover:bg-[rgba(63,175,122,0.02)] transition-colors flex items-center gap-1.5">
              Open in BRD →
            </button>
            <button className="text-[10px] font-semibold px-3 py-[6px] rounded-md border border-[#E5E5E5] text-[#7B7B7B] hover:border-[#3FAF7A] hover:text-[#25785A] hover:bg-[rgba(63,175,122,0.02)] transition-colors flex items-center gap-1.5">
              <MessageCircle className="w-3 h-3" /> Discuss
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ══════════════════════════════════════════════════════════
// Experience Tab
// ══════════════════════════════════════════════════════════

function ExperienceTab({ experience }: { experience: SurfaceExperience | Record<string, never> }) {
  if (!experience || !experience.narr) {
    return (
      <div className="flex flex-col items-center justify-center py-10 gap-2">
        <div className="text-[14px] opacity-30">🎨</div>
        <p className="text-[12px] text-[#A0AEC0] text-center leading-relaxed">
          Experience details will be defined as this surface moves into design.
        </p>
      </div>
    )
  }

  const exp = experience as SurfaceExperience

  return (
    <div className="space-y-3">
      {/* Narrative */}
      <div className="text-[12px] text-[#4A5568] leading-[1.65] italic p-3 bg-[rgba(63,175,122,0.04)] rounded-lg border-l-[3px] border-[#3FAF7A]">
        {exp.narr}
      </div>

      {/* Layout */}
      <Block label="Layout">
        <div className="text-[12px] text-[#1D1D1F] font-medium">{exp.layout}</div>
      </Block>

      {/* Key elements */}
      <Block label="Key Elements">
        <div className="flex flex-wrap gap-1.5">
          {exp.elements.map(el => (
            <span key={el} className="text-[10px] font-medium px-2.5 py-1 rounded-md bg-white border border-[#E5E5E5] text-[#7B7B7B]">{el}</span>
          ))}
        </div>
      </Block>

      {/* How it feels */}
      <Block label="How it feels to use">
        <div className="text-[12px] text-[#1D1D1F]">{exp.interaction}</div>
      </Block>

      {/* Emotional tone */}
      <Block label="Emotional tone">
        <div className="text-[12px] text-[#1D1D1F]">{exp.tone}</div>
      </Block>

      {/* Reference */}
      <Block label="Think of it like">
        <div className="text-[12px] text-[#A0AEC0] italic">{exp.reference}</div>
      </Block>
    </div>
  )
}

function Block({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="p-3 bg-[rgba(0,0,0,0.012)] rounded-lg border border-[rgba(0,0,0,0.03)]">
      <div className="text-[9px] font-bold uppercase tracking-[0.05em] text-[#044159] mb-1.5">{label}</div>
      {children}
    </div>
  )
}

// ══════════════════════════════════════════════════════════
// Detail Tab
// ══════════════════════════════════════════════════════════

function DetailTab({
  surface, surfaces, outcomes,
}: {
  surface: SolutionSurface
  surfaces: SolutionSurface[]
  outcomes: Outcome[]
}) {
  // Roadmap insight (H2/H3)
  const showRoadmap = surface.roadmap_insight && (surface.horizon === 'h2' || surface.horizon === 'h3')

  // Linked outcomes
  const linkedOcs = surface.linked_outcome_ids
    .map(oid => outcomes.find(o => o.id === oid))
    .filter(Boolean) as Outcome[]

  // Unique actors
  const actorSet = new Set<string>()
  linkedOcs.forEach(oc => oc.actors?.forEach(a => actorSet.add(a.persona_name)))

  // Evolution
  const evolvesFrom = surface.evolves_from_id ? surfaces.find(s => s.id === surface.evolves_from_id) : null
  const evolvesTo = surfaces.filter(s => s.evolves_from_id === surface.id)

  return (
    <div className="space-y-4">
      {/* Roadmap insight */}
      {showRoadmap && (
        <div className={`p-3 rounded-lg border-l-[3px] ${
          surface.horizon === 'h3'
            ? 'bg-[rgba(196,154,26,0.02)] border-[#C49A1A]'
            : 'bg-[rgba(4,65,89,0.02)] border-[#044159]'
        }`}>
          <div className={`text-[8px] font-bold uppercase tracking-[0.05em] mb-1 ${
            surface.horizon === 'h3' ? 'text-[#C49A1A]' : 'text-[#044159]'
          }`}>
            {surface.horizon === 'h3' ? 'How we get here' : 'Path from Now'}
          </div>
          <div className="text-[12px] text-[#1D1D1F] leading-[1.6]">{surface.roadmap_insight}</div>
        </div>
      )}

      {/* Convergence insight */}
      {surface.convergence_insight && (
        <Section label="Convergence Insight">
          <div className="text-[12px] text-[#044159] font-medium leading-[1.55]">{surface.convergence_insight}</div>
        </Section>
      )}

      {/* Outcomes served */}
      {linkedOcs.length > 0 && (
        <Section label={`Outcomes served (${linkedOcs.length})`}>
          {linkedOcs.map((oc, i) => {
            const howServed = surface.how_served?.[oc.id]
            return (
              <div key={oc.id} className="flex gap-2 py-2 border-b border-[#F5F6F7] last:border-none">
                <div
                  className="w-[18px] h-[18px] rounded-[5px] flex items-center justify-center text-[8px] font-extrabold text-white flex-shrink-0 mt-0.5"
                  style={{ background: OC_COLORS[i % OC_COLORS.length] }}
                >
                  {i + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-[8px] font-bold uppercase tracking-[0.3px] mb-0.5"
                    style={{ color: getPersonaColor(oc.actors?.[0]?.persona_name || '') }}>
                    {oc.actors?.[0]?.persona_name || ''}
                  </div>
                  <div className="text-[11px] font-semibold text-[#0A1E2F] leading-[1.3]">{oc.title}</div>
                  {howServed && (
                    <div className="text-[10px] text-[#25785A] font-medium mt-1 leading-[1.4]">{howServed}</div>
                  )}
                </div>
              </div>
            )
          })}
        </Section>
      )}

      {/* Actors */}
      {actorSet.size > 0 && (
        <Section label="Actors">
          {[...actorSet].map(name => {
            const color = getPersonaColor(name)
            return (
              <div key={name} className="flex gap-2 p-2 border border-[#F0F2F4] rounded-lg mb-1.5 last:mb-0" style={{ borderLeftColor: color, borderLeftWidth: 3 }}>
                <div className="w-[22px] h-[22px] rounded-md flex items-center justify-center text-[8px] font-bold text-white flex-shrink-0" style={{ background: color }}>
                  {name.split(' ').map(w => w[0]).join('').slice(0, 2)}
                </div>
                <div>
                  <div className="text-[11px] font-semibold text-[#0A1E2F]">{name}</div>
                </div>
              </div>
            )
          })}
        </Section>
      )}

      {/* Capabilities */}
      {surface.linked_feature_ids.length > 0 && (
        <Section label={`Capabilities (${surface.linked_feature_ids.length})`}>
          <div className="text-[11px] text-[#7B7B7B]">
            {surface.linked_feature_ids.length} feature{surface.linked_feature_ids.length !== 1 ? 's' : ''} linked to this surface
          </div>
        </Section>
      )}

      {/* Evolution */}
      {evolvesFrom && (
        <Section label="Evolves from">
          <div className="flex items-center gap-2 p-2 rounded-lg bg-[rgba(4,65,89,0.02)] border border-[rgba(4,65,89,0.06)]">
            <span className="text-[14px] text-[#044159] flex-shrink-0">←</span>
            <div>
              <div className="text-[11px] font-semibold text-[#044159]">{evolvesFrom.title}</div>
              <div className="text-[9px] text-[#7B7B7B] mt-0.5">{evolvesFrom.route}</div>
            </div>
          </div>
        </Section>
      )}
      {evolvesTo.length > 0 && (
        <Section label="Evolves into">
          {evolvesTo.map(et => (
            <div key={et.id} className="flex items-center gap-2 p-2 rounded-lg bg-[rgba(4,65,89,0.02)] border border-[rgba(4,65,89,0.06)] mb-1.5 last:mb-0">
              <span className="text-[14px] text-[#044159] flex-shrink-0">→</span>
              <div>
                <div className="text-[11px] font-semibold text-[#044159]">{et.title}</div>
                <div className="text-[9px] text-[#7B7B7B] mt-0.5">{et.route} · {et.horizon.toUpperCase()}</div>
              </div>
            </div>
          ))}
        </Section>
      )}
    </div>
  )
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-[9px] font-bold uppercase tracking-[0.05em] text-[#A0AEC0] mb-2">{label}</div>
      {children}
    </div>
  )
}

// ══════════════════════════════════════════════════════════
// Chat Tab (placeholder)
// ══════════════════════════════════════════════════════════

function ChatTab({ surfaceTitle }: { surfaceTitle: string }) {
  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 flex flex-col items-center justify-center gap-2 py-8">
        <div className="text-[20px] opacity-30">💬</div>
        <p className="text-[11px] text-[#A0AEC0] text-center leading-relaxed">
          Ask about this surface —<br />convergence, capabilities, risks
        </p>
      </div>
      <div className="flex gap-2 pt-2 border-t border-[#F0F2F4]">
        <input
          type="text"
          placeholder={`Ask about ${surfaceTitle}...`}
          className="flex-1 px-3 py-2 border border-[#E5E5E5] rounded-lg text-[11px] outline-none focus:border-[#3FAF7A] font-[inherit]"
        />
        <button className="px-3.5 py-2 bg-[#3FAF7A] text-white border-none rounded-lg text-[10px] font-semibold cursor-pointer">
          Send
        </button>
      </div>
    </div>
  )
}
