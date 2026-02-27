/**
 * Features Page - Redirect
 *
 * Features are now shown nested within the Product Requirements tab.
 * This page redirects to the main project page.
 */

'use client'

import { useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'

export default function FeaturesPage() {
  const params = useParams()
  const router = useRouter()
  const projectId = params.projectId as string

  useEffect(() => {
    // Redirect to Product Requirements tab (main project page)
    router.replace(`/projects/${projectId}`)
  }, [projectId, router])

  return (
    <div className="p-6 flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-primary mx-auto mb-4"></div>
        <p className="text-[12px] text-text-placeholder">
          Redirecting to Product Requirements...
        </p>
      </div>
    </div>
  )
}
