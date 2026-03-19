'use client'

import { useCallback, useState } from 'react'

interface PresentShareToolbarProps {
  onDownloadPDF: () => void
  onScreenshot: () => void
  contentRef?: React.RefObject<HTMLDivElement | null>
}

export function PresentShareToolbar({
  onDownloadPDF,
  onScreenshot,
  contentRef,
}: PresentShareToolbarProps) {
  const [screenshotting, setScreenshotting] = useState(false)

  const handleScreenshot = useCallback(async () => {
    setScreenshotting(true)
    try {
      const html2canvas = (await import('html2canvas')).default
      const target =
        contentRef?.current ?? document.querySelector<HTMLDivElement>('[data-present-content]')
      if (!target) return

      const canvas = await html2canvas(target, {
        backgroundColor: '#0A1E2F',
        scale: 2,
        useCORS: true,
      })

      const link = document.createElement('a')
      link.download = `slide-${Date.now()}.png`
      link.href = canvas.toDataURL('image/png')
      link.click()
    } catch {
      // Silently fail — user can retry
    } finally {
      setScreenshotting(false)
    }
  }, [contentRef])

  return (
    <div className="flex items-center gap-1.5 print:hidden">
      {/* Download PDF */}
      <ToolbarButton tooltip="Download PDF" onClick={onDownloadPDF}>
        <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
          <path
            d="M3.5 1.5h5l3 3v8a1 1 0 01-1 1h-7a1 1 0 01-1-1v-10a1 1 0 011-1z"
            stroke="currentColor"
            strokeWidth="1.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="M8.5 1.5v3h3M7.5 7v4M5.5 9l2 2 2-2"
            stroke="currentColor"
            strokeWidth="1.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </ToolbarButton>

      {/* Screenshot */}
      <ToolbarButton
        tooltip="Screenshot current slide"
        onClick={handleScreenshot}
        disabled={screenshotting}
      >
        <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
          <rect
            x="1.5"
            y="3.5"
            width="12"
            height="9"
            rx="1.5"
            stroke="currentColor"
            strokeWidth="1.2"
          />
          <circle cx="7.5" cy="8" r="2.25" stroke="currentColor" strokeWidth="1.2" />
          <path d="M5 3.5V2.5a1 1 0 011-1h3a1 1 0 011 1v1" stroke="currentColor" strokeWidth="1.2" />
        </svg>
      </ToolbarButton>
    </div>
  )
}

/* ── Button primitive ── */

function ToolbarButton({
  tooltip,
  onClick,
  disabled,
  children,
}: {
  tooltip: string
  onClick: () => void
  disabled?: boolean
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={tooltip}
      className="print:hidden cursor-pointer transition-colors disabled:opacity-40 disabled:cursor-default"
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: 32,
        height: 32,
        borderRadius: 16,
        border: '1px solid rgba(255,255,255,0.10)',
        background: 'rgba(255,255,255,0.06)',
        color: 'rgba(255,255,255,0.5)',
      }}
      onMouseEnter={e => {
        if (!e.currentTarget.disabled) {
          e.currentTarget.style.background = 'rgba(255,255,255,0.12)'
          e.currentTarget.style.color = '#FFFFFF'
        }
      }}
      onMouseLeave={e => {
        e.currentTarget.style.background = 'rgba(255,255,255,0.06)'
        e.currentTarget.style.color = 'rgba(255,255,255,0.5)'
      }}
    >
      {children}
    </button>
  )
}
