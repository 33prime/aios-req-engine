/**
 * SendConfirmModal - Confirmation dialog before sending prep to portal
 */

'use client'

import { useState } from 'react'
import { AlertTriangle, Loader2, Send } from 'lucide-react'
import { Modal } from '@/components/ui/Modal'
import { sendDiscoveryPrepToPortal } from '@/lib/api'

interface SendConfirmModalProps {
  projectId: string
  isOpen: boolean
  onClose: () => void
  onRefresh?: () => void
  questionCount: number
  documentCount: number
}

export function SendConfirmModal({
  projectId,
  isOpen,
  onClose,
  onRefresh,
  questionCount,
  documentCount,
}: SendConfirmModalProps) {
  const [sending, setSending] = useState(false)

  const handleSend = async () => {
    try {
      setSending(true)
      await sendDiscoveryPrepToPortal(projectId)
      onRefresh?.()
      onClose()
    } finally {
      setSending(false)
    }
  }

  const footer = (
    <>
      <button
        onClick={onClose}
        disabled={sending}
        className="px-4 py-2 text-sm text-text-body border border-border rounded-lg hover:bg-surface-muted transition-colors disabled:opacity-50"
      >
        Cancel
      </button>
      <button
        onClick={handleSend}
        disabled={sending}
        className="flex items-center gap-1.5 px-4 py-2 bg-brand-primary text-white text-sm font-medium rounded-lg hover:bg-[#25785A] disabled:opacity-50 transition-colors"
      >
        {sending ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Send className="h-4 w-4" />
        )}
        {sending ? 'Sending...' : 'Send Now'}
      </button>
    </>
  )

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Send to Client Portal?" size="sm" footer={footer}>
      <div className="text-center py-2">
        <div className="mx-auto w-12 h-12 rounded-full bg-amber-100 flex items-center justify-center mb-4">
          <AlertTriangle className="h-6 w-6 text-amber-600" />
        </div>
        <p className="text-sm text-text-body">
          This will send <strong>{questionCount}</strong> confirmed question{questionCount !== 1 ? 's' : ''}
          {documentCount > 0 && (
            <> and <strong>{documentCount}</strong> document request{documentCount !== 1 ? 's' : ''}</>
          )}
          {' '}to the client portal.
        </p>
        <p className="text-xs text-text-placeholder mt-2">
          Clients with portal access will be able to see and respond.
        </p>
      </div>
    </Modal>
  )
}
