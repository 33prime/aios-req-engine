'use client'

import { useParams } from 'next/navigation'
import { useEffect, useState } from 'react'
import { Card, CardHeader } from '@/components/ui'

interface Job {
  id: string
  job_type: string
  status: string
  created_at: string
  completed_at: string | null
  error_message: string | null
  input_json: any
  output_json: any
}

interface Project {
  id: string
  name: string
  prd_mode: string
}

export default function DiagnosticsPage() {
  const params = useParams()
  const projectId = params.projectId as string
  const [project, setProject] = useState<Project | null>(null)
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function loadDiagnostics() {
      try {
        setLoading(true)
        const apiBase = process.env.NEXT_PUBLIC_API_BASE || ''

        // Get project details
        const projectRes = await fetch(`${apiBase}/v1/projects/${projectId}`)
        if (projectRes.ok) {
          const projectData = await projectRes.json()
          setProject(projectData)
        }

        // Get recent jobs
        const jobsRes = await fetch(`${apiBase}/v1/jobs?project_id=${projectId}&limit=20`)
        if (jobsRes.ok) {
          const jobsData = await jobsRes.json()
          setJobs(jobsData.jobs || [])
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load diagnostics')
      } finally {
        setLoading(false)
      }
    }

    loadDiagnostics()
  }, [projectId])

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="text-center py-12">Loading diagnostics...</div>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold mb-2">Diagnostics</h1>
        <p className="text-[#999999]">Debug auto-trigger workflow and job execution</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
          {error}
        </div>
      )}

      {/* Project Mode */}
      <Card>
        <CardHeader title="Project Configuration" />
        <div className="space-y-3">
          <div>
            <div className="text-sm font-medium text-[#333333] mb-1">Project Name</div>
            <div className="text-lg text-[#333333]">{project?.name || 'Unknown'}</div>
          </div>
          <div>
            <div className="text-sm font-medium text-[#333333] mb-1">PRD Mode</div>
            <div className="flex items-center gap-2">
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                project?.prd_mode === 'initial'
                  ? 'bg-blue-100 text-blue-800'
                  : 'bg-purple-100 text-purple-800'
              }`}>
                {project?.prd_mode || 'unknown'}
              </span>
              <span className="text-sm text-[#999999]">
                {project?.prd_mode === 'initial'
                  ? '→ Runs extract_facts after signal ingestion'
                  : '→ Runs surgical_update after signal ingestion'}
              </span>
            </div>
          </div>
        </div>
      </Card>

      {/* Recent Jobs */}
      <Card>
        <CardHeader
          title={`Recent Jobs (${jobs.length})`}
          subtitle="Jobs created by signal ingestion and API calls"
        />

        {jobs.length === 0 ? (
          <div className="text-center py-8 text-[#999999]">
            No jobs found. This is unusual - signal ingestion should create jobs.
          </div>
        ) : (
          <div className="space-y-3">
            {jobs.map((job) => (
              <div
                key={job.id}
                className="bg-[#F9F9F9] border border-[#E5E5E5] rounded-lg p-4"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-medium text-[#333333]">
                      {job.job_type}
                    </span>
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                      job.status === 'completed' ? 'bg-green-100 text-green-800' :
                      job.status === 'failed' ? 'bg-red-100 text-red-800' :
                      job.status === 'running' ? 'bg-blue-100 text-blue-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {job.status}
                    </span>
                  </div>
                  <span className="text-xs text-[#999999]">
                    {new Date(job.created_at).toLocaleString()}
                  </span>
                </div>

                {job.error_message && (
                  <div className="mb-2 text-sm text-red-600 bg-red-50 p-2 rounded">
                    Error: {job.error_message}
                  </div>
                )}

                <div className="grid grid-cols-2 gap-4 text-xs">
                  <div>
                    <div className="text-[#999999] mb-1">Input</div>
                    <pre className="bg-gray-50 p-2 rounded overflow-x-auto">
                      {JSON.stringify(job.input_json, null, 2)}
                    </pre>
                  </div>
                  <div>
                    <div className="text-[#999999] mb-1">Output</div>
                    <pre className="bg-gray-50 p-2 rounded overflow-x-auto">
                      {JSON.stringify(job.output_json, null, 2)}
                    </pre>
                  </div>
                </div>

                <div className="mt-2 text-xs text-[#999999] font-mono">
                  ID: {job.id}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Troubleshooting Guide */}
      <Card>
        <CardHeader title="Troubleshooting Guide" />
        <div className="space-y-4 text-sm">
          <div>
            <h4 className="font-medium text-[#333333] mb-2">
              ❌ Problem: "No jobs recorded" after adding signal
            </h4>
            <ul className="list-disc list-inside space-y-1 text-[#999999] ml-4">
              <li>Check if "ingest" jobs appear above - these should be created for every signal</li>
              <li>If no ingest jobs: signal ingestion is failing completely (check backend logs)</li>
              <li>If ingest jobs exist: signal was ingested successfully</li>
            </ul>
          </div>

          <div>
            <h4 className="font-medium text-[#333333] mb-2">
              ❌ Problem: "Zero impact" shown for signal
            </h4>
            <ul className="list-disc list-inside space-y-1 text-[#999999] ml-4">
              <li>Impact is recorded when PRD/VP/Features are created with evidence from signal chunks</li>
              <li>In <strong>initial mode</strong>: extract_facts runs automatically (no job created for this!)</li>
              <li>In <strong>maintenance mode</strong>: surgical_update runs automatically (no job created for this!)</li>
              <li>Zero impact means these agents either didn't run or didn't create entities</li>
              <li><strong>CRITICAL</strong>: Auto-trigger errors are logged but NOT surfaced to UI</li>
            </ul>
          </div>

          <div>
            <h4 className="font-medium text-[#333333] mb-2">
              ✅ How to verify auto-trigger ran
            </h4>
            <ul className="list-disc list-inside space-y-1 text-[#999999] ml-4">
              <li>Check backend logs for: "Auto-triggering processing for signal..."</li>
              <li>Check for: "Project in initial mode, triggering extract_facts" (or surgical_update)</li>
              <li>Check for errors: "Extract facts failed: ..." or "Surgical update failed: ..."</li>
              <li>These errors are CAUGHT and logged but don't fail the ingestion</li>
            </ul>
          </div>

          <div>
            <h4 className="font-medium text-[#333333] mb-2">
              🔧 Next Steps
            </h4>
            <ol className="list-decimal list-inside space-y-1 text-[#999999] ml-4">
              <li>Check your PRD mode above (initial vs maintenance)</li>
              <li>Look for "ingest" jobs in the list above from when you added the signal</li>
              <li>Check backend logs for auto-trigger execution and any errors</li>
              <li>If extract_facts/surgical_update failed silently, you'll only see it in logs</li>
            </ol>
          </div>
        </div>
      </Card>
    </div>
  )
}
