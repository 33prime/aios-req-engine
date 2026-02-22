'use client'

import { useState } from 'react'
import { X } from 'lucide-react'

export interface DrawerTab {
  id: string
  label: string
  icon: React.ComponentType<{ className?: string }>
  /** Optional badge (count, alert indicator, etc.) */
  badge?: React.ReactNode
}

interface DrawerShellProps {
  /** Called when backdrop or close button is clicked */
  onClose: () => void
  /** Icon rendered in the navy circle (pass a lucide component) */
  icon: React.ComponentType<{ className?: string }>
  /** Small uppercase label above the title (e.g. "Feature", "Pain Point") */
  entityLabel?: string
  /** Main title text */
  title: string
  /** Content rendered between the title and confirm actions (badges, subtitle, etc.) */
  headerExtra?: React.ReactNode
  /** Content rendered in the top-right area next to close button (e.g. StatusBadge) */
  headerRight?: React.ReactNode
  /** Content rendered below the header row (e.g. ConfirmActions) */
  headerActions?: React.ReactNode
  /** Tab definitions — if provided, renders a tab bar */
  tabs?: DrawerTab[]
  /** Currently active tab ID (controlled) */
  activeTab?: string
  /** Called when a tab is clicked */
  onTabChange?: (tabId: string) => void
  /** Drawer body content */
  children: React.ReactNode
}

export function DrawerShell({
  onClose,
  icon: Icon,
  entityLabel,
  title,
  headerExtra,
  headerRight,
  headerActions,
  tabs,
  activeTab,
  onTabChange,
  children,
}: DrawerShellProps) {
  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 z-40 transition-opacity"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-[560px] max-w-full bg-white shadow-xl z-50 flex flex-col animate-slide-in-right">
        {/* Header */}
        <div className="flex-shrink-0 border-b border-[#E5E5E5] px-6 py-4">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3 min-w-0 flex-1">
              <div className="w-8 h-8 rounded-full bg-[#0A1E2F] flex items-center justify-center flex-shrink-0 mt-0.5">
                <Icon className="w-4 h-4 text-white" />
              </div>
              <div className="min-w-0">
                {entityLabel && (
                  <p className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-1">
                    {entityLabel}
                  </p>
                )}
                <h2 className="text-[15px] font-semibold text-[#333333] line-clamp-2 leading-snug">
                  {title}
                </h2>
                {headerExtra}
              </div>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              {headerRight}
              <button
                onClick={onClose}
                className="p-1.5 rounded-md text-[#999999] hover:text-[#666666] hover:bg-[#F0F0F0] transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {headerActions && <div className="mt-3">{headerActions}</div>}

          {tabs && tabs.length > 0 && (
            <div className="flex gap-0 mt-4 -mb-4 border-b-0">
              {tabs.map((tab) => {
                const TabIcon = tab.icon
                const isActive = activeTab === tab.id
                return (
                  <button
                    key={tab.id}
                    onClick={() => onTabChange?.(tab.id)}
                    className={`flex items-center gap-1.5 px-3 py-2 text-[12px] font-medium border-b-2 transition-colors ${
                      isActive
                        ? 'border-[#3FAF7A] text-[#25785A]'
                        : 'border-transparent text-[#999999] hover:text-[#666666]'
                    }`}
                  >
                    <TabIcon className="w-3.5 h-3.5" />
                    {tab.label}
                    {tab.badge}
                  </button>
                )
              })}
            </div>
          )}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {children}
        </div>
      </div>
    </>
  )
}
