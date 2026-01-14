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

/**
 * Format meeting agenda as plain text
 */
export function exportAgendaAsText(agenda: MeetingAgenda): string {
  const lines: string[] = []

  // Title
  lines.push(agenda.title.toUpperCase())
  lines.push('='.repeat(agenda.title.length))
  lines.push('')

  // Duration and count
  lines.push(
    `Duration: ${agenda.duration_estimate} | Items: ${agenda.agenda.length} | Confirmations: ${agenda.confirmation_count}`
  )
  lines.push('')

  // Pre-read
  if (agenda.pre_read) {
    lines.push(`Pre-read for client:`)
    const wrappedPreRead = wrapText(agenda.pre_read, 70, '   ')
    lines.push(wrappedPreRead)
    lines.push('')
  }

  lines.push('-'.repeat(60))
  lines.push('')

  // Agenda items
  agenda.agenda.forEach((item, index) => {
    lines.push(`${index + 1}. ${item.topic} (${item.time_minutes} min)`)
    lines.push('')

    // Description
    if (item.description) {
      const wrappedDescription = wrapText(item.description, 70, '   ')
      lines.push(wrappedDescription)
      lines.push('')
    }

    // Related confirmations
    if (item.confirmation_ids && item.confirmation_ids.length > 0) {
      lines.push(
        `   Related Confirmations: ${item.confirmation_ids.length} item${item.confirmation_ids.length !== 1 ? 's' : ''}`
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
