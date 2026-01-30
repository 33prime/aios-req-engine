/**
 * BuildPhaseView - Prototype embed and build tracking
 *
 * Shows the deployed prototype URL as an iframe with controls.
 * Also shows build progress and validation status.
 */

'use client'

import { useState, useRef, useEffect } from 'react'
import {
  ExternalLink,
  RefreshCw,
  Maximize2,
  Minimize2,
  Edit3,
  Check,
  X,
  Link as LinkIcon,
  AlertCircle,
} from 'lucide-react'

interface BuildPhaseViewProps {
  projectId: string
  prototypeUrl?: string | null
  prototypeUpdatedAt?: string | null
  readinessScore: number
  onUpdatePrototypeUrl: (url: string) => Promise<void>
}

export function BuildPhaseView({
  projectId,
  prototypeUrl,
  prototypeUpdatedAt,
  readinessScore,
  onUpdatePrototypeUrl,
}: BuildPhaseViewProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [urlValue, setUrlValue] = useState(prototypeUrl || '')
  const [isSaving, setIsSaving] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [iframeKey, setIframeKey] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    setUrlValue(prototypeUrl || '')
  }, [prototypeUrl])

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [isEditing])

  const handleSave = async () => {
    if (!urlValue.trim()) {
      setIsEditing(false)
      return
    }

    // Add https:// if missing
    let normalizedUrl = urlValue.trim()
    if (!/^https?:\/\//i.test(normalizedUrl)) {
      normalizedUrl = `https://${normalizedUrl}`
      setUrlValue(normalizedUrl)
    }

    setIsSaving(true)
    try {
      await onUpdatePrototypeUrl(normalizedUrl)
      setIsEditing(false)
    } catch (error) {
      console.error('Failed to save prototype URL:', error)
    } finally {
      setIsSaving(false)
    }
  }

  const handleCancel = () => {
    setUrlValue(prototypeUrl || '')
    setIsEditing(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSave()
    } else if (e.key === 'Escape') {
      handleCancel()
    }
  }

  const refreshIframe = () => {
    setIframeKey((k) => k + 1)
  }

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return null
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    })
  }

  return (
    <div className={`h-full flex flex-col ${isFullscreen ? 'fixed inset-0 z-50 bg-white' : ''}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-ui-cardBorder bg-white">
        <div className="flex items-center gap-4">
          <h2 className="text-section text-ui-headingDark">Prototype</h2>

          {/* Readiness Badge */}
          <div className="flex items-center gap-2">
            <div className="w-20 h-1.5 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-brand-teal rounded-full transition-all"
                style={{ width: `${readinessScore}%` }}
              />
            </div>
            <span className="text-sm font-medium text-ui-bodyText">
              {Math.round(readinessScore)}% ready
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {prototypeUrl && (
            <>
              <button
                onClick={refreshIframe}
                className="p-2 text-ui-supportText hover:text-ui-headingDark hover:bg-ui-background rounded-lg transition-colors"
                title="Refresh preview"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
              <a
                href={prototypeUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="p-2 text-ui-supportText hover:text-ui-headingDark hover:bg-ui-background rounded-lg transition-colors"
                title="Open in new tab"
              >
                <ExternalLink className="w-4 h-4" />
              </a>
              <button
                onClick={() => setIsFullscreen(!isFullscreen)}
                className="p-2 text-ui-supportText hover:text-ui-headingDark hover:bg-ui-background rounded-lg transition-colors"
                title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
              >
                {isFullscreen ? (
                  <Minimize2 className="w-4 h-4" />
                ) : (
                  <Maximize2 className="w-4 h-4" />
                )}
              </button>
            </>
          )}
        </div>
      </div>

      {/* URL Bar */}
      <div className="px-4 py-2 bg-ui-background border-b border-ui-cardBorder">
        {isEditing ? (
          <div className="flex items-center gap-2">
            <LinkIcon className="w-4 h-4 text-ui-supportText flex-shrink-0" />
            <input
              ref={inputRef}
              type="url"
              value={urlValue}
              onChange={(e) => setUrlValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="https://your-prototype.vercel.app"
              className="flex-1 px-3 py-1.5 text-sm bg-white border border-ui-cardBorder rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-teal/20 focus:border-brand-teal"
              disabled={isSaving}
            />
            <button
              onClick={handleCancel}
              className="p-1.5 text-ui-supportText hover:text-ui-bodyText rounded transition-colors"
              disabled={isSaving}
            >
              <X className="w-4 h-4" />
            </button>
            <button
              onClick={handleSave}
              className="p-1.5 text-brand-teal hover:bg-brand-teal/10 rounded transition-colors"
              disabled={isSaving}
            >
              <Check className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <div
            onClick={() => setIsEditing(true)}
            className="flex items-center gap-2 cursor-pointer group"
          >
            <LinkIcon className="w-4 h-4 text-ui-supportText flex-shrink-0" />
            {prototypeUrl ? (
              <span className="text-sm text-ui-bodyText truncate flex-1">
                {prototypeUrl}
              </span>
            ) : (
              <span className="text-sm text-ui-supportText italic">
                Click to add prototype URL...
              </span>
            )}
            <Edit3 className="w-3.5 h-3.5 text-ui-supportText opacity-0 group-hover:opacity-100 transition-opacity" />
            {prototypeUpdatedAt && (
              <span className="text-support text-ui-supportText ml-auto">
                Updated {formatDate(prototypeUpdatedAt)}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Prototype Preview */}
      <div className="flex-1 bg-gray-100 relative">
        {prototypeUrl ? (
          <iframe
            key={iframeKey}
            src={prototypeUrl}
            className="w-full h-full border-0"
            title="Prototype Preview"
            sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
          />
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-ui-background flex items-center justify-center">
                <LinkIcon className="w-8 h-8 text-ui-supportText" />
              </div>
              <h3 className="text-section text-ui-headingDark mb-2">
                Add Your Prototype URL
              </h3>
              <p className="text-sm text-ui-supportText mb-4">
                Paste the URL of your deployed prototype (Vercel, Replit, etc.)
                to preview it directly in the workspace.
              </p>
              <button
                onClick={() => setIsEditing(true)}
                className="px-4 py-2 bg-brand-teal text-white text-sm font-medium rounded-lg hover:bg-brand-tealDark transition-colors"
              >
                Add Prototype URL
              </button>
            </div>
          </div>
        )}

        {/* X-Frame-Options Warning */}
        {prototypeUrl && (
          <div className="absolute bottom-4 left-4 right-4">
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-start gap-3 shadow-sm">
              <AlertCircle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm text-amber-800">
                  Some sites block embedding. If the preview doesn't load,{' '}
                  <a
                    href={prototypeUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="underline hover:text-amber-900"
                  >
                    open in a new tab
                  </a>
                  .
                </p>
              </div>
              <button
                onClick={(e) => {
                  const parent = e.currentTarget.parentElement
                  if (parent) parent.style.display = 'none'
                }}
                className="text-amber-500 hover:text-amber-700"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default BuildPhaseView
