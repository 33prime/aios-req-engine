'use client'

import { useEffect, useCallback, useRef } from 'react'

interface PresentModeShellProps {
  isOpen: boolean
  onClose: () => void
  totalSlides: number
  currentSlide: number
  onNavigate: (direction: 1 | -1) => void
  counterLabel: string
  children: React.ReactNode
  variant?: 'walkthrough' | 'onepager'
  toolbar?: React.ReactNode
}

export function PresentModeShell({
  isOpen,
  onClose,
  totalSlides,
  currentSlide,
  onNavigate,
  counterLabel,
  children,
  variant = 'walkthrough',
  toolbar,
}: PresentModeShellProps) {
  const contentRef = useRef<HTMLDivElement>(null)

  const handleKey = useCallback(
    (e: KeyboardEvent) => {
      if (!isOpen) return
      if (e.key === 'Escape') onClose()
      if (variant === 'onepager') return // no slide nav in onepager
      if (e.key === 'ArrowRight' || e.key === ' ') {
        e.preventDefault()
        if (currentSlide < totalSlides - 1) onNavigate(1)
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault()
        if (currentSlide > 0) onNavigate(-1)
      }
    },
    [isOpen, onClose, onNavigate, currentSlide, totalSlides, variant]
  )

  useEffect(() => {
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [handleKey])

  if (!isOpen) return null

  // One-Pager: light scrollable document
  if (variant === 'onepager') {
    return (
      <div className="fixed inset-0 z-[1000] flex flex-col" style={{ background: '#FFFFFF' }}>
        {/* Sticky header */}
        <div
          className="flex items-center justify-between px-8 py-3 flex-shrink-0 print:hidden"
          style={{ borderBottom: '1px solid #E2E8F0' }}
        >
          <span className="text-xs font-medium" style={{ color: '#718096' }}>
            {counterLabel}
          </span>
          <div className="flex items-center gap-2">
            {toolbar}
            <button
              onClick={onClose}
              className="px-3.5 py-1.5 rounded-lg text-xs cursor-pointer transition-colors"
              style={{ border: '1px solid #E2E8F0', color: '#718096' }}
              onMouseEnter={e => { e.currentTarget.style.background = '#F7FAFC'; e.currentTarget.style.color = '#0A1E2F' }}
              onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#718096' }}
            >
              ESC &middot; Close
            </button>
          </div>
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto" ref={contentRef} data-present-content>
          <div className="max-w-[900px] w-full mx-auto px-8 py-8">
            {children}
          </div>
        </div>

        <style jsx>{`
          @media print {
            .print\\:hidden { display: none !important; }
          }
        `}</style>
      </div>
    )
  }

  // Walkthrough: dark fullscreen slides
  return (
    <div className="fixed inset-0 z-[1000] flex flex-col" style={{ background: '#0A1E2F' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-12 py-4 flex-shrink-0">
        <span className="text-xs font-medium" style={{ color: 'rgba(255,255,255,0.35)' }}>
          {counterLabel}
        </span>
        <div className="flex items-center gap-2">
          {toolbar}
          <button
            onClick={onClose}
            className="px-3.5 py-1.5 rounded-lg text-xs cursor-pointer transition-colors"
            style={{
              border: '1px solid rgba(255,255,255,0.12)',
              background: 'transparent',
              color: 'rgba(255,255,255,0.45)',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = 'rgba(255,255,255,0.04)'
              e.currentTarget.style.color = '#fff'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = 'transparent'
              e.currentTarget.style.color = 'rgba(255,255,255,0.45)'
            }}
          >
            ESC &middot; Exit
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 flex items-center justify-center px-20 pb-9 overflow-y-auto">
        <div
          ref={contentRef}
          data-present-content
          className="max-w-[820px] w-full animate-in fade-in slide-in-from-bottom-4 duration-450"
        >
          {children}
        </div>
      </div>

      {/* Navigation */}
      <div className="flex justify-center items-center gap-3.5 pb-6 flex-shrink-0">
        <button
          onClick={() => onNavigate(-1)}
          disabled={currentSlide === 0}
          className="px-5 py-1.5 rounded-lg text-xs font-medium cursor-pointer transition-colors disabled:opacity-25 disabled:cursor-default"
          style={{
            border: '1px solid rgba(255,255,255,0.1)',
            background: 'transparent',
            color: 'rgba(255,255,255,0.45)',
          }}
          onMouseEnter={e => {
            if (!e.currentTarget.disabled) {
              e.currentTarget.style.background = 'rgba(255,255,255,0.04)'
              e.currentTarget.style.color = '#fff'
            }
          }}
          onMouseLeave={e => {
            e.currentTarget.style.background = 'transparent'
            e.currentTarget.style.color = 'rgba(255,255,255,0.45)'
          }}
        >
          &larr; Previous
        </button>

        {/* Dots — collapse to scrollable when many slides */}
        <div className="flex items-center gap-1 max-w-[300px] overflow-hidden">
          {Array.from({ length: totalSlides }).map((_, i) => (
            <div
              key={i}
              className="rounded-full transition-all duration-300 flex-shrink-0"
              style={{
                width: i === currentSlide ? 18 : 6,
                height: 6,
                borderRadius: i === currentSlide ? 3 : '50%',
                background: i === currentSlide ? '#3FAF7A' : 'rgba(255,255,255,0.1)',
              }}
            />
          ))}
        </div>

        <button
          onClick={() => onNavigate(1)}
          disabled={currentSlide >= totalSlides - 1}
          className="px-5 py-1.5 rounded-lg text-xs font-medium cursor-pointer transition-colors disabled:opacity-25 disabled:cursor-default"
          style={{
            border: '1px solid rgba(255,255,255,0.1)',
            background: 'transparent',
            color: 'rgba(255,255,255,0.45)',
          }}
          onMouseEnter={e => {
            if (!e.currentTarget.disabled) {
              e.currentTarget.style.background = 'rgba(255,255,255,0.04)'
              e.currentTarget.style.color = '#fff'
            }
          }}
          onMouseLeave={e => {
            e.currentTarget.style.background = 'transparent'
            e.currentTarget.style.color = 'rgba(255,255,255,0.45)'
          }}
        >
          Next &rarr;
        </button>
      </div>
    </div>
  )
}
