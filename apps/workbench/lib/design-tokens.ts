/**
 * Design System Tokens
 *
 * Central source of truth for colors, typography, spacing, and component styles.
 * Based on the brand style guide for clean, professional consultant workflow.
 */

// ============================================================================
// COLORS
// ============================================================================

export const colors = {
  // Primary & Accent
  primary: '#044159',      // Deep Ocean Blue - CTA, highlights
  accent: '#88BABF',       // Soft Aqua - subtle highlights, borders
  deepText: '#011F26',     // Midnight Navy - deep text, high contrast
  warmSand: '#F2E4BB',     // Warm Sand - neutral badge accent (optional)

  // UI Grays
  background: '#FAFAFA',   // Page background
  cardBorder: '#E5E5E5',   // Card borders
  bodyText: '#4B4B4B',     // Body text
  supportText: '#7B7B7B',  // Supporting/secondary text

  // Headings
  headingDark: '#1D1D1F',  // H1, section headers
  headingPrimary: '#044159', // H2, tab titles

  // UI Element Colors
  buttonGray: '#F5F5F5',
  buttonGrayHover: '#E5E5E5',
} as const

// Status Badge Colors
export const statusColors = {
  aiDraft: {
    bg: 'rgba(136, 186, 191, 0.1)', // accent with 10% opacity
    text: '#044159',
    label: 'AI DRAFT'
  },
  needsConfirmation: {
    bg: '#FEF3C7', // yellow-50
    text: '#B45309', // yellow-700
    label: 'NEEDS CONFIRMATION'
  },
  confirmedConsultant: {
    bg: '#DBEAFE', // blue-50
    text: '#1D4ED8', // blue-700
    label: 'CONFIRMED'
  },
  confirmedClient: {
    bg: '#D1FAE5', // green-50
    text: '#047857', // green-700
    label: 'CONFIRMED (CLIENT)'
  }
} as const

// Severity Badge Colors (for insights)
export const severityColors = {
  critical: {
    bg: '#FEE2E2', // red-50
    text: '#991B1B', // red-800
    label: 'CRITICAL'
  },
  important: {
    bg: '#FEF3C7', // yellow-50
    text: '#92400E', // yellow-800
    label: 'IMPORTANT'
  },
  minor: {
    bg: '#F3F4F6', // gray-50
    text: '#374151', // gray-800
    label: 'MINOR'
  }
} as const

// Gate Badge Colors (for insights)
export const gateColors = {
  completeness: {
    bg: '#DBEAFE', // blue-50
    text: '#1E40AF', // blue-800
    icon: '🔧',
    label: 'COMPLETENESS',
    description: 'Can we build a prototype?'
  },
  validation: {
    bg: '#D1FAE5', // green-50
    text: '#065F46', // green-800
    icon: '✓',
    label: 'VALIDATION',
    description: 'Is this optimal per research?'
  },
  assumption: {
    bg: '#FEF3C7', // yellow-50
    text: '#92400E', // yellow-800
    icon: '⚠',
    label: 'ASSUMPTION',
    description: 'Are assumptions solid?'
  },
  scope: {
    bg: '#E0E7FF', // indigo-50
    text: '#3730A3', // indigo-800
    icon: '🎯',
    label: 'SCOPE',
    description: 'Is VP staying focused?'
  },
  wow: {
    bg: '#FCE7F3', // pink-50
    text: '#831843', // pink-900
    icon: '✨',
    label: 'WOW FACTOR',
    description: 'Will this impress the client?'
  }
} as const

// Channel Badge Colors (for confirmations)
export const channelColors = {
  email: {
    bg: '#E0E7FF', // indigo-50
    text: '#3730A3', // indigo-800
    icon: '✉',
    label: 'EMAIL'
  },
  meeting: {
    bg: '#DBEAFE', // blue-50
    text: '#1E40AF', // blue-800
    icon: '📅',
    label: 'MEETING'
  }
} as const

// ============================================================================
// TYPOGRAPHY
// ============================================================================

export const typography = {
  h1: {
    fontSize: '26px',
    fontWeight: 600,
    color: colors.headingDark,
    lineHeight: '1.3'
  },
  h2: {
    fontSize: '20px',
    fontWeight: 500,
    color: colors.headingPrimary,
    lineHeight: '1.4'
  },
  sectionHeader: {
    fontSize: '18px',
    fontWeight: 600,
    color: colors.headingDark,
    lineHeight: '1.4'
  },
  body: {
    fontSize: '16px',
    fontWeight: 400,
    color: colors.bodyText,
    lineHeight: '1.5'
  },
  support: {
    fontSize: '13px',
    fontWeight: 400,
    color: colors.supportText,
    lineHeight: '1.5'
  },
  badge: {
    fontSize: '12px',
    fontWeight: 600,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.025em'
  }
} as const

// ============================================================================
// SPACING
// ============================================================================

export const spacing = {
  cardPadding: '16px',
  cardRadius: '8px',
  buttonPaddingY: '8px',
  buttonPaddingX: '16px',
  sectionGap: '24px',
  itemGap: '16px'
} as const

// ============================================================================
// SHADOWS
// ============================================================================

export const shadows = {
  card: '0 1px 2px rgba(0, 0, 0, 0.04)',
  cardHover: '0 4px 6px rgba(0, 0, 0, 0.08)',
  button: 'none',
  buttonHover: '0 2px 4px rgba(0, 0, 0, 0.1)'
} as const

// ============================================================================
// COMPONENT STYLES (for Tailwind classes)
// ============================================================================

export const componentClasses = {
  card: 'bg-white border border-[#E5E5E5] rounded-lg p-4 shadow-[0_1px_2px_rgba(0,0,0,0.04)]',
  cardHover: 'hover:shadow-[0_4px_6px_rgba(0,0,0,0.08)] transition-shadow',

  button: {
    base: 'px-4 py-2 rounded-lg font-medium transition-all duration-200 inline-flex items-center justify-center',
    primary: 'bg-[#044159] text-white hover:bg-[#033344]',
    secondary: 'bg-[#F5F5F5] text-[#4B4B4B] hover:bg-[#E5E5E5]',
    outline: 'bg-white border border-[#044159] text-[#044159] hover:bg-[#044159]/5',
    disabled: 'opacity-50 cursor-not-allowed'
  },

  badge: {
    base: 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wide',
  },

  input: 'w-full px-3 py-2 border border-[#E5E5E5] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#044159]/20 focus:border-[#044159]',

  twoColumn: {
    container: 'grid grid-cols-1 lg:grid-cols-12 gap-6',
    leftCol: 'lg:col-span-4 space-y-4',
    rightCol: 'lg:col-span-8'
  }
} as const

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

export type StatusType = 'draft' | 'confirmed_consultant' | 'needs_client' | 'confirmed_client'
export type SeverityType = 'critical' | 'important' | 'minor'
export type GateType = 'completeness' | 'validation' | 'assumption' | 'scope' | 'wow'
export type ChannelType = 'email' | 'meeting'
export type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost'
