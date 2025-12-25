/**
 * Utilities for exporting meeting agendas
 */

export interface AgendaItem {
  topic: string
  time_allocation_minutes: number
  discussion_approach: string
  related_confirmation_ids: string[]
  key_questions: string[]
}

export interface MeetingAgenda {
  title: string
  summary: string
  suggested_duration_minutes: number
  agenda_items: AgendaItem[]
  confirmation_count: number
}

/**
 * Format meeting agenda as markdown
 */
export function exportAgendaAsMarkdown(agenda: MeetingAgenda): string {
  const lines: string[] = []

  // Title
  lines.push(`# ${agenda.title}`)
  lines.push('')

  // Summary
  lines.push(`**Summary:** ${agenda.summary}`)
  lines.push('')
  lines.push(
    `**Duration:** ${agenda.suggested_duration_minutes} minutes | **Items:** ${agenda.agenda_items.length} | **Confirmations:** ${agenda.confirmation_count}`
  )
  lines.push('')
  lines.push('---')
  lines.push('')

  // Agenda items
  agenda.agenda_items.forEach((item, index) => {
    lines.push(`## ${index + 1}. ${item.topic} (${item.time_allocation_minutes} min)`)
    lines.push('')

    // Discussion approach
    lines.push(`**Discussion Approach:**`)
    lines.push(item.discussion_approach)
    lines.push('')

    // Key questions
    if (item.key_questions && item.key_questions.length > 0) {
      lines.push(`**Key Questions:**`)
      item.key_questions.forEach((question) => {
        lines.push(`- ${question}`)
      })
      lines.push('')
    }

    // Related confirmations
    if (item.related_confirmation_ids && item.related_confirmation_ids.length > 0) {
      lines.push(
        `**Related Confirmations:** ${item.related_confirmation_ids.length} item${item.related_confirmation_ids.length !== 1 ? 's' : ''}`
      )
      lines.push('')
    }

    lines.push('---')
    lines.push('')
  })

  return lines.join('\n')
}

/**
 * Format meeting agenda as plain text
 */
export function exportAgendaAsText(agenda: MeetingAgenda): string {
  const lines: string[] = []

  // Title
  lines.push(agenda.title.toUpperCase())
  lines.push('='.repeat(agenda.title.length))
  lines.push('')

  // Summary
  lines.push(`Summary: ${agenda.summary}`)
  lines.push('')
  lines.push(
    `Duration: ${agenda.suggested_duration_minutes} minutes | Items: ${agenda.agenda_items.length} | Confirmations: ${agenda.confirmation_count}`
  )
  lines.push('')
  lines.push('-'.repeat(60))
  lines.push('')

  // Agenda items
  agenda.agenda_items.forEach((item, index) => {
    lines.push(`${index + 1}. ${item.topic} (${item.time_allocation_minutes} min)`)
    lines.push('')

    // Discussion approach
    lines.push(`   Discussion Approach:`)
    // Wrap text to 70 characters
    const wrappedApproach = wrapText(item.discussion_approach, 70, '   ')
    lines.push(wrappedApproach)
    lines.push('')

    // Key questions
    if (item.key_questions && item.key_questions.length > 0) {
      lines.push(`   Key Questions:`)
      item.key_questions.forEach((question) => {
        lines.push(`   • ${question}`)
      })
      lines.push('')
    }

    // Related confirmations
    if (item.related_confirmation_ids && item.related_confirmation_ids.length > 0) {
      lines.push(
        `   Related Confirmations: ${item.related_confirmation_ids.length} item${item.related_confirmation_ids.length !== 1 ? 's' : ''}`
      )
      lines.push('')
    }

    lines.push('-'.repeat(60))
    lines.push('')
  })

  return lines.join('\n')
}

/**
 * Wrap text to a specific line length
 */
function wrapText(text: string, maxLength: number, indent = ''): string {
  const words = text.split(' ')
  const lines: string[] = []
  let currentLine = indent

  words.forEach((word) => {
    if (currentLine.length + word.length + 1 > maxLength) {
      lines.push(currentLine)
      currentLine = indent + word
    } else {
      currentLine += (currentLine === indent ? '' : ' ') + word
    }
  })

  if (currentLine.length > indent.length) {
    lines.push(currentLine)
  }

  return lines.join('\n')
}

/**
 * Trigger browser download of agenda
 */
export function downloadAgenda(content: string, format: 'md' | 'txt', title: string) {
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url

  // Create filename from title
  const filename = title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '')

  link.download = `${filename}.${format}`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
