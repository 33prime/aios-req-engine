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
  // Project detail pages (workspace canvas) and projects list render without app shell
  const isProjectDetailPage = /^\/projects\/[^/]+\/?$/.test(pathname)
  const isProjectsListPage = pathname === '/projects'
  const isSettingsPage = pathname === '/settings'
  const isPeoplePage = pathname === '/people' || pathname.startsWith('/people/')
  const isClientsPage = pathname === '/clients' || pathname.startsWith('/clients/')

  // Pages that render without the app shell (they manage their own layout)
  if (isAuthPage || isProjectDetailPage || isProjectsListPage || isSettingsPage || isPeoplePage || isClientsPage) {
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
