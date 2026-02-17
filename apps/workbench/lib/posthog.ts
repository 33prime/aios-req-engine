import posthog from 'posthog-js'

let initialized = false

export function initPostHog() {
  if (initialized || typeof window === 'undefined') return

  const key = process.env.NEXT_PUBLIC_POSTHOG_KEY
  if (!key) return

  posthog.init(key, {
    api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST || 'https://us.i.posthog.com',
    capture_pageview: false, // We track manually on route changes
    capture_pageleave: true,
    persistence: 'localStorage',
    autocapture: false, // We use explicit tracking
  })

  initialized = true
}

export { posthog }
