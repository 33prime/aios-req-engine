'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Home, CheckSquare, Monitor, FileText, Users } from 'lucide-react'
import type { PortalRole } from '@/types/portal'

interface PortalNavProps {
  projectId: string
  portalRole: PortalRole
  projectName?: string
}

const NAV_ITEMS = [
  { label: 'Home', href: '', icon: Home },
  { label: 'Validate', href: '/validate', icon: CheckSquare },
  { label: 'Prototype', href: '/prototype', icon: Monitor },
  { label: 'Materials', href: '/materials', icon: FileText },
  { label: 'Team', href: '/team', icon: Users, adminOnly: true },
]

export default function PortalNav({ projectId, portalRole }: PortalNavProps) {
  const pathname = usePathname()
  const basePath = `/portal/${projectId}`

  const visibleItems = NAV_ITEMS.filter(item => !item.adminOnly || portalRole === 'client_admin')

  return (
    <nav className="border-b border-border bg-surface-card">
      <div className="max-w-5xl mx-auto px-4">
        <div className="flex items-center gap-1 overflow-x-auto">
          {visibleItems.map(item => {
            const fullPath = `${basePath}${item.href}`
            const isActive = item.href === ''
              ? pathname === basePath || pathname === `${basePath}/`
              : pathname.startsWith(fullPath)
            const Icon = item.icon

            return (
              <Link
                key={item.href}
                href={fullPath}
                className={`
                  flex items-center gap-1.5 px-4 py-3 text-sm font-medium
                  border-b-2 transition-colors whitespace-nowrap
                  ${isActive
                    ? 'border-brand-primary text-brand-primary'
                    : 'border-transparent text-text-muted hover:text-text-body hover:border-border-strong'
                  }
                `}
              >
                <Icon className="w-4 h-4" />
                {item.label}
              </Link>
            )
          })}
        </div>
      </div>
    </nav>
  )
}
