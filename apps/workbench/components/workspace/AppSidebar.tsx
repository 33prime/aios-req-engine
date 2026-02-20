/**
 * AppSidebar - Fixed left navigation bar
 *
 * Compact design with:
 * - Smaller logo, icons, text
 * - Tighter spacing
 * - Green "+" button and notification bell (visible in collapsed state too)
 * - Launches HybridOnboardingModal from "+" button
 */

'use client'

import { useState } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import { usePathname, useRouter } from 'next/navigation'
import {
  Home,
  Folder,
  Building2,
  UserCircle,
  Calendar,
  Settings,
  Shield,
  ChevronLeft,
  ChevronRight,
  User,
  Plus,
  ListTodo,
} from 'lucide-react'
import { useAuth } from '@/components/auth/AuthProvider'
import { useProfile } from '@/lib/hooks/use-api'
import { HybridOnboardingModal } from '@/app/projects/components/HybridOnboardingModal'
import { NotificationBell } from './NotificationBell'

// =============================================================================
// NavItem
// =============================================================================

interface NavItemProps {
  href: string
  icon: React.ReactNode
  label: string
  isActive: boolean
  isCollapsed: boolean
}

function NavItem({ href, icon, label, isActive, isCollapsed }: NavItemProps) {
  return (
    <Link
      href={href}
      className={`
        flex items-center gap-2.5 px-3 py-2 transition-all duration-200
        ${isActive
          ? 'bg-[#E8F5E9] text-[#3FAF7A] font-medium border-l-[3px] border-l-[#3FAF7A] -ml-px'
          : 'text-[#333333] hover:bg-[#F4F4F4] hover:text-[#333333]'
        }
        ${isCollapsed ? 'justify-center' : ''}
      `}
      title={isCollapsed ? label : undefined}
    >
      <span className={`flex-shrink-0 ${isActive ? 'text-[#3FAF7A]' : ''}`}>
        {icon}
      </span>
      {!isCollapsed && <span className="text-[13px]">{label}</span>}
    </Link>
  )
}

// =============================================================================
// AppSidebar
// =============================================================================

interface AppSidebarProps {
  isCollapsed?: boolean
  onToggleCollapse?: () => void
}

