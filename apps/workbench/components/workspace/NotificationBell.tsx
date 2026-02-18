'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { Bell } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { formatDistanceToNow } from 'date-fns'
import {
  getUnreadNotificationCount,
  listNotifications,
  markNotificationRead,
  markAllNotificationsRead,
} from '@/lib/api'
import type { Notification } from '@/types/api'

const POLL_INTERVAL = 30000 // 30 seconds

export function NotificationBell() {
  const [unreadCount, setUnreadCount] = useState(0)
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [isOpen, setIsOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const panelRef = useRef<HTMLDivElement>(null)
  const router = useRouter()

  // Poll unread count
  useEffect(() => {
    let active = true

    const fetchCount = async () => {
      try {
        const data = await getUnreadNotificationCount()
        if (active) setUnreadCount(data.count)
      } catch {
        // Silently fail — non-critical
      }
    }

    fetchCount()
    const interval = setInterval(fetchCount, POLL_INTERVAL)
    return () => {
      active = false
      clearInterval(interval)
    }
  }, [])

  // Load notifications when panel opens
  const loadNotifications = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listNotifications(false, 10)
      setNotifications(data)
    } catch {
      // Silently fail
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (isOpen) loadNotifications()
  }, [isOpen, loadNotifications])

  // Close on click outside
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    if (isOpen) document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [isOpen])

  const handleNotificationClick = async (notif: Notification) => {
    if (!notif.read) {
      await markNotificationRead(notif.id)
      setUnreadCount((c) => Math.max(0, c - 1))
      setNotifications((prev) =>
        prev.map((n) => (n.id === notif.id ? { ...n, read: true } : n))
      )
    }
    if (notif.project_id) {
      router.push(`/projects/${notif.project_id}`)
    }
    setIsOpen(false)
  }

  const handleMarkAllRead = async () => {
    await markAllNotificationsRead()
    setUnreadCount(0)
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })))
  }

  return (
    <div className="relative" ref={panelRef}>
      {/* Bell button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-1.5 rounded-lg text-[#999999] hover:bg-[#F4F4F4] hover:text-[#333333] transition-colors"
        title="Notifications"
      >
        <Bell className="w-4 h-4" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-red-500 text-white text-[9px] font-bold rounded-full flex items-center justify-center">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown panel */}
      {isOpen && (
        <div className="absolute left-0 top-full mt-2 w-80 bg-white rounded-xl shadow-2xl border border-[#E5E5E5] z-50 overflow-hidden">
          {/* Header */}
          <div className="px-4 py-3 border-b border-[#E5E5E5]">
            <h3 className="text-sm font-semibold text-[#333333]">Notifications</h3>
          </div>

          {/* Notification list */}
          <div className="max-h-80 overflow-y-auto">
            {loading && (
              <div className="px-4 py-6 text-center text-sm text-[#999999]">
                Loading...
              </div>
            )}

            {!loading && notifications.length === 0 && (
              <div className="px-4 py-6 text-center text-sm text-[#999999]">
                No notifications yet
              </div>
            )}

            {!loading &&
              notifications.map((notif) => (
                <button
                  key={notif.id}
                  onClick={() => handleNotificationClick(notif)}
                  className="w-full text-left px-4 py-3 hover:bg-[#F4F4F4] transition-colors border-b border-[#F0F0F0] last:border-b-0"
                >
                  <div className="flex items-start gap-2.5">
                    <div
                      className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${
                        notif.read ? 'bg-transparent' : 'bg-[#3FAF7A]'
                      }`}
                    />
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm leading-snug ${
                        notif.read ? 'text-[#666666]' : 'text-[#333333] font-medium'
                      }`}>
                        {notif.title}
                      </p>
                      {notif.body && (
                        <p className="text-xs text-[#999999] mt-0.5 line-clamp-2">
                          {notif.body}
                        </p>
                      )}
                      <p className="text-[10px] text-[#BBBBBB] mt-1">
                        {formatDistanceToNow(new Date(notif.created_at), { addSuffix: true })}
                      </p>
                    </div>
                  </div>
                </button>
              ))}
          </div>

          {/* Footer */}
          {notifications.length > 0 && unreadCount > 0 && (
            <div className="border-t border-[#E5E5E5] px-4 py-2.5">
              <button
                onClick={handleMarkAllRead}
                className="text-xs text-[#3FAF7A] hover:text-[#25785A] font-medium"
              >
                Mark all as read
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
