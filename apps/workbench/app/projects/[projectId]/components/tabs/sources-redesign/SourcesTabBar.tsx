/**
 * SourcesTabBar Component
 *
 * Tab navigation for the Sources tab sub-tabs.
 * Supports Documents, Signals, Research, Intelligence, and Memory tabs.
 */

'use client'

import {
  FileText,
  Signal,
  Globe,
  Sparkles,
  BookOpen,
  type LucideIcon,
} from 'lucide-react'

export type SourcesSubTab = 'documents' | 'signals' | 'research' | 'intelligence' | 'memory'

interface TabConfig {
  id: SourcesSubTab
  label: string
  icon: LucideIcon
}

const TABS: TabConfig[] = [
  { id: 'signals', label: 'Signals', icon: Signal },
  { id: 'documents', label: 'Documents', icon: FileText },
  { id: 'research', label: 'Research', icon: Globe },
  { id: 'intelligence', label: 'Intelligence', icon: Sparkles },
  { id: 'memory', label: 'Memory', icon: BookOpen },
]

interface SourcesTabBarProps {
  /** Currently active tab */
  activeTab: SourcesSubTab
  /** Tab change handler */
  onTabChange: (tab: SourcesSubTab) => void
  /** Optional counts for each tab */
  counts?: Partial<Record<SourcesSubTab, number>>
}

export function SourcesTabBar({ activeTab, onTabChange, counts = {} }: SourcesTabBarProps) {
  return (
    <div className="border-b border-gray-200">
      <nav className="-mb-px flex space-x-6" aria-label="Sources tabs">
        {TABS.map((tab) => {
          const isActive = activeTab === tab.id
          const count = counts[tab.id]

          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`
                flex items-center gap-2 py-3 px-1 border-b-2 text-sm font-medium transition-colors
                ${isActive
                  ? 'border-brand-primary text-brand-primary'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }
              `}
            >
              <tab.icon className="w-4 h-4" />
              <span>{tab.label}</span>
              {count !== undefined && count > 0 && (
                <span
                  className={`
                    px-2 py-0.5 rounded-full text-xs font-semibold
                    ${isActive
                      ? 'bg-emerald-50 text-brand-primary'
                      : 'bg-gray-100 text-gray-600'
                    }
                  `}
                >
                  {count}
                </span>
              )}
            </button>
          )
        })}
      </nav>
    </div>
  )
}
