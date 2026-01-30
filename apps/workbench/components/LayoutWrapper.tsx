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
  const isWorkspacePage = pathname.includes('/workspace')

  // Pages that render without the app shell
  if (isAuthPage || isWorkspacePage) {
    return <>{children}</>
  }

  // Regular pages get the full app shell
  return (
    <div className="min-h-screen bg-gray-50">
      <AppHeader />
      <main>{children}</main>
    </div>
  )
}
