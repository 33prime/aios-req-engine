'use client'

import Link from 'next/link'
import { Settings } from 'lucide-react'

export default function AppHeader() {
  return (
    <header className="bg-white shadow-sm border-b">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center py-3">
          <Link href="/projects" className="text-xl font-bold text-gray-900 hover:text-emerald-600 transition-colors">
            Readytogo
          </Link>
          <div className="flex items-center gap-4">
            <Link
              href="/settings"
              className="p-2 hover:bg-zinc-100 rounded-lg transition-colors text-zinc-500 hover:text-zinc-700"
              title="Settings"
            >
              <Settings className="w-5 h-5" />
            </Link>
          </div>
        </div>
      </div>
    </header>
  )
}
