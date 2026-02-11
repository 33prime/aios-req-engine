/**
 * AppSidebar - Fixed left navigation bar
 *
 * Compact design with:
 * - Smaller logo, icons, text
 * - Tighter spacing
 * - Green "+" button and notification bell (visible in collapsed state too)
 * - Launches SmartProjectCreation modal from "+" button
 */

'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import { usePathname, useRouter } from 'next/navigation'
import {
  Home,
  Folder,
  UserCircle,
  Settings,
  ChevronLeft,
  ChevronRight,
  User,
  Bell,
  Plus,
} from 'lucide-react'
import { useAuth } from '@/components/auth/AuthProvider'
import { getMyProfile } from '@/lib/api'
import { SmartProjectCreation } from '@/app/projects/components/SmartProjectCreation'
import type { Profile } from '@/types/api'

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
          ? 'bg-brand-teal/5 text-brand-teal font-medium border-l-[3px] border-l-brand-teal -ml-px'
          : 'text-ui-bodyText hover:bg-ui-background hover:text-ui-headingDark'
        }
        ${isCollapsed ? 'justify-center' : ''}
      `}
      title={isCollapsed ? label : undefined}
    >
      <span className={`flex-shrink-0 ${isActive ? 'text-brand-teal' : ''}`}>
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
  const [profile, setProfile] = useState<Profile | null>(null)
  const [internalCollapsed, setInternalCollapsed] = useState(false)
  const [showCreateProject, setShowCreateProject] = useState(false)

  // Use controlled state if provided, otherwise internal
  const isCollapsed = controlledCollapsed ?? internalCollapsed
  const handleToggle = onToggleCollapse ?? (() => setInternalCollapsed(!internalCollapsed))

  useEffect(() => {
    if (user) {
      getMyProfile()
        .then(setProfile)
        .catch(() => {})
    }
  }, [user])

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
    { href: '/', icon: <Home className="w-4 h-4" />, label: 'Home' },
    { href: '/projects', icon: <Folder className="w-4 h-4" />, label: 'Projects' },
    { href: '/people', icon: <UserCircle className="w-4 h-4" />, label: 'People' },
    { href: '/settings', icon: <Settings className="w-4 h-4" />, label: 'Admin Panel' },
  ]

  // Handle project created
  const handleProjectCreated = (response: { id: string; name: string; onboarding_job_id?: string }) => {
    setShowCreateProject(false)
    router.push(`/projects/${response.id}`)
  }

  return (
    <>
      <aside
        className={`
          fixed left-0 top-0 h-screen bg-[#F8F9FB] border-r border-ui-cardBorder
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
            <button
              className="relative p-1.5 rounded-lg text-ui-supportText hover:bg-ui-buttonGray hover:text-ui-headingDark transition-colors"
              title="Notifications"
            >
              <Bell className="w-4 h-4" />
              {/* Badge placeholder — will be wired later */}
            </button>

            {/* Green "+" button */}
            <button
              onClick={() => setShowCreateProject(true)}
              className="p-1.5 rounded-full bg-brand-teal text-white hover:bg-brand-tealDark transition-colors"
              title="New project"
            >
              <Plus className="w-3.5 h-3.5" />
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
              isActive={pathname === item.href}
              isCollapsed={isCollapsed}
            />
          ))}
        </nav>

        {/* Collapse Toggle */}
        <button
          onClick={handleToggle}
          className="mx-3 mb-2 p-1.5 rounded-lg text-ui-supportText hover:bg-ui-background hover:text-ui-bodyText transition-colors"
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
          <div className={`border-t border-ui-cardBorder p-2.5 ${isCollapsed ? 'px-2' : ''}`}>
            <Link
              href="/settings"
              className={`
                flex items-center gap-2.5 rounded-lg p-1.5 transition-colors
                hover:bg-ui-background text-ui-bodyText
                ${isCollapsed ? 'justify-center' : ''}
              `}
              title={isCollapsed ? displayName : undefined}
            >
              <div className="w-7 h-7 rounded-full bg-gradient-to-br from-emerald-400 to-teal-500 flex items-center justify-center overflow-hidden flex-shrink-0">
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
                  <p className="text-[13px] font-medium text-ui-headingDark truncate">
                    {displayName}
                  </p>
                  <p className="text-[11px] text-ui-supportText truncate">
                    {user.email}
                  </p>
                </div>
              )}
            </Link>
          </div>
        )}
      </aside>

      {/* Smart Project Creation Modal */}
      <SmartProjectCreation
        isOpen={showCreateProject}
        onClose={() => setShowCreateProject(false)}
        onSuccess={handleProjectCreated}
      />
    </>
  )
}

export default AppSidebar
