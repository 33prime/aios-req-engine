'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Home, Workflow, Monitor, FileText, Users, LogOut } from 'lucide-react'
import type { PortalRole } from '@/types/portal'

interface NavItem {
  label: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  badge?: number | string | null
  adminOnly?: boolean
}

interface PortalSidebarProps {
  projectName: string
  portalRole: PortalRole
  pendingWorkflows: number
  teamCompletionPct?: number | null
}

export default function PortalSidebar({
  projectName,
  portalRole,
  pendingWorkflows,
  teamCompletionPct,
}: PortalSidebarProps) {
  const pathname = usePathname()
  const segments = pathname.split('/')
  const projectId = segments[2] || ''
  const basePath = `/portal/${projectId}`

  const navItems: NavItem[] = [
    { label: 'Home', href: '', icon: Home },
    { label: 'Workflows', href: '/workflows', icon: Workflow, badge: pendingWorkflows || null },
    { label: 'Prototype', href: '/prototype', icon: Monitor },
    { label: 'Materials', href: '/materials', icon: FileText },
    { label: 'Team', href: '/team', icon: Users, adminOnly: true, badge: teamCompletionPct != null ? `${teamCompletionPct}%` : null },
  ]

  const visibleItems = navItems.filter(item => !item.adminOnly || portalRole === 'client_admin')
  const initial = projectName ? projectName.charAt(0).toUpperCase() : '?'

  return (
    <aside className="fixed left-0 top-0 bottom-0 w-[220px] bg-[#F8F9FB] border-r border-border flex flex-col z-30">
      {/* Project header */}
      <div className="px-4 py-5 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-brand-primary rounded-lg flex items-center justify-center flex-shrink-0">
            <span className="text-white font-bold text-sm">{initial}</span>
          </div>
          <span className="font-semibold text-text-primary text-sm truncate">
            {projectName || 'Project Portal'}
          </span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4">
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
                flex items-center gap-2.5 px-4 py-2.5 text-sm transition-colors relative
                ${isActive
                  ? 'bg-[#E8F5E9] text-brand-primary font-medium border-l-[3px] border-l-brand-primary'
                  : 'text-text-secondary hover:bg-surface-subtle hover:text-text-primary border-l-[3px] border-l-transparent'
                }
              `}
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              <span className="flex-1 truncate">{item.label}</span>
              {item.badge != null && (
                <span className={`
                  text-[10px] font-medium px-1.5 py-0.5 rounded-full flex-shrink-0
                  ${isActive
                    ? 'bg-brand-primary/15 text-brand-primary'
                    : 'bg-surface-subtle text-text-muted'
                  }
                `}>
                  {item.badge}
                </span>
              )}
            </Link>
          )
        })}
      </nav>

      {/* Sign out */}
      <div className="border-t border-border px-4 py-3">
        <button
          onClick={() => {
            localStorage.removeItem('access_token')
            window.location.href = '/'
          }}
          className="flex items-center gap-2 text-sm text-text-muted hover:text-text-body transition-colors w-full"
        >
          <LogOut className="w-4 h-4" />
          Sign out
        </button>
      </div>
    </aside>
  )
}
