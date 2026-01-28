/**
 * SourceTypeIcon Component
 *
 * Icon component for different source types.
 * Provides consistent iconography across the Sources tab.
 */

import {
  FileText,
  Mail,
  MessageSquare,
  Mic,
  Globe,
  File,
  Image,
  Table,
  Presentation,
  PenSquare,
  Lightbulb,
  BookOpen,
  type LucideIcon,
} from 'lucide-react'

type SourceType =
  | 'document'
  | 'pdf'
  | 'docx'
  | 'xlsx'
  | 'pptx'
  | 'image'
  | 'email'
  | 'note'
  | 'transcript'
  | 'chat'
  | 'research'
  | 'ai'
  | 'memory'

interface SourceTypeIconProps {
  /** Type of source */
  type: SourceType | string
  /** Size class */
  size?: 'sm' | 'md' | 'lg'
  /** Additional className */
  className?: string
}

const ICON_MAP: Record<string, LucideIcon> = {
  document: FileText,
  pdf: FileText,
  docx: FileText,
  xlsx: Table,
  pptx: Presentation,
  image: Image,
  email: Mail,
  note: PenSquare,
  transcript: Mic,
  chat: MessageSquare,
  research: Globe,
  ai: Lightbulb,
  memory: BookOpen,
}

const SIZE_MAP = {
  sm: 'w-4 h-4',
  md: 'w-5 h-5',
  lg: 'w-6 h-6',
}

export function SourceTypeIcon({ type, size = 'md', className = '' }: SourceTypeIconProps) {
  const Icon = ICON_MAP[type.toLowerCase()] || File
  const sizeClass = SIZE_MAP[size]

  return <Icon className={`${sizeClass} ${className}`} />
}

/**
 * Badge variant with background color
 */
interface SourceTypeBadgeProps {
  /** Type of source */
  type: SourceType | string
  /** Show label text */
  showLabel?: boolean
}

const TYPE_COLORS: Record<string, { bg: string; text: string }> = {
  document: { bg: 'bg-blue-50', text: 'text-blue-600' },
  pdf: { bg: 'bg-red-50', text: 'text-red-600' },
  docx: { bg: 'bg-blue-50', text: 'text-blue-600' },
  xlsx: { bg: 'bg-green-50', text: 'text-green-600' },
  pptx: { bg: 'bg-orange-50', text: 'text-orange-600' },
  image: { bg: 'bg-purple-50', text: 'text-purple-600' },
  email: { bg: 'bg-amber-50', text: 'text-amber-600' },
  note: { bg: 'bg-emerald-50', text: 'text-emerald-600' },
  transcript: { bg: 'bg-cyan-50', text: 'text-cyan-600' },
  chat: { bg: 'bg-indigo-50', text: 'text-indigo-600' },
  research: { bg: 'bg-violet-50', text: 'text-violet-600' },
  ai: { bg: 'bg-brand-primary/10', text: 'text-brand-primary' },
  memory: { bg: 'bg-pink-50', text: 'text-pink-600' },
}

const TYPE_LABELS: Record<string, string> = {
  document: 'Document',
  pdf: 'PDF',
  docx: 'Word',
  xlsx: 'Excel',
  pptx: 'PowerPoint',
  image: 'Image',
  email: 'Email',
  note: 'Note',
  transcript: 'Transcript',
  chat: 'Chat',
  research: 'Research',
  ai: 'AI Generated',
  memory: 'Memory',
}

export function SourceTypeBadge({ type, showLabel = true }: SourceTypeBadgeProps) {
  const colors = TYPE_COLORS[type.toLowerCase()] || { bg: 'bg-gray-50', text: 'text-gray-600' }
  const label = TYPE_LABELS[type.toLowerCase()] || type

  return (
    <div
      className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md ${colors.bg}`}
    >
      <SourceTypeIcon type={type} size="sm" className={colors.text} />
      {showLabel && (
        <span className={`text-xs font-medium ${colors.text}`}>{label}</span>
      )}
    </div>
  )
}
