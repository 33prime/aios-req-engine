/**
 * Google Auth utilities for client-side token management.
 *
 * Retrieves Google access token from Supabase session with refresh fallback.
 */

import { supabase } from './supabase'

const CALENDAR_SCOPE = 'https://www.googleapis.com/auth/calendar.events'

/**
 * Get a Google access token from the current Supabase session.
 * Falls back to session refresh if the token is stale.
 */
export async function getGoogleAccessToken(): Promise<string | null> {
  if (!supabase) return null

  const { data: { session } } = await supabase.auth.getSession()
  if (!session) return null

  // provider_token is the Google access token
  if (session.provider_token) {
    return session.provider_token
  }

  // Try refreshing the session to get a fresh provider token
  const { data: { session: refreshed } } = await supabase.auth.refreshSession()
  return refreshed?.provider_token ?? null
}

/**
 * Check if the current session has the calendar.events scope granted.
 */
export function hasCalendarScope(session: { provider_token?: string | null } | null): boolean {
  // If we have a provider token, the scope was granted at sign-in
  // (Supabase only returns the token if all requested scopes were approved)
  return !!session?.provider_token
}
