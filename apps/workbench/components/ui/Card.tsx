/**
 * Card Component
 *
 * Reusable card container with consistent styling.
 * Supports clickable variants, hover effects, and active states.
 *
 * Usage:
 *   <Card>Content here</Card>
 *   <Card hoverable onClick={handleClick}>Clickable card</Card>
 *   <Card active>Active card</Card>
 *   <Card noPadding>Custom padding</Card>
 */

import React, { HTMLAttributes, ReactNode } from 'react'

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode
  hoverable?: boolean
  active?: boolean
  noPadding?: boolean
  className?: string
}

export function Card({
  children,
  hoverable = false,
  active = false,
  noPadding = false,
  className = '',
  onClick,
  ...props
}: CardProps) {
  const baseClasses = 'bg-white border border-ui-cardBorder rounded-card shadow-card'
  const paddingClasses = noPadding ? '' : 'p-card'
  const hoverClasses = hoverable
    ? 'hover:shadow-card-hover hover:border-brand-primary transition-all duration-200 cursor-pointer'
    : ''
  const activeClasses = active
    ? 'border-brand-primary bg-brand-primary/[0.02]'
    : ''
  const clickableClasses = onClick ? 'cursor-pointer' : ''

  return (
    <div
      className={`
        ${baseClasses}
        ${paddingClasses}
        ${hoverClasses}
        ${activeClasses}
        ${clickableClasses}
        ${className}
      `}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onClick(e as any)
        }
      } : undefined}
      {...props}
    >
      {children}
    </div>
  )
}

/**
 * CardHeader Component
 *
 * Consistent header section for cards
 */

interface CardHeaderProps {
  title: string | ReactNode
  subtitle?: string | ReactNode
  actions?: ReactNode
  className?: string
}

export function CardHeader({ title, subtitle, actions, className = '' }: CardHeaderProps) {
  return (
    <div className={`flex items-start justify-between mb-4 ${className}`}>
      <div className="flex-1">
        <h3 className="text-section text-ui-headingDark">
          {title}
        </h3>
        {subtitle && (
          <p className="text-support text-ui-supportText mt-1">
            {subtitle}
          </p>
        )}
      </div>
      {actions && (
        <div className="ml-4 flex items-center gap-2">
          {actions}
        </div>
      )}
    </div>
  )
}

/**
 * CardSection Component
 *
 * Section divider within a card
 */

interface CardSectionProps {
  title?: string
  children: ReactNode
  className?: string
}

export function CardSection({ title, children, className = '' }: CardSectionProps) {
  return (
    <div className={`${className}`}>
      {title && (
        <h4 className="text-sm font-semibold text-ui-headingDark mb-2">
          {title}
        </h4>
      )}
      {children}
    </div>
  )
}

/**
 * CardFooter Component
 *
 * Footer section with actions
 */

interface CardFooterProps {
  children: ReactNode
  className?: string
}

export function CardFooter({ children, className = '' }: CardFooterProps) {
  return (
    <div className={`mt-4 pt-4 border-t border-ui-cardBorder flex items-center gap-2 ${className}`}>
      {children}
    </div>
  )
}

/**
 * CardList Component
 *
 * Container for a list of cards (used in left column)
 */

interface CardListProps {
  children: ReactNode
  className?: string
}

export function CardList({ children, className = '' }: CardListProps) {
  return (
    <div className={`space-y-4 ${className}`}>
      {children}
    </div>
  )
}

/**
 * EmptyCard Component
 *
 * Placeholder card for empty states
 */

interface EmptyCardProps {
  icon?: ReactNode
  title: string
  description?: string
  action?: ReactNode
  className?: string
}

export function EmptyCard({ icon, title, description, action, className = '' }: EmptyCardProps) {
  return (
    <Card className={`text-center py-12 ${className}`}>
      {icon && (
        <div className="flex justify-center mb-4 text-ui-supportText">
          {icon}
        </div>
      )}
      <h3 className="text-lg font-medium text-ui-headingDark mb-2">
        {title}
      </h3>
      {description && (
        <p className="text-support text-ui-supportText mb-4">
          {description}
        </p>
      )}
      {action && (
        <div className="flex justify-center">
          {action}
        </div>
      )}
    </Card>
  )
}
