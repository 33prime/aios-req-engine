/**
 * Button Component
 *
 * Reusable button with 3 variants: primary, secondary, outline
 * Based on the design system tokens.
 *
 * Usage:
 *   <Button onClick={handleClick}>Click me</Button>
 *   <Button variant="secondary">Secondary</Button>
 *   <Button variant="outline" disabled>Disabled</Button>
 *   <Button loading>Processing...</Button>
 */

import React, { ButtonHTMLAttributes, ReactNode } from 'react'
import type { ButtonVariant } from '@/lib/design-tokens'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  loading?: boolean
  icon?: ReactNode
  children: ReactNode
  fullWidth?: boolean
  size?: 'sm' | 'md' | 'lg'
}

export function Button({
  variant = 'primary',
  loading = false,
  icon,
  children,
  fullWidth = false,
  size = 'md',
  className = '',
  disabled,
  ...props
}: ButtonProps) {
  const sizeClasses = {
    sm: 'px-3 py-1.5 text-sm gap-1.5',
    md: 'px-4 py-2 gap-2',
    lg: 'px-5 py-2.5 text-lg gap-2.5'
  }
  const baseClasses = `rounded-lg font-medium transition-all duration-200 inline-flex items-center justify-center ${sizeClasses[size]}`

  const variantClasses = {
    primary: 'bg-[#3FAF7A] text-white hover:bg-[#033344] active:bg-[#022836]',
    secondary: 'bg-[#F5F5F5] text-[#333333] hover:bg-[#E5E5E5] active:bg-[#D4D4D4]',
    outline: 'bg-white border border-[#3FAF7A] text-[#3FAF7A] hover:bg-[#3FAF7A]/5 active:bg-[#3FAF7A]/10',
    ghost: 'bg-transparent text-[#333333] hover:bg-gray-100 active:bg-gray-200'
  }

  const disabledClasses = 'opacity-50 cursor-not-allowed'
  const loadingClasses = 'cursor-wait'
  const widthClasses = fullWidth ? 'w-full' : ''

  const isDisabled = disabled || loading

  return (
    <button
      className={`
        ${baseClasses}
        ${variantClasses[variant]}
        ${isDisabled ? disabledClasses : ''}
        ${loading ? loadingClasses : ''}
        ${widthClasses}
        ${className}
      `}
      disabled={isDisabled}
      {...props}
    >
      {loading && (
        <svg
          className="animate-spin h-4 w-4"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      )}
      {!loading && icon && <span className="inline-flex">{icon}</span>}
      {children}
    </button>
  )
}

/**
 * IconButton Component
 *
 * Button with only an icon (no text)
 */

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon: ReactNode
  label: string // For accessibility
  variant?: ButtonVariant
  size?: 'sm' | 'md' | 'lg'
}

export function IconButton({
  icon,
  label,
  variant = 'secondary',
  size = 'md',
  className = '',
  ...props
}: IconButtonProps) {
  const sizeClasses = {
    sm: 'p-1.5',
    md: 'p-2',
    lg: 'p-3'
  }

  const variantClasses = {
    primary: 'bg-[#3FAF7A] text-white hover:bg-[#033344]',
    secondary: 'bg-[#F5F5F5] text-[#333333] hover:bg-[#E5E5E5]',
    outline: 'bg-white border border-[#3FAF7A] text-[#3FAF7A] hover:bg-[#3FAF7A]/5',
    ghost: 'bg-transparent text-[#333333] hover:bg-gray-100 active:bg-gray-200'
  }

  return (
    <button
      className={`
        rounded-lg transition-all duration-200 inline-flex items-center justify-center
        ${sizeClasses[size]}
        ${variantClasses[variant]}
        ${className}
      `}
      aria-label={label}
      title={label}
      {...props}
    >
      {icon}
    </button>
  )
}

/**
 * ButtonGroup Component
 *
 * Group multiple buttons together
 */

interface ButtonGroupProps {
  children: ReactNode
  className?: string
}

export function ButtonGroup({ children, className = '' }: ButtonGroupProps) {
  return (
    <div className={`inline-flex gap-2 ${className}`}>
      {children}
    </div>
  )
}
