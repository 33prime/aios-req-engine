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
      return { icon: null, color: 'text-ui-supportText', bg: 'bg-ui-background', border: 'border-l-gray-300' }
  }
}

export function PersonaRow({ personas, onPersonaClick }: PersonaRowProps) {
  if (personas.length === 0) {
    return (
      <div className="bg-ui-background rounded-card border border-dashed border-ui-cardBorder p-8 text-center">
        <User className="w-10 h-10 text-gray-300 mx-auto mb-3" />
        <p className="text-sm text-ui-supportText">No personas defined yet</p>
        <p className="text-support text-ui-supportText mt-1">
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
              flex-shrink-0 w-56 bg-white rounded-card border border-ui-cardBorder shadow-card p-4
              border-l-[3px] ${status.border}
              hover:border-brand-teal/30 hover:shadow-card-hover transition-all text-left
            `}
          >
            <div className="flex items-start gap-3">
              <div className={`w-10 h-10 rounded-full ${status.bg} flex items-center justify-center`}>
                <User className={`w-5 h-5 ${status.color}`} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <h3 className="text-sm font-semibold text-ui-headingDark truncate">
                    {persona.name}
                  </h3>
                  {StatusIcon && (
                    <StatusIcon className={`w-3.5 h-3.5 ${status.color} flex-shrink-0`} />
                  )}
                </div>
                {persona.role && (
                  <p className="text-support text-ui-supportText truncate mt-0.5">
                    {persona.role}
                  </p>
                )}
                {persona.description && (
                  <p className="text-support text-ui-bodyText mt-1 line-clamp-2">
                    {persona.description}
                  </p>
                )}
                {persona.persona_type && (
                  <span className="inline-block mt-1.5 px-2 py-0.5 text-badge rounded-full bg-ui-background text-ui-bodyText capitalize">
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
