'use client'

import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from 'react'
import type { AiosBridgeCommand, AiosBridgeEvent } from '@/types/prototype'

export interface PrototypeFrameHandle {
  sendMessage: (command: AiosBridgeCommand) => void
  isReady: () => boolean
}

interface PrototypeFrameProps {
  deployUrl: string
  onFeatureClick: (featureId: string, componentName: string | null) => void
  onPageChange: (path: string, visibleFeatures: string[]) => void
  onHighlightReady?: (featureId: string, rect: { top: number; left: number; width: number; height: number }) => void
  onHighlightNotFound?: (featureId: string) => void
  onTourStepComplete?: (featureId: string) => void
  onIframeReady?: () => void
}

/**
 * Iframe wrapper for the prototype with PostMessage bridge listener.
 * Tracks feature clicks and page changes via the injected bridge script.
 * Exposes imperative API via ref for sending commands to the bridge.
 */
const PrototypeFrame = forwardRef<PrototypeFrameHandle, PrototypeFrameProps>(function PrototypeFrame(
  {
    deployUrl,
    onFeatureClick,
    onPageChange,
    onHighlightReady,
    onHighlightNotFound,
    onTourStepComplete,
    onIframeReady,
  },
  ref
) {
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const [ready, setReady] = useState(false)

  useImperativeHandle(ref, () => ({
    sendMessage(command: AiosBridgeCommand) {
      iframeRef.current?.contentWindow?.postMessage(command, '*')
    },
    isReady() {
      return ready
    },
  }))

  const handleMessage = useCallback(
    (event: MessageEvent) => {
      const data = event.data as AiosBridgeEvent
      if (!data || typeof data !== 'object' || !('type' in data)) return

      switch (data.type) {
        case 'aios:feature-click':
          onFeatureClick(data.featureId, data.componentName)
          break
        case 'aios:page-change':
          if (!ready) {
            setReady(true)
            onIframeReady?.()
          }
          onPageChange(data.path, data.visibleFeatures)
          break
        case 'aios:highlight-ready':
          onHighlightReady?.(data.featureId, data.rect)
          break
        case 'aios:highlight-not-found':
          onHighlightNotFound?.(data.featureId)
          break
        case 'aios:tour-step-complete':
          onTourStepComplete?.(data.featureId)
          break
      }
    },
    [onFeatureClick, onPageChange, onHighlightReady, onHighlightNotFound, onTourStepComplete, onIframeReady, ready]
  )

  useEffect(() => {
    window.addEventListener('message', handleMessage)
    return () => window.removeEventListener('message', handleMessage)
  }, [handleMessage])

  return (
    <iframe
      ref={iframeRef}
      src={deployUrl}
      className="w-full h-full border-0"
      title="Prototype Preview"
      sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
    />
  )
})

export default PrototypeFrame
