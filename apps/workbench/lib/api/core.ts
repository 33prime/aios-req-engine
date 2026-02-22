import { API_BASE } from '../config'

// API key fallback disabled - auth is required
// Set NEXT_PUBLIC_BYPASS_AUTH=true to enable API key fallback for testing
export const ADMIN_API_KEY = process.env.NEXT_PUBLIC_BYPASS_AUTH === 'true'
  ? process.env.NEXT_PUBLIC_ADMIN_API_KEY
  : undefined

// Module-level access token for authenticated requests
let accessToken: string | null = null

export const setAccessToken = (token: string | null) => {
  accessToken = token
  // Persist to localStorage for page reloads
  if (typeof window !== 'undefined') {
    if (token) {
      localStorage.setItem('access_token', token)
    } else {
      localStorage.removeItem('access_token')
    }
  }
}

export const getAccessToken = () => {
  // Restore from localStorage if not set
  if (!accessToken && typeof window !== 'undefined') {
    accessToken = localStorage.getItem('access_token')
  }
  return accessToken
}

export const clearAuth = () => {
  accessToken = null
  if (typeof window !== 'undefined') {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    // Clear Supabase session storage
    const keysToRemove = Object.keys(localStorage).filter(key =>
      key.startsWith('sb-') || key.includes('supabase')
    )
    keysToRemove.forEach(key => localStorage.removeItem(key))
  }
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

export async function apiRequest<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE}/v1${endpoint}`

  // Build auth headers - prefer Bearer token, fallback to API key
  const authHeaders: Record<string, string> = {}
  if (accessToken) {
    authHeaders['Authorization'] = `Bearer ${accessToken}`
  } else if (ADMIN_API_KEY) {
    authHeaders['X-API-Key'] = ADMIN_API_KEY
  }

  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders,
      ...options?.headers,
    },
    ...options,
  })

  if (!response.ok) {
    const errorText = await response.text().catch(() => 'Unknown error')
    throw new ApiError(response.status, errorText)
  }

  return response.json()
}

// Current organization ID (set by org switcher)
let currentOrganizationId: string | null = null

export const setCurrentOrganization = (orgId: string | null) => {
  currentOrganizationId = orgId
}

export const getCurrentOrganization = () => currentOrganizationId

// Helper for org-scoped requests
export async function orgApiRequest<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const headers: Record<string, string> = {
    ...(options?.headers as Record<string, string>),
  }

  if (currentOrganizationId) {
    headers['X-Organization-Id'] = currentOrganizationId
  }

  return apiRequest<T>(endpoint, {
    ...options,
    headers,
  })
}

// Re-export API_BASE for modules that need it
export { API_BASE }
