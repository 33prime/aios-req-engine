/**
 * TabNavigation Component
 *
 * 6-tab navigation for the main workspace:
 * 1. Overview
 * 2. Strategic Context
 * 3. Personas & Features
 * 4. Value Path
 * 5. Research
 * 6. Next Steps
 *
 * Usage:
 *   <TabNavigation activeTab={activeTab} onTabChange={setActiveTab} />
 */

'use client'

import React from 'react'
import { Compass, Zap, CheckSquare, LayoutDashboard, Search, Users, Target } from 'lucide-react'

export type TabType = 'overview' | 'strategic-foundation' | 'personas-features' | 'value-path' | 'sources' | 'next-steps'

interface Tab {
  id: TabType
  label: string
  icon: React.ComponentType<{ className?: string }>
  description: string
}

const tabs: Tab[] = [
  {
    id: 'overview',
    label: 'Overview',
    icon: LayoutDashboard,
    description: 'Project health and proposals'
  },
  {
    id: 'strategic-foundation',
    label: 'Strategic Foundation',
    icon: Compass,
    description: 'Company, drivers, and references'
  },
  {
    id: 'personas-features',
    label: 'Personas & Features',
    icon: Users,
    description: 'User personas and product features'
  },
  {
    id: 'value-path',
    label: 'Value Path',
    icon: Zap,
    description: 'Step-by-step user journey'
  },
  {
    id: 'sources',
    label: 'Sources',
    icon: Search,
    description: 'Signals and original materials'
  },
  {
    id: 'next-steps',
    label: 'Next Steps',
    icon: CheckSquare,
    description: 'Confirmations and action items'
  }
]

interface TabNavigationProps {
  activeTab: TabType
  onTabChange: (tab: TabType) => void
  counts?: {
    strategicContext?: number
    valuePath?: number
    nextSteps?: number
    sources?: number
  }
  recentChanges?: {
    strategicContext?: number
    valuePath?: number
  }
}

export function TabNavigation({ activeTab, onTabChange, counts, recentChanges }: TabNavigationProps) {
  return (
    <div className="border-b border-gray-200 bg-white">
      <nav className="flex space-x-1 px-6" aria-label="Tabs">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id
          const Icon = tab.icon

          // Get count for this tab
          let count: number | undefined
          if (tab.id === 'strategic-foundation') count = counts?.strategicContext
          if (tab.id === 'value-path') count = counts?.valuePath
          if (tab.id === 'next-steps') count = counts?.nextSteps
          if (tab.id === 'sources') count = counts?.sources

          // Get recent changes for this tab
          let recentCount: number | undefined
          if (tab.id === 'strategic-foundation') recentCount = recentChanges?.strategicContext
          if (tab.id === 'value-path') recentCount = recentChanges?.valuePath

          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`
                group relative px-4 py-4 flex items-center gap-2 font-medium text-sm
                transition-all duration-200 border-b-2
                ${isActive
                  ? 'border-[#009b87] text-[#009b87]'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }
              `}
              aria-current={isActive ? 'page' : undefined}
            >
              <Icon className={`h-4 w-4 ${isActive ? 'text-[#009b87]' : 'text-gray-400 group-hover:text-gray-600'}`} />
              <span>{tab.label}</span>
              {count !== undefined && count > 0 && (
                <span
                  className={`
                    inline-flex items-center justify-center px-2 py-0.5 rounded-full text-xs font-semibold
                    ${isActive
                      ? 'bg-emerald-100 text-emerald-700'
                      : 'bg-gray-100 text-gray-600'
                    }
                  `}
                >
                  {count}
                </span>
              )}
              {recentCount !== undefined && recentCount > 0 && (
                <span className="ml-1 inline-flex items-center justify-center px-1.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500 text-white">
                  {recentCount}
                </span>
              )}

              {/* Tooltip on hover (desktop only) */}
              <div className="hidden lg:block absolute top-full left-1/2 -translate-x-1/2 mt-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                <div className="bg-gray-900 text-white text-xs rounded px-2 py-1 whitespace-nowrap">
                  {tab.description}
                  <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-2 h-2 bg-gray-900 rotate-45"></div>
                </div>
              </div>
            </button>
          )
        })}
      </nav>
    </div>
  )
}

/**
 * MobileTabNavigation Component
 *
 * Dropdown-style navigation for mobile screens
 */

interface MobileTabNavigationProps {
  activeTab: TabType
  onTabChange: (tab: TabType) => void
}

export function MobileTabNavigation({ activeTab, onTabChange }: MobileTabNavigationProps) {
  const activeTabData = tabs.find(t => t.id === activeTab)
  const [isOpen, setIsOpen] = React.useState(false)

  return (
    <div className="relative lg:hidden border-b border-gray-200 bg-white">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-4 py-3 flex items-center justify-between text-left"
      >
        <div className="flex items-center gap-2">
          {activeTabData && (
            <>
              <activeTabData.icon className="h-4 w-4 text-[#009b87]" />
              <span className="font-medium text-gray-900">{activeTabData.label}</span>
            </>
          )}
        </div>
        <svg
          className={`h-5 w-5 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/20 z-40"
            onClick={() => setIsOpen(false)}
          />

          {/* Dropdown menu */}
          <div className="absolute top-full left-0 right-0 bg-white border-b border-gray-200 shadow-lg z-50">
            {tabs.map((tab) => {
              const Icon = tab.icon
              const isActive = activeTab === tab.id

              return (
                <button
                  key={tab.id}
                  onClick={() => {
                    onTabChange(tab.id)
                    setIsOpen(false)
                  }}
                  className={`
                    w-full px-4 py-3 flex items-center gap-3 text-left transition-colors
                    ${isActive
                      ? 'bg-emerald-50 text-[#009b87]'
                      : 'text-gray-700 hover:bg-gray-50'
                    }
                  `}
                >
                  <Icon className="h-4 w-4" />
                  <div className="flex-1">
                    <div className="font-medium">{tab.label}</div>
                    <div className="text-xs text-gray-500">{tab.description}</div>
                  </div>
                  {isActive && (
                    <svg className="h-5 w-5 text-[#009b87]" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  )}
                </button>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
