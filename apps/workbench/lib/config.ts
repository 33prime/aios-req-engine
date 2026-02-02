/**
 * Centralized application configuration.
 * Single source of truth for environment variables.
 */

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000'
export const API_V1 = `${API_BASE}/v1`
