'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  Users,
  FolderOpen,
  Building2,
  DollarSign,
  BarChart3,
  Target,
  FlaskConical,
  Shield,
} from 'lucide-react'

const navItems = [
  { href: '/admin', icon: LayoutDashboard, label: 'Dashboard', exact: true },
  { href: '/admin/users', icon: Users, label: 'Users' },
  { href: '/admin/projects', icon: FolderOpen, label: 'Projects' },
  { href: '/admin/clients', icon: Building2, label: 'Clients' },
  { href: '/admin/cost', icon: DollarSign, label: 'Cost & Usage' },
  { href: '/admin/analytics', icon: BarChart3, label: 'Analytics' },
  { href: '/admin/icp', icon: Target, label: 'ICP' },
  { href: '/admin/evals', icon: FlaskConical, label: 'Evals' },
]

export function AdminSidebar() {
  const pathname = usePathname()

  return (
    <div className="w-[200px] bg-white border-r border-[#E5E5E5] flex flex-col flex-shrink-0">
      {/* Header */}
      <div className="px-4 py-4 border-b border-[#E5E5E5]">
        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4 text-[#3FAF7A]" />
          <span className="text-[14px] font-semibold text-[#333333]">Admin</span>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-2">
        {navItems.map((item) => {
          const isActive = item.exact
            ? pathname === item.href
            : pathname === item.href || pathname.startsWith(item.href + '/')

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`
                flex items-center gap-2.5 px-4 py-2 text-[13px] transition-colors
                ${isActive
                  ? 'bg-[#E8F5E9] text-[#3FAF7A] font-medium border-l-[3px] border-l-[#3FAF7A]'
                  : 'text-[#666666] hover:bg-[#F4F4F4] hover:text-[#333333] border-l-[3px] border-l-transparent'
                }
              `}
            >
              <item.icon className="w-4 h-4 flex-shrink-0" />
              <span>{item.label}</span>
            </Link>
          )
        })}
      </nav>
    </div>
  )
}
