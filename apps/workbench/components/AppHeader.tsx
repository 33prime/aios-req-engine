'use client'

import Link from 'next/link'
import Image from 'next/image'
import { Settings, User } from 'lucide-react'
import { useAuth } from '@/components/auth/AuthProvider'

export default function AppHeader() {
  const { user } = useAuth()

  // Get user's full name from metadata or email
  const displayName = user?.user_metadata?.full_name ||
    user?.user_metadata?.name ||
    user?.email?.split('@')[0] ||
    'User'

  // Get avatar URL if available
  const avatarUrl = user?.user_metadata?.avatar_url || user?.user_metadata?.picture

  return (
    <header className="bg-white shadow-sm border-b">
      {/* Use same padding as page content (px-6) for alignment with Daily Snapshot */}
      <div className="px-6">
        <div className="flex items-center py-3">
          {/* Logo - left aligned with page content */}
          <Link href="/projects" className="flex items-center hover:opacity-80 transition-opacity">
            <Image
              src="/logo.svg"
              alt="Readytogo"
              width={160}
              height={30}
              priority
              className="h-7 w-auto"
            />
          </Link>

          {/* Spacer to push right content */}
          <div className="flex-1" />

          {/* Right side items */}
          <div className="flex items-center gap-3">
            {/* Profile with avatar and full name */}
            {user && (
              <Link
                href="/settings"
                className="flex items-center gap-2.5 hover:bg-zinc-50 rounded-full px-3 py-1.5 transition-colors"
              >
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-emerald-400 to-teal-500 flex items-center justify-center overflow-hidden">
                  {avatarUrl ? (
                    <Image
                      src={avatarUrl}
                      alt={displayName}
                      width={32}
                      height={32}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <User className="w-4 h-4 text-white" />
                  )}
                </div>
                <span className="text-sm font-medium text-zinc-700">{displayName}</span>
              </Link>
            )}

            {/* Settings icon */}
            <Link
              href="/settings"
              className="p-2 hover:bg-zinc-100 rounded-lg transition-colors text-zinc-400 hover:text-zinc-600"
              title="Settings"
            >
              <Settings className="w-5 h-5" />
            </Link>
          </div>
        </div>
      </div>
    </header>
  )
}
