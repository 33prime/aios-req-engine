'use client'

import { useState } from 'react'
import { EvalDashboard } from './components/EvalDashboard'
import { EvalRunBrowser } from './components/EvalRunBrowser'
import { EvalLearnings } from './components/EvalLearnings'

const tabs = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'runs', label: 'Eval Runs' },
  { id: 'learnings', label: 'Learnings' },
] as const

type TabId = (typeof tabs)[number]['id']

export default function EvalsPage() {
  const [activeTab, setActiveTab] = useState<TabId>('dashboard')

  return (
    <div className="space-y-6">
      <h1 className="text-[22px] font-bold text-[#333333]">Prototype Evals</h1>

      {/* Tabs */}
      <div className="flex gap-0 border-b border-[#E5E5E5]">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`
              px-4 py-2.5 text-[13px] font-medium transition-colors relative
              ${activeTab === tab.id
                ? 'text-[#3FAF7A]'
                : 'text-[#666666] hover:text-[#333333]'
              }
            `}
          >
            {tab.label}
            {activeTab === tab.id && (
              <div className="absolute bottom-0 left-0 right-0 h-[2px] bg-[#3FAF7A]" />
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === 'dashboard' && <EvalDashboard />}
      {activeTab === 'runs' && <EvalRunBrowser />}
      {activeTab === 'learnings' && <EvalLearnings />}
    </div>
  )
}
