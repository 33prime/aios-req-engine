/**
 * PersonaRow - Horizontal display of personas
 *
 * Each persona shows as a compact card with name, role, description, and status.
 */

'use client'

import { User, CheckCircle, AlertCircle } from 'lucide-react'
import type { PersonaSummary } from '@/types/workspace'

interface PersonaRowProps {
  personas: PersonaSummary[]
  onPersonaClick?: (personaId: string) => void
}

function getStatusIndicator(status?: string | null) {
  switch (status) {
    case 'confirmed_client':
      return { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-50', border: 'border-l-green-400' }
    case 'confirmed_consultant':
      return { icon: CheckCircle, color: 'text-blue-500', bg: 'bg-blue-50', border: 'border-l-blue-400' }
    case 'needs_client':
    case 'needs_confirmation':
      return { icon: AlertCircle, color: 'text-amber-500', bg: 'bg-amber-50', border: 'border-l-amber-400' }
    default:
      return { icon: null, color: 'text-[#999999]', bg: 'bg-[#F9F9F9]', border: 'border-l-gray-300' }
  }
}

export function PersonaRow({ personas, onPersonaClick }: PersonaRowProps) {
  if (personas.length === 0) {
    return (
      <div className="bg-[#F9F9F9] rounded-lg border border-dashed border-[#E5E5E5] p-8 text-center">
        <User className="w-10 h-10 text-gray-300 mx-auto mb-3" />
        <p className="text-sm text-[#999999]">No personas defined yet</p>
        <p className="text-[12px] text-[#999999] mt-1">
          Add signals about your users to generate personas
        </p>
      </div>
    )
  }

  return (
    <div className="flex gap-3 overflow-x-auto pb-2">
      {personas.map((persona) => {
        const status = getStatusIndicator(persona.confirmation_status)
        const StatusIcon = status.icon

        return (
          <button
            key={persona.id}
            onClick={() => onPersonaClick?.(persona.id)}
            className={`
              flex-shrink-0 w-56 bg-white rounded-lg border border-[#E5E5E5] shadow-sm p-4
              border-l-[3px] ${status.border}
              hover:border-[#3FAF7A]/30 hover:shadow-md transition-all text-left
            `}
          >
            <div className="flex items-start gap-3">
              <div className={`w-10 h-10 rounded-full ${status.bg} flex items-center justify-center`}>
                <User className={`w-5 h-5 ${status.color}`} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <h3 className="text-sm font-semibold text-[#333333] truncate">
                    {persona.name}
                  </h3>
                  {StatusIcon && (
                    <StatusIcon className={`w-3.5 h-3.5 ${status.color} flex-shrink-0`} />
                  )}
                  {(() => {
                    if (persona.confirmation_status && persona.confirmation_status !== 'ai_generated') return null
                    if (!persona.created_at) return null
                    const age = Date.now() - new Date(persona.created_at).getTime()
                    if (age >= 24 * 60 * 60 * 1000) return null
                    const isNew = persona.version === 1 || persona.version == null
                    return (
                      <span className={`px-1 py-px text-[9px] font-bold text-white rounded leading-tight flex-shrink-0 ${isNew ? 'bg-emerald-500' : 'bg-indigo-500'}`}>
                        {isNew ? 'NEW' : 'UPDATED'}
                      </span>
                    )
                  })()}
                </div>
                {persona.role && (
                  <p className="text-[12px] text-[#999999] truncate mt-0.5">
                    {persona.role}
                  </p>
                )}
                {persona.description && (
                  <p className="text-[12px] text-[#333333] mt-1 line-clamp-2">
                    {persona.description}
                  </p>
                )}
                {persona.persona_type && (
                  <span className="inline-block mt-1.5 px-2 py-0.5 text-xs font-semibold rounded-full bg-[#F9F9F9] text-[#333333] capitalize">
                    {persona.persona_type.replace('_', ' ')}
                  </span>
                )}
              </div>
            </div>
          </button>
        )
      })}
    </div>
  )
}

export default PersonaRow
