/**
 * NestedPersonas Component
 *
 * Displays parsed personas within Personas section detail view.
 * Supports both card grid view and text view with modal detail expansion.
 */

'use client'

import React, { useState } from 'react'
import { Users, LayoutGrid, List } from 'lucide-react'
import { Card } from '@/components/ui'
import PersonaCard from '@/components/personas/PersonaCard'
import PersonaModal from '@/components/personas/PersonaModal'
import { parsePersonasFromText, type Persona } from '@/lib/persona-utils'

interface NestedPersonasProps {
  content: string
  enrichedContent?: string
  /** Structured persona data if available (preferred over parsing) */
  structuredPersonas?: Persona[]
}

export function NestedPersonas({ content, enrichedContent, structuredPersonas }: NestedPersonasProps) {
  const [viewMode, setViewMode] = useState<'cards' | 'text'>('cards')
  const [selectedPersona, setSelectedPersona] = useState<Persona | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  // Use structured personas if available, otherwise parse from text
  let personas: Persona[] = []

  if (structuredPersonas && structuredPersonas.length > 0) {
    personas = structuredPersonas
  } else {
    const textToParse = enrichedContent || content
    personas = parsePersonasFromText(textToParse)
  }

  if (personas.length === 0) {
    return (
      <Card>
        <div className="p-4">
          <div className="flex items-center gap-2 mb-4">
            <Users className="h-5 w-5 text-brand-primary" />
            <h4 className="font-semibold text-ui-bodyText">Personas</h4>
          </div>
          <div className="text-center py-6 bg-ui-background rounded-lg border border-ui-cardBorder">
            <p className="text-sm text-ui-supportText">
              Unable to parse individual personas. Content displayed as text above.
            </p>
          </div>
        </div>
      </Card>
    )
  }

  const handleCardClick = (persona: Persona) => {
    setSelectedPersona(persona)
    setIsModalOpen(true)
  }

  const handleCloseModal = () => {
    setIsModalOpen(false)
    setSelectedPersona(null)
  }

  return (
    <>
      <Card>
        <div className="p-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Users className="h-5 w-5 text-brand-primary" />
              <h4 className="font-semibold text-ui-bodyText">Personas</h4>
              <span className="text-xs text-ui-supportText">({personas.length})</span>
            </div>

            {/* View mode toggle */}
            <div className="flex items-center gap-1 bg-ui-background rounded-lg p-1 border border-ui-cardBorder">
              <button
                onClick={() => setViewMode('cards')}
                className={`p-1.5 rounded transition-colors ${
                  viewMode === 'cards'
                    ? 'bg-brand-primary text-white'
                    : 'text-ui-supportText hover:text-ui-bodyText'
                }`}
                title="Card view"
              >
                <LayoutGrid className="h-4 w-4" />
              </button>
              <button
                onClick={() => setViewMode('text')}
                className={`p-1.5 rounded transition-colors ${
                  viewMode === 'text'
                    ? 'bg-brand-primary text-white'
                    : 'text-ui-supportText hover:text-ui-bodyText'
                }`}
                title="Text view"
              >
                <List className="h-4 w-4" />
              </button>
            </div>
          </div>

          {viewMode === 'cards' ? (
            /* Card Grid View */
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {personas.map((persona, idx) => (
                <PersonaCard
                  key={persona.id || idx}
                  persona={persona}
                  onClick={() => handleCardClick(persona)}
                />
              ))}
            </div>
          ) : (
            /* Text View (original layout) */
            <div className="space-y-3">
              {personas.map((persona, idx) => (
                <div
                  key={persona.id || idx}
                  className="bg-ui-background border border-ui-cardBorder rounded-lg p-4 cursor-pointer hover:border-brand-primary transition-colors"
                  onClick={() => handleCardClick(persona)}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <Users className="h-5 w-5 text-brand-primary" />
                    <h5 className="font-semibold text-ui-bodyText">{persona.name}</h5>
                  </div>
                  {persona.role && (
                    <div className="text-sm font-medium text-ui-supportText mb-2">
                      {persona.role}
                    </div>
                  )}
                  <p className="text-sm text-ui-bodyText">{persona.description}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </Card>

      {/* Persona Detail Modal */}
      <PersonaModal
        persona={selectedPersona}
        isOpen={isModalOpen}
        onClose={handleCloseModal}
      />
    </>
  )
}
