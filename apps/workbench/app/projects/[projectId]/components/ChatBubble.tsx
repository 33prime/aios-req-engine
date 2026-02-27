/**
 * ChatBubble Component
 *
 * Floating action button that opens the chat assistant panel.
 * Always visible in bottom-right corner of the screen.
 *
 * Features:
 * - Notification badge for new messages
 * - Smooth animations
 * - Click to toggle chat panel
 * - Visual feedback on hover
 */

'use client'

import { MessageCircle, X } from 'lucide-react'
import { useState, useEffect } from 'react'

interface ChatBubbleProps {
  /** Whether the chat panel is currently open */
  isOpen: boolean
  /** Callback when the bubble is clicked */
  onToggle: () => void
  /** Number of unread messages (optional) */
  unreadCount?: number
}

export function ChatBubble({ isOpen, onToggle, unreadCount = 0 }: ChatBubbleProps) {
  const [isAnimating, setIsAnimating] = useState(false)

  // Trigger animation on mount
  useEffect(() => {
    setIsAnimating(true)
  }, [])

  return (
    <div className="fixed bottom-4 right-4 sm:bottom-6 sm:right-6 z-50">
      {/* Floating Action Button */}
      <button
        onClick={onToggle}
        className={`
          relative
          flex items-center justify-center
          w-14 h-14
          bg-brand-primary hover:bg-[#25785A]
          text-white
          rounded-full
          shadow-lg hover:shadow-xl
          transition-all duration-300 ease-in-out
          ${isAnimating ? 'scale-100 opacity-100' : 'scale-0 opacity-0'}
          ${isOpen ? 'rotate-0' : 'rotate-0'}
        `}
        aria-label={isOpen ? 'Close chat' : 'Open chat assistant'}
      >
        {/* Icon with rotation animation */}
        <div className={`transition-transform duration-300 ${isOpen ? 'rotate-90' : 'rotate-0'}`}>
          {isOpen ? (
            <X className="h-6 w-6" />
          ) : (
            <MessageCircle className="h-6 w-6" />
          )}
        </div>

        {/* Unread Badge */}
        {!isOpen && unreadCount > 0 && (
          <div className="absolute -top-1 -right-1 flex items-center justify-center w-5 h-5 bg-red-500 text-white text-xs font-bold rounded-full animate-pulse">
            {unreadCount > 9 ? '9+' : unreadCount}
          </div>
        )}

        {/* Pulse Animation Ring (when closed) */}
        {!isOpen && (
          <div className="absolute inset-0 rounded-full bg-brand-primary animate-ping opacity-20" />
        )}
      </button>

      {/* Tooltip (when closed) */}
      {!isOpen && (
        <div className="absolute bottom-full right-0 mb-2 px-3 py-1.5 bg-gray-900 text-white text-sm rounded-lg opacity-0 hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap">
          Chat with AI Assistant
          <div className="absolute top-full right-6 -mt-1 border-4 border-transparent border-t-gray-900" />
        </div>
      )}
    </div>
  )
}
