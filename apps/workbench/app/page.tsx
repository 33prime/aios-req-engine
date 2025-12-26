'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { ArrowRight, Briefcase, FolderOpen, Hash } from 'lucide-react'

export default function HomePage() {
  const [projectId, setProjectId] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!projectId.trim()) return

    setIsLoading(true)
    try {
      // Validate project ID by checking baseline status
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}/v1/projects/${projectId}/baseline`)
      if (response.ok) {
        router.push(`/projects/${projectId}`)
      } else {
        alert('Invalid project ID or project not found')
      }
    } catch (error) {
      alert('Failed to validate project ID. Please check your API connection.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-16">
      <div className="text-center mb-12">
        <div className="flex justify-center mb-6">
          <div className="p-4 bg-blue-100 rounded-full">
            <Briefcase className="h-12 w-12 text-blue-600" />
          </div>
        </div>
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Consultant Workbench
        </h1>
        <p className="text-xl text-gray-600 mb-8">
          AI-powered requirements management and analysis platform
        </p>
      </div>

      <div className="max-w-2xl mx-auto space-y-6">
        {/* Primary: Browse Projects */}
        <div className="card">
          <div className="flex items-center gap-4 mb-4">
            <div className="p-3 bg-brand-primary/10 rounded-lg">
              <FolderOpen className="h-6 w-6 text-brand-primary" />
            </div>
            <div className="flex-1">
              <h2 className="text-xl font-semibold text-gray-900">
                Browse Projects
              </h2>
              <p className="text-sm text-gray-600">
                View and manage all your projects
              </p>
            </div>
          </div>

          <button
            onClick={() => router.push('/projects')}
            className="btn btn-primary w-full flex items-center justify-center"
          >
            <FolderOpen className="h-5 w-5 mr-2" />
            Go to Projects
            <ArrowRight className="h-5 w-5 ml-2" />
          </button>
        </div>

        {/* Secondary: Quick Access by ID */}
        <div className="card border-2 border-dashed border-gray-300">
          <div className="flex items-center gap-4 mb-4">
            <div className="p-3 bg-gray-100 rounded-lg">
              <Hash className="h-6 w-6 text-gray-600" />
            </div>
            <div className="flex-1">
              <h2 className="text-xl font-semibold text-gray-900">
                Quick Access by ID
              </h2>
              <p className="text-sm text-gray-600">
                Jump directly to a project using its UUID
              </p>
            </div>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="mb-4">
              <label htmlFor="projectId" className="block text-sm font-medium text-gray-700 mb-2">
                Project UUID
              </label>
              <input
                type="text"
                id="projectId"
                value={projectId}
                onChange={(e) => setProjectId(e.target.value)}
                placeholder="e.g., 97e0dc34-feb9-48ca-a3a3-ba104d9e8203"
                className="input"
                required
              />
            </div>

            <button
              type="submit"
              disabled={isLoading || !projectId.trim()}
              className="btn btn-secondary w-full flex items-center justify-center"
            >
              {isLoading ? (
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-current mr-2"></div>
              ) : (
                <ArrowRight className="h-5 w-5 mr-2" />
              )}
              Open Project
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