export function AppSidebar({ isCollapsed: controlledCollapsed, onToggleCollapse }: AppSidebarProps) {
  const pathname = usePathname()
  const router = useRouter()
  const { user } = useAuth()
  const { data: profile } = useProfile()
  const [internalCollapsed, setInternalCollapsed] = useState(false)
  const [showCreateProject, setShowCreateProject] = useState(false)

  // Use controlled state if provided, otherwise internal
  const isCollapsed = controlledCollapsed ?? internalCollapsed
  const handleToggle = onToggleCollapse ?? (() => setInternalCollapsed(!internalCollapsed))

  const displayName = profile?.first_name && profile?.last_name
    ? `${profile.first_name} ${profile.last_name}`
    : profile?.first_name ||
      user?.user_metadata?.full_name ||
      user?.user_metadata?.name ||
      user?.email?.split('@')[0] ||
      'User'

  const avatarUrl = profile?.photo_url ||
    user?.user_metadata?.avatar_url ||
    user?.user_metadata?.picture

  const navItems = [
    { href: '/home', icon: <Home className="w-4 h-4" />, label: 'Home' },
    { href: '/projects', icon: <Folder className="w-4 h-4" />, label: 'Projects' },
    { href: '/tasks', icon: <ListTodo className="w-4 h-4" />, label: 'Tasks' },
    { href: '/clients', icon: <Building2 className="w-4 h-4" />, label: 'Clients' },
    { href: '/people', icon: <UserCircle className="w-4 h-4" />, label: 'People' },
    { href: '/meetings', icon: <Calendar className="w-4 h-4" />, label: 'Meetings' },
    { href: '/settings', icon: <Settings className="w-4 h-4" />, label: 'Settings' },
    ...(profile?.platform_role === 'super_admin'
      ? [{ href: '/admin', icon: <Shield className="w-4 h-4" />, label: 'Admin' }]
      : []),
  ]

  // Handle project launched — navigate to projects list with build context
  const handleProjectLaunched = (response: { project_id: string; launch_id: string }) => {
    setShowCreateProject(false)
    router.push(`/projects?building=${response.project_id}&launch=${response.launch_id}`)
  }

  return (
    <>
      <aside
        className={`
          fixed left-0 top-0 h-screen bg-[#F8F9FB] border-r border-[#E5E5E5]
          flex flex-col z-40 transition-all duration-300
          ${isCollapsed ? 'w-16' : 'w-56'}
        `}
      >
        {/* Logo + Actions */}
        <div className={`flex items-center ${isCollapsed ? 'flex-col gap-2 px-2 pt-3 pb-2' : 'justify-between px-3 py-3'}`}>
          {/* Logo */}
          <Link href="/projects" className="flex items-center flex-shrink-0">
            {isCollapsed ? (
              <Image
                src="/favicon.svg"
                alt="Readytogo"
                width={24}
                height={24}
                className="w-6 h-6"
              />
            ) : (
              <Image
                src="/logo.svg"
                alt="Readytogo"
                width={110}
                height={22}
                priority
                className="h-5 w-auto"
              />
            )}
          </Link>

          {/* Action buttons — always visible */}
          <div className={`flex items-center ${isCollapsed ? 'flex-col gap-1.5' : 'gap-1'}`}>
            {/* Notification bell */}
            <NotificationBell />

            {/* Green "+" button */}
            <button
              onClick={() => setShowCreateProject(true)}
              className="p-1 rounded-full bg-[#3FAF7A] text-white hover:bg-[#25785A] transition-colors"
              title="New project"
            >
              <Plus className="w-3 h-3" />
            </button>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-1 space-y-px">
          {navItems.map((item) => (
            <NavItem
              key={item.label}
              href={item.href}
              icon={item.icon}
              label={item.label}
              isActive={item.href === '/admin' ? pathname.startsWith('/admin') : item.href === '/meetings' ? pathname.startsWith('/meetings') : item.href === '/tasks' ? pathname.startsWith('/tasks') : pathname === item.href}
              isCollapsed={isCollapsed}
            />
          ))}
        </nav>

        {/* Collapse Toggle */}
        <button
          onClick={handleToggle}
          className="mx-3 mb-2 p-1.5 rounded-lg text-[#999999] hover:bg-[#F4F4F4] hover:text-[#333333] transition-colors"
          title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {isCollapsed ? (
            <ChevronRight className="w-3.5 h-3.5 mx-auto" />
          ) : (
            <ChevronLeft className="w-3.5 h-3.5" />
          )}
        </button>

        {/* User Profile */}
        {user && (
          <div className={`border-t border-[#E5E5E5] p-2.5 ${isCollapsed ? 'px-2' : ''}`}>
            <Link
              href="/settings"
              className={`
                flex items-center gap-2.5 rounded-lg p-1.5 transition-colors
                hover:bg-[#F4F4F4] text-[#333333]
                ${isCollapsed ? 'justify-center' : ''}
              `}
              title={isCollapsed ? displayName : undefined}
            >
              <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#3FAF7A] to-[#25785A] flex items-center justify-center overflow-hidden flex-shrink-0">
                {avatarUrl ? (
                  <Image
                    src={avatarUrl}
                    alt={displayName}
                    width={28}
                    height={28}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <User className="w-3.5 h-3.5 text-white" />
                )}
              </div>
              {!isCollapsed && (
                <div className="flex-1 min-w-0">
                  <p className="text-[13px] font-medium text-[#333333] truncate">
                    {displayName}
                  </p>
                  <p className="text-[11px] text-[#999999] truncate">
                    {user.email}
                  </p>
                </div>
              )}
            </Link>
          </div>
        )}
      </aside>

      {/* Hybrid Onboarding Modal */}
      <HybridOnboardingModal
        isOpen={showCreateProject}
        onClose={() => setShowCreateProject(false)}
        onLaunched={handleProjectLaunched}
      />
    </>
  )
}

export default AppSidebar
