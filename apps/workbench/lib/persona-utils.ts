/**
 * Persona Utilities
 *
 * Helper functions for parsing and working with personas from PRD sections.
 * Personas are stored in prd_sections where slug='personas' and can be in either:
 * - enrichment.enhanced_fields.personas (structured)
 * - fields.content (text that needs parsing)
 */

export interface Persona {
  name: string
  role: string
  demographics?: string
  psychographics?: string
  goals?: string[]
  pain_points?: string[]
  related_features?: string[]
  related_vp_steps?: number[]
  description?: string
}

/**
 * Parse personas from a PRD section
 *
 * Attempts to extract personas from enriched data first, then falls back to
 * parsing from text content if needed.
 */
export function parsePersonas(section: any): Persona[] {
  const personas: Persona[] = []

  // Try enriched structured data first
  if (section?.enrichment?.enhanced_fields?.personas) {
    const enrichedPersonas = section.enrichment.enhanced_fields.personas

    // Handle if it's already an array of persona objects
    if (Array.isArray(enrichedPersonas)) {
      return enrichedPersonas.map(normalizePersona)
    }

    // Handle if it's a JSON string
    if (typeof enrichedPersonas === 'string') {
      try {
        const parsed = JSON.parse(enrichedPersonas)
        if (Array.isArray(parsed)) {
          return parsed.map(normalizePersona)
        }
      } catch (e) {
        console.warn('Failed to parse enriched personas as JSON:', e)
        // Fall through to text parsing
      }
    }
  }

  // Fallback: Try to parse from text content
  const content = section?.enrichment?.enhanced_fields?.content || section?.fields?.content
  if (content && typeof content === 'string') {
    return parsePersonasFromText(content)
  }

  return personas
}

/**
 * Normalize a persona object to ensure consistent structure
 */
function normalizePersona(persona: any): Persona {
  return {
    name: persona.name || 'Unnamed Persona',
    role: persona.role || '',
    demographics: persona.demographics || '',
    psychographics: persona.psychographics || '',
    goals: Array.isArray(persona.goals) ? persona.goals : [],
    pain_points: Array.isArray(persona.pain_points) ? persona.pain_points : [],
    related_features: Array.isArray(persona.related_features) ? persona.related_features : [],
    related_vp_steps: Array.isArray(persona.related_vp_steps) ? persona.related_vp_steps : [],
    description: persona.description || '',
  }
}

/**
 * Parse personas from markdown/text content
 *
 * Looks for patterns like:
 * ## Persona Name
 * **Role:** description
 * **Demographics:** description
 * etc.
 */
function parsePersonasFromText(content: string): Persona[] {
  const personas: Persona[] = []

  // Split by ## headers (assuming each persona has its own section)
  const sections = content.split(/\n##\s+/).filter(Boolean)

  for (const section of sections) {
    const lines = section.split('\n').filter(Boolean)
    if (lines.length === 0) continue

    // First line is the persona name (remove any remaining # symbols)
    const name = lines[0].replace(/^#+\s*/, '').trim()

    const persona: Persona = {
      name,
      role: '',
      demographics: '',
      psychographics: '',
      goals: [],
      pain_points: [],
      description: '',
    }

    let currentField: string | null = null
    let currentContent = ''

    for (let i = 1; i < lines.length; i++) {
      const line = lines[i].trim()

      // Check if it's a field label
      const fieldMatch = line.match(/^\*\*([^:]+):\*\*\s*(.*)$/)
      if (fieldMatch) {
        // Save previous field if exists
        if (currentField && currentContent) {
          saveField(persona, currentField, currentContent.trim())
        }

        currentField = fieldMatch[1].toLowerCase().replace(/\s+/g, '_')
        currentContent = fieldMatch[2]
      } else if (currentField) {
        // Continue accumulating content for current field
        currentContent += ' ' + line
      } else if (!persona.description) {
        // If no field is active, it's part of the description
        persona.description += (persona.description ? ' ' : '') + line
      }
    }

    // Save final field
    if (currentField && currentContent) {
      saveField(persona, currentField, currentContent.trim())
    }

    personas.push(persona)
  }

  return personas
}

/**
 * Save a parsed field to the persona object
 */
function saveField(persona: Persona, field: string, content: string) {
  switch (field) {
    case 'role':
      persona.role = content
      break
    case 'demographics':
      persona.demographics = content
      break
    case 'psychographics':
      persona.psychographics = content
      break
    case 'goals':
    case 'goal':
      persona.goals = parseListField(content)
      break
    case 'pain_points':
    case 'pain':
    case 'pains':
    case 'challenges':
      persona.pain_points = parseListField(content)
      break
    case 'description':
    case 'overview':
      persona.description = content
      break
    default:
      // Unknown field - add to description
      persona.description += (persona.description ? '\n\n' : '') + `**${field}:** ${content}`
  }
}

/**
 * Parse a list field (e.g., "- Item 1\n- Item 2" or "Item 1, Item 2")
 */
function parseListField(content: string): string[] {
  // Try markdown list first
  if (content.includes('\n-') || content.startsWith('-')) {
    return content
      .split('\n')
      .filter(line => line.trim().startsWith('-'))
      .map(line => line.replace(/^-\s*/, '').trim())
      .filter(Boolean)
  }

  // Try comma-separated
  if (content.includes(',')) {
    return content.split(',').map(item => item.trim()).filter(Boolean)
  }

  // Single item
  return [content]
}

/**
 * Get related features for a persona
 *
 * Matches features that are mentioned in the persona's related_features list
 * or that mention the persona by name
 */
export function getRelatedFeatures(persona: Persona, allFeatures: any[]): any[] {
  if (!allFeatures || allFeatures.length === 0) return []

  return allFeatures.filter(feature => {
    // Check if feature is in related_features list
    if (persona.related_features && persona.related_features.includes(feature.name)) {
      return true
    }

    // Check if persona name appears in feature name or details
    const personaNameLower = persona.name.toLowerCase()
    const featureText = `${feature.name} ${JSON.stringify(feature.details || {})}`.toLowerCase()

    return featureText.includes(personaNameLower)
  })
}

/**
 * Get related VP steps for a persona
 *
 * Matches VP steps that are mentioned in the persona's related_vp_steps list
 * or that mention the persona by name
 */
export function getRelatedVpSteps(persona: Persona, allVpSteps: any[]): any[] {
  if (!allVpSteps || allVpSteps.length === 0) return []

  return allVpSteps.filter(step => {
    // Check if step index is in related_vp_steps list
    if (persona.related_vp_steps && persona.related_vp_steps.includes(step.step_index)) {
      return true
    }

    // Check if persona name appears in step description or label
    const personaNameLower = persona.name.toLowerCase()
    const stepText = `${step.label} ${step.description} ${step.user_benefit_pain}`.toLowerCase()

    return stepText.includes(personaNameLower)
  })
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

/**
 * Get a color for persona avatar based on name hash
 */
export function getPersonaColor(persona: Persona): { bg: string; text: string } {
  const colors = [
    { bg: 'bg-blue-100', text: 'text-blue-700' },
    { bg: 'bg-green-100', text: 'text-green-700' },
    { bg: 'bg-purple-100', text: 'text-purple-700' },
    { bg: 'bg-pink-100', text: 'text-pink-700' },
    { bg: 'bg-indigo-100', text: 'text-indigo-700' },
    { bg: 'bg-yellow-100', text: 'text-yellow-700' },
  ]

  // Simple hash based on name
  const hash = persona.name.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
  return colors[hash % colors.length]
}
