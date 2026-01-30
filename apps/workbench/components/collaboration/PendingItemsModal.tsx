/**
 * PendingItemsModal - Modal wrapper around PendingQueue
 *
 * Opens from the "Pending" stat pill in CollaborationHub.
 * Fetches fresh pending items and renders PendingQueue inside a Modal.
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import { Loader2 } from 'lucide-react'
import { Modal } from '@/components/ui/Modal'
import { PendingQueue } from './PendingQueue'
import { listPendingItems, generateClientPackage, removePendingItem } from '@/lib/api'
import type { PendingItemsQueue } from '@/types/api'

interface PendingItemsModalProps {
  projectId: string
  isOpen: boolean
  onClose: () => void
  onRefresh?: () => void
}

export function PendingItemsModal({
  projectId,
  isOpen,
  onClose,
  onRefresh,
}: PendingItemsModalProps) {
  const [queue, setQueue] = useState<PendingItemsQueue | null>(null)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      const data = await listPendingItems(projectId)
      // Build queue shape from API response
      const items = data.items || []
      const byType: Record<string, number> = {}
      for (const item of items) {
        byType[item.item_type] = (byType[item.item_type] || 0) + 1
      }
      setQueue({ items, by_type: byType, total_count: items.length })
    } catch {
      setQueue({ items: [], by_type: {}, total_count: 0 })
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    if (isOpen) {
      loadData()
    }
  }, [isOpen, loadData])

  const handleGeneratePackage = async (itemIds?: string[]) => {
    try {
      setGenerating(true)
      await generateClientPackage(projectId, { item_ids: itemIds })
      onRefresh?.()
      onClose()
    } finally {
      setGenerating(false)
    }
  }

  const handleRemoveItem = async (itemId: string) => {
    try {
      await removePendingItem(itemId)
      await loadData()
    } catch {
      // silently fail
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Pending Items" size="lg">
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 text-brand-teal animate-spin" />
        </div>
      ) : queue && queue.total_count === 0 ? (
        <div className="text-center py-12">
          <p className="text-ui-bodyText font-medium mb-1">All caught up</p>
          <p className="text-sm text-ui-supportText">No items need confirmation right now.</p>
        </div>
      ) : queue ? (
        <PendingQueue
          queue={queue}
          onGeneratePackage={handleGeneratePackage}
          onRemoveItem={handleRemoveItem}
          isGenerating={generating}
        />
      ) : null}
    </Modal>
  )
}
