'use client'

import { ReactNode } from 'react'
import { usePathname } from 'next/navigation'
import AppHeader from '@/components/AppHeader'

interface LayoutWrapperProps {
  children: ReactNode
}

export function LayoutWrapper({ children }: LayoutWrapperProps) {
  const pathname = usePathname()
  const isAuthPage = pathname.startsWith('/auth')
  // Project detail pages (workspace canvas) and sub-pages (prototype, diagnostics) render without app shell
  const isProjectDetailPage = /^\/projects\/[^/]+/.test(pathname)
  const isProjectsListPage = pathname === '/projects'
  const isSettingsPage = pathname === '/settings'
  const isPeoplePage = pathname === '/people' || pathname.startsWith('/people/')
  const isClientsPage = pathname === '/clients' || pathname.startsWith('/clients/')
  const isHomePage = pathname === '/home'
  const isAdminPage = pathname === '/admin' || pathname.startsWith('/admin/')
  const isMeetingsPage = pathname === '/meetings' || pathname.startsWith('/meetings/')
  const isTasksPage = pathname === '/tasks' || pathname.startsWith('/tasks/')

  // Pages that render without the app shell (they manage their own layout)
  if (isAuthPage || isProjectDetailPage || isProjectsListPage || isSettingsPage || isPeoplePage || isClientsPage || isHomePage || isAdminPage || isMeetingsPage || isTasksPage) {
    return <>{children}</>
  }

  // Regular pages get the full app shell with AppHeader
  return (
    <div className="min-h-screen bg-gray-50">
      <AppHeader />
      <main>{children}</main>
    </div>
  )
}
