'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useProfile } from '@/lib/hooks/use-api'

export function AdminGuard({ children }: { children: React.ReactNode }) {
  const { data: profile, isLoading } = useProfile()
  const router = useRouter()

  useEffect(() => {
    if (!isLoading && profile?.platform_role !== 'super_admin') {
      router.replace('/home')
    }
  }, [isLoading, profile, router])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-[#F4F4F4]">
        <div className="flex items-center gap-3 text-[#999999]">
          <div className="w-5 h-5 border-2 border-[#3FAF7A] border-t-transparent rounded-full animate-spin" />
          <span className="text-sm">Loading...</span>
        </div>
      </div>
    )
  }

  if (profile?.platform_role !== 'super_admin') {
    return null
  }

  return <>{children}</>
}
