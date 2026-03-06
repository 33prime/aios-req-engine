'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Home, Workflow, Monitor, LogOut, ChevronsLeft, ChevronsRight } from 'lucide-react'
import type { PortalRole } from '@/types/portal'

interface NavItem {
  label: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  badge?: number | string | null
}

interface PortalSidebarProps {
  projectName: string
  portalRole: PortalRole
  pendingWorkflows: number
  collapsed: boolean
  onToggleCollapse: () => void
}

export default function PortalSidebar({
  projectName,
  portalRole,
  pendingWorkflows,
  collapsed,
  onToggleCollapse,
}: PortalSidebarProps) {
  const pathname = usePathname()
  const segments = pathname.split('/')
  const projectId = segments[2] || ''
  const basePath = `/portal/${projectId}`

  const navItems: NavItem[] = [
    { label: 'Home', href: '', icon: Home },
    { label: 'Workflows', href: '/workflows', icon: Workflow, badge: pendingWorkflows || null },
    { label: 'Prototype', href: '/prototype', icon: Monitor },
  ]

  const initial = projectName ? projectName.charAt(0).toUpperCase() : '?'
  const width = collapsed ? 'w-[64px]' : 'w-[220px]'

  return (
    <aside className={`fixed left-0 top-0 bottom-0 ${width} bg-[#F8F9FB] border-r border-border flex flex-col z-30 transition-[width] duration-200`}>
      {/* Project header */}
      <div className="px-3 py-4 border-b border-border">
        <div className={`flex items-center ${collapsed ? 'justify-center' : 'gap-3 px-1'}`}>
          <div className="w-8 h-8 bg-brand-primary rounded-lg flex items-center justify-center flex-shrink-0">
            <span className="text-white font-bold text-sm">{initial}</span>
          </div>
          {!collapsed && (
            <span className="font-semibold text-text-primary text-sm truncate">
              {projectName || 'Project Portal'}
            </span>
          )}
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-3">
        {navItems.map(item => {
          const fullPath = `${basePath}${item.href}`
          const isActive = item.href === ''
            ? pathname === basePath || pathname === `${basePath}/`
            : pathname.startsWith(fullPath)
          const Icon = item.icon

          return (
            <Link
              key={item.href}
              href={fullPath}
              title={collapsed ? item.label : undefined}
              className={`
                flex items-center text-sm transition-colors relative
                ${collapsed
                  ? 'justify-center px-0 py-2.5 mx-2 rounded-lg'
                  : 'gap-2.5 px-4 py-2.5 border-l-[3px]'
                }
                ${isActive
                  ? collapsed
                    ? 'bg-[#E8F5E9] text-brand-primary font-medium'
                    : 'bg-[#E8F5E9] text-brand-primary font-medium border-l-brand-primary'
                  : collapsed
                    ? 'text-text-secondary hover:bg-surface-subtle hover:text-text-primary'
                    : 'text-text-secondary hover:bg-surface-subtle hover:text-text-primary border-l-transparent'
                }
              `}
            >
              <Icon className={`flex-shrink-0 ${collapsed ? 'w-5 h-5' : 'w-4 h-4'}`} />
              {!collapsed && <span className="flex-1 truncate">{item.label}</span>}
              {!collapsed && item.badge != null && (
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
              {/* Collapsed badge dot */}
              {collapsed && item.badge != null && (
                <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-brand-primary rounded-full" />
              )}
            </Link>
          )
        })}
      </nav>

      {/* Collapse toggle */}
      <div className="border-t border-border px-2 py-2">
        <button
          onClick={onToggleCollapse}
          className="flex items-center justify-center w-full py-2 rounded-lg text-text-muted hover:bg-surface-subtle hover:text-text-body transition-colors"
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed
            ? <ChevronsRight className="w-4 h-4" />
            : <ChevronsLeft className="w-4 h-4" />
          }
        </button>
      </div>

      {/* Sign out */}
      <div className="border-t border-border px-3 py-3">
        <button
          onClick={() => {
            localStorage.removeItem('access_token')
            window.location.href = '/'
          }}
          title={collapsed ? 'Sign out' : undefined}
          className={`flex items-center text-sm text-text-muted hover:text-text-body transition-colors w-full ${
            collapsed ? 'justify-center' : 'gap-2'
          }`}
        >
          <LogOut className="w-4 h-4" />
          {!collapsed && 'Sign out'}
        </button>
      </div>
    </aside>
  )
}
