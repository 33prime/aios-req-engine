'use client'

import { useEffect, useRef } from 'react'
import { usePathname } from 'next/navigation'
import { useAuth } from '@/components/auth/AuthProvider'
import { useProfile } from '@/lib/hooks/use-api'
import { initPostHog, posthog } from '@/lib/posthog'

export function PostHogProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const { user } = useAuth()
  const { data: profile } = useProfile()
  const identifiedRef = useRef(false)
  const enrichmentSyncedRef = useRef(false)

  // Initialize PostHog on mount
  useEffect(() => {
    initPostHog()
  }, [])

  // Track page views on route changes
  useEffect(() => {
    if (typeof window === 'undefined') return
    posthog.capture('$pageview', { $current_url: window.location.href })
  }, [pathname])

  // Identify user when auth loads
  useEffect(() => {
    if (!user || identifiedRef.current) return
    identifiedRef.current = true

    posthog.identify(user.id, {
      email: user.email,
      provider: user.app_metadata?.provider,
    })
  }, [user])

  // Push enrichment person properties when profile is enriched
  useEffect(() => {
    if (!profile || enrichmentSyncedRef.current) return
    if (profile.enrichment_status !== 'enriched') return
    enrichmentSyncedRef.current = true

    posthog.people.set({
      industry_expertise: profile.industry_expertise,
      methodology_expertise: profile.methodology_expertise,
      profile_completeness: profile.profile_completeness,
      enrichment_status: profile.enrichment_status,
    })
  }, [profile])

  return <>{children}</>
}
