'use client'

import { useState } from 'react'
import { AppSidebar } from '@/components/workspace/AppSidebar'
import { AdminSidebar } from './components/AdminSidebar'
import { AdminGuard } from './components/AdminGuard'

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const [isCollapsed, setIsCollapsed] = useState(false)

  return (
    <AdminGuard>
      <div className="min-h-screen bg-[#F4F4F4]">
        <AppSidebar
          isCollapsed={isCollapsed}
          onToggleCollapse={() => setIsCollapsed(!isCollapsed)}
        />

        <div
          className="flex min-h-screen transition-all duration-300"
          style={{ marginLeft: isCollapsed ? 64 : 224 }}
        >
          <AdminSidebar />

          <main className="flex-1 p-6 overflow-auto">
            <div className="max-w-[1400px] mx-auto">
              {children}
            </div>
          </main>
        </div>
      </div>
    </AdminGuard>
  )
}
