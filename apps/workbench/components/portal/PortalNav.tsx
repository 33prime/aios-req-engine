'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import type { PortalRole } from '@/types/portal'

interface PortalNavProps {
  projectId: string
  portalRole: PortalRole
  projectName?: string
}

const NAV_ITEMS = [
  { label: 'Home', href: '', icon: '⌂' },
  { label: 'Validate', href: '/validate', icon: '✓' },
  { label: 'Prototype', href: '/prototype', icon: '◎' },
  { label: 'Materials', href: '/materials', icon: '▤' },
  { label: 'Team', href: '/team', icon: '⊕', adminOnly: true },
]

export default function PortalNav({ projectId, portalRole, projectName }: PortalNavProps) {
  const pathname = usePathname()
  const basePath = `/portal/${projectId}`

  const visibleItems = NAV_ITEMS.filter(item => !item.adminOnly || portalRole === 'client_admin')

  return (
    <nav className="border-b border-gray-200 bg-white">
      <div className="max-w-5xl mx-auto px-4">
        <div className="flex items-center gap-1 overflow-x-auto">
          {visibleItems.map(item => {
            const fullPath = `${basePath}${item.href}`
            const isActive = item.href === ''
              ? pathname === basePath || pathname === `${basePath}/`
              : pathname.startsWith(fullPath)

            return (
              <Link
                key={item.href}
                href={fullPath}
                className={`
                  flex items-center gap-1.5 px-4 py-3 text-sm font-medium
                  border-b-2 transition-colors whitespace-nowrap
                  ${isActive
                    ? 'border-[#009b87] text-[#009b87]'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }
                `}
              >
                <span className="text-xs">{item.icon}</span>
                {item.label}
              </Link>
            )
          })}
        </div>
      </div>
    </nav>
  )
}
