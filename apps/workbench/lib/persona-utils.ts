/**
 * Persona Utilities
 *
 * Helper functions for parsing and working with personas.
 * Personas are stored in the personas table with structured fields:
 * - name, role, demographics, psychographics, goals, pain_points, etc.
 */

import type { Persona } from '@/types/api'
export type { Persona }

/**
 * Convert dict-based demographics/psychographics to display string
 */
export function formatDemographicsOrPsychographics(value: string | Record<string, any> | undefined): string {
  if (!value) return ''
  if (typeof value === 'string') return value
  // Convert dict to readable string
  const entries = Object.entries(value).filter(([_, v]) => v)
  if (entries.length === 0) return ''
  return entries.map(([k, v]) => `${k}: ${v}`).join(', ')
}

/**
 * Get avatar initials for a persona
 */
export function getPersonaInitials(persona: Persona): string {
  const names = persona.name.split(' ').filter(Boolean)
  if (names.length >= 2) {
    return (names[0][0] + names[1][0]).toUpperCase()
  }
  return persona.name.substring(0, 2).toUpperCase()
}

