/**
 * TabNavigation Component
 *
 * 4-tab navigation for the main workspace:
 * 1. Product Requirements
 * 2. Value Path
 * 3. Insights
 * 4. Next Steps
 *
 * Usage:
 *   <TabNavigation activeTab={activeTab} onTabChange={setActiveTab} />
 */

'use client'

import React from 'react'
import { FileText, Zap, AlertCircle, CheckSquare } from 'lucide-react'

export type TabType = 'requirements' | 'value-path' | 'insights' | 'next-steps'

interface Tab {
  id: TabType
  label: string
  icon: React.ComponentType<{ className?: string }>
  description: string
}

const tabs: Tab[] = [
  {
    id: 'requirements',
    label: 'Product Requirements',
    icon: FileText,
    description: 'Lock the foundation quickly'
  },
  {
    id: 'value-path',
    label: 'Value Path',
    icon: Zap,
    description: 'Expand into step-level clarity'
  },
  {
    id: 'insights',
    label: 'Insights',
    icon: AlertCircle,
    description: 'Red-team the plan'
  },
  {
    id: 'next-steps',
    label: 'Next Steps',
    icon: CheckSquare,
    description: 'Batch client confirmations'
  }
]

interface TabNavigationProps {
  activeTab: TabType
  onTabChange: (tab: TabType) => void
  counts?: {
    requirements?: number
    valuePath?: number
    insights?: number
    nextSteps?: number
  }
}

export function TabNavigation({ activeTab, onTabChange, counts }: TabNavigationProps) {
  return (
    <div className="border-b border-ui-cardBorder bg-white">
      <nav className="flex space-x-1 px-6" aria-label="Tabs">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id
          const Icon = tab.icon

          // Get count for this tab
          let count: number | undefined
          if (tab.id === 'requirements') count = counts?.requirements
          if (tab.id === 'value-path') count = counts?.valuePath
          if (tab.id === 'insights') count = counts?.insights
          if (tab.id === 'next-steps') count = counts?.nextSteps

          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`
                group relative px-4 py-4 flex items-center gap-2 font-medium text-sm
                transition-all duration-200 border-b-2
                ${isActive
                  ? 'border-brand-primary text-brand-primary'
                  : 'border-transparent text-ui-supportText hover:text-ui-bodyText hover:border-ui-cardBorder'
                }
              `}
              aria-current={isActive ? 'page' : undefined}
            >
              <Icon className={`h-4 w-4 ${isActive ? 'text-brand-primary' : 'text-ui-supportText group-hover:text-ui-bodyText'}`} />
              <span>{tab.label}</span>
              {count !== undefined && count > 0 && (
                <span
                  className={`
                    inline-flex items-center justify-center px-2 py-0.5 rounded-full text-xs font-semibold
                    ${isActive
                      ? 'bg-brand-primary/10 text-brand-primary'
                      : 'bg-ui-buttonGray text-ui-supportText'
                    }
                  `}
                >
                  {count}
                </span>
              )}

              {/* Tooltip on hover (desktop only) */}
              <div className="hidden lg:block absolute top-full left-1/2 -translate-x-1/2 mt-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                <div className="bg-ui-headingDark text-white text-xs rounded px-2 py-1 whitespace-nowrap">
                  {tab.description}
                  <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-2 h-2 bg-ui-headingDark rotate-45"></div>
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
    <div className="relative lg:hidden border-b border-ui-cardBorder bg-white">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-4 py-3 flex items-center justify-between text-left"
      >
        <div className="flex items-center gap-2">
          {activeTabData && (
            <>
              <activeTabData.icon className="h-4 w-4 text-brand-primary" />
              <span className="font-medium text-ui-bodyText">{activeTabData.label}</span>
            </>
          )}
        </div>
        <svg
          className={`h-5 w-5 text-ui-supportText transition-transform ${isOpen ? 'rotate-180' : ''}`}
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
          <div className="absolute top-full left-0 right-0 bg-white border-b border-ui-cardBorder shadow-lg z-50">
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
                      ? 'bg-brand-primary/5 text-brand-primary'
                      : 'text-ui-bodyText hover:bg-ui-background'
                    }
                  `}
                >
                  <Icon className="h-4 w-4" />
                  <div className="flex-1">
                    <div className="font-medium">{tab.label}</div>
                    <div className="text-xs text-ui-supportText">{tab.description}</div>
                  </div>
                  {isActive && (
                    <svg className="h-5 w-5 text-brand-primary" fill="currentColor" viewBox="0 0 20 20">
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
