/**
 * TwoColumnLayout Component
 *
 * Standard two-column workspace layout:
 * - Left column: List/navigation (sticky on desktop)
 * - Right column: Detail view
 *
 * Responsive:
 * - Desktop: Two columns side by side
 * - Mobile/Tablet: Stacked (list on top, detail below)
 *
 * Usage:
 *   <TwoColumnLayout
 *     left={<MyList />}
 *     right={<MyDetail />}
 *   />
 */

import React, { ReactNode } from 'react'

interface TwoColumnLayoutProps {
  left: ReactNode
  right: ReactNode
  leftWidth?: 'narrow' | 'medium' | 'wide'
  stickyLeft?: boolean
  className?: string
}

export function TwoColumnLayout({
  left,
  right,
  leftWidth = 'medium',
  stickyLeft = true,
  className = ''
}: TwoColumnLayoutProps) {
  // Define left column widths
  const widthClasses = {
    narrow: 'lg:col-span-3',   // 3/12 = 25%
    medium: 'lg:col-span-4',   // 4/12 = 33%
    wide: 'lg:col-span-5'      // 5/12 = 42%
  }

  const rightWidthClasses = {
    narrow: 'lg:col-span-9',   // 9/12 = 75%
    medium: 'lg:col-span-8',   // 8/12 = 67%
    wide: 'lg:col-span-7'      // 7/12 = 58%
  }

  return (
    <div className={`grid grid-cols-1 lg:grid-cols-12 gap-6 ${className}`}>
      {/* Left Column (List) */}
      <div className={`${widthClasses[leftWidth]}`}>
        <div className={stickyLeft ? 'sticky-sidebar' : ''}>
          {left}
        </div>
      </div>

      {/* Right Column (Detail) */}
      <div className={`${rightWidthClasses[leftWidth]}`}>
        {right}
      </div>
    </div>
  )
}

/**
 * LeftColumn Component
 *
 * Wrapper for left column content with consistent styling
 */

interface ColumnProps {
  children: ReactNode
  title?: string
  subtitle?: string
  actions?: ReactNode
  className?: string
}

export function LeftColumn({ children, title, subtitle, actions, className = '' }: ColumnProps) {
  return (
    <div className={`space-y-4 ${className}`}>
      {(title || subtitle || actions) && (
        <div className="mb-4">
          {title && (
            <h2 className="text-h2 text-brand-primary">
              {title}
            </h2>
          )}
          {subtitle && (
            <p className="text-support text-ui-supportText mt-1">
              {subtitle}
            </p>
          )}
          {actions && (
            <div className="mt-3">
              {actions}
            </div>
          )}
        </div>
      )}
      <div className="custom-scrollbar">
        {children}
      </div>
    </div>
  )
}

/**
 * RightColumn Component
 *
 * Wrapper for right column content with consistent styling
 */

export function RightColumn({ children, title, subtitle, actions, className = '' }: ColumnProps) {
  return (
    <div className={`space-y-6 ${className}`}>
      {(title || subtitle || actions) && (
        <div className="mb-6">
          {title && (
            <h2 className="text-h2 text-brand-primary">
              {title}
            </h2>
          )}
          {subtitle && (
            <p className="text-support text-ui-supportText mt-1">
              {subtitle}
            </p>
          )}
          {actions && (
            <div className="mt-4 flex items-center gap-2">
              {actions}
            </div>
          )}
        </div>
      )}
      {children}
    </div>
  )
}

/**
 * ListItem Component
 *
 * Reusable list item for left column (selectable card)
 */

interface ListItemProps {
  title: string
  subtitle?: string
  meta?: ReactNode
  badge?: ReactNode
  active?: boolean
  onClick: () => void
  className?: string
}

export function ListItem({
  title,
  subtitle,
  meta,
  badge,
  active = false,
  onClick,
  className = ''
}: ListItemProps) {
  return (
    <div
      className={`
        list-item-base
        ${active ? 'active' : ''}
        ${className}
      `}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onClick()
        }
      }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <h4 className="font-medium text-ui-bodyText truncate">
            {title}
          </h4>
          {subtitle && (
            <p className="text-support text-ui-supportText mt-1 line-clamp-2">
              {subtitle}
            </p>
          )}
          {meta && (
            <div className="mt-2 text-xs text-ui-supportText">
              {meta}
            </div>
          )}
        </div>
        {badge && (
          <div className="flex-shrink-0">
            {badge}
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * DetailSection Component
 *
 * Section within the detail view (right column)
 */

interface DetailSectionProps {
  title?: string
  children: ReactNode
  collapsible?: boolean
  defaultOpen?: boolean
  className?: string
}

export function DetailSection({
  title,
  children,
  collapsible = false,
  defaultOpen = true,
  className = ''
}: DetailSectionProps) {
  const [isOpen, setIsOpen] = React.useState(defaultOpen)

  if (!collapsible) {
    return (
      <div className={`${className}`}>
        {title && (
          <h3 className="heading-section mb-3">
            {title}
          </h3>
        )}
        <div className="text-body">
          {children}
        </div>
      </div>
    )
  }

  return (
    <div className={`${className}`}>
      {title && (
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="w-full flex items-center justify-between heading-section mb-3 hover:text-brand-primary transition-colors"
        >
          <span>{title}</span>
          <svg
            className={`w-5 h-5 transition-transform ${isOpen ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      )}
      {isOpen && (
        <div className="text-body">
          {children}
        </div>
      )}
    </div>
  )
}

/**
 * EmptyState Component
 *
 * Empty state for right column when nothing is selected
 */

interface EmptyStateProps {
  icon?: ReactNode
  title: string
  description: string
  action?: ReactNode
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <div className="text-center max-w-md">
        {icon && (
          <div className="flex justify-center mb-4 text-ui-supportText">
            {icon}
          </div>
        )}
        <h3 className="text-lg font-medium text-ui-headingDark mb-2">
          {title}
        </h3>
        <p className="text-support text-ui-supportText mb-4">
          {description}
        </p>
        {action && (
          <div className="flex justify-center">
            {action}
          </div>
        )}
      </div>
    </div>
  )
}
