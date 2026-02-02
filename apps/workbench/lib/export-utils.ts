/**
 * Utilities for exporting meeting agendas
 */

export interface AgendaItem {
  topic: string
  description: string
  time_minutes: number
  confirmation_ids: string[]
}

export interface MeetingAgenda {
  title: string
  duration_estimate: string
  agenda: AgendaItem[]
  pre_read: string
  confirmation_count: number
  confirmations_included: string[]
}

/**
 * Format meeting agenda as markdown
 */
export function exportAgendaAsMarkdown(agenda: MeetingAgenda): string {
  const lines: string[] = []

  // Title
  lines.push(`# ${agenda.title}`)
  lines.push('')

  // Duration and count
  lines.push(`**Duration:** ${agenda.duration_estimate} | **Items:** ${agenda.agenda.length} | **Confirmations:** ${agenda.confirmation_count}`)
  lines.push('')

  // Pre-read
  if (agenda.pre_read) {
    lines.push(`**Pre-read for client:**`)
    lines.push(agenda.pre_read)
    lines.push('')
  }

  lines.push('---')
  lines.push('')

  // Agenda items
  agenda.agenda.forEach((item, index) => {
    lines.push(`## ${index + 1}. ${item.topic} (${item.time_minutes} min)`)
    lines.push('')

    // Description
    if (item.description) {
      lines.push(item.description)
      lines.push('')
    }

    // Related confirmations
    if (item.confirmation_ids && item.confirmation_ids.length > 0) {
      lines.push(
        `**Related Confirmations:** ${item.confirmation_ids.length} item${item.confirmation_ids.length !== 1 ? 's' : ''}`
      )
      lines.push('')
    }

    lines.push('---')
    lines.push('')
  })

  return lines.join('\n')
}

