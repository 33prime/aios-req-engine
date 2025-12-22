'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  FileText,
  Target,
  Zap,
  CheckSquare,
  Settings,
  Play,
  RefreshCw,
  AlertCircle,
  CheckCircle
} from 'lucide-react'
import { getBaselineStatus, listConfirmations, getFeatures, getPrdSections, getVpSteps } from '@/lib/api'
import { BaselineStatus, Confirmation, Feature, PrdSection, VpStep } from '@/types/api'
import SignalInput from '@/components/SignalInput'

export default function ProjectPage() {
  const params = useParams()
  const router = useRouter()
  const projectId = params.projectId as string

  const [baseline, setBaseline] = useState<BaselineStatus | null>(null)
  const [confirmations, setConfirmations] = useState<Confirmation[]>([])
  const [features, setFeatures] = useState<Feature[]>([])
  const [prdSections, setPrdSections] = useState<PrdSection[]>([])
  const [vpSteps, setVpSteps] = useState<VpStep[]>([])
  const [loading, setLoading] = useState(true)
  const [debugInfo, setDebugInfo] = useState<any>({})

  useEffect(() => {
    loadProjectData()
  }, [projectId])

  const loadProjectData = async () => {
    console.log('🔄 Loading project data for:', projectId)
    const startTime = Date.now()

    try {
      setLoading(true)
      const [
        baselineData,
        confirmationsData,
        featuresData,
        prdData,
        vpData
      ] = await Promise.all([
        getBaselineStatus(projectId),
        listConfirmations(projectId, 'open'),
        getFeatures(projectId),
        getPrdSections(projectId),
        getVpSteps(projectId),
      ])

      const loadTime = Date.now() - startTime
      console.log(`✅ Project data loaded in ${loadTime}ms:`, {
        baseline: baselineData,
        confirmations: confirmationsData.confirmations?.length || 0,
        features: featuresData?.length || 0,
        prdSections: prdData?.length || 0,
        vpSteps: vpData?.length || 0,
      })

      setBaseline(baselineData)
      setConfirmations(confirmationsData.confirmations)
      setFeatures(featuresData)
      setPrdSections(prdData)
      setVpSteps(vpData)

      setDebugInfo({
        loadTime,
        dataCounts: {
          confirmations: confirmationsData.confirmations?.length || 0,
          features: featuresData?.length || 0,
          prdSections: prdData?.length || 0,
          vpSteps: vpData?.length || 0,
        },
        baseline: baselineData,
        lastUpdated: new Date().toISOString(),
      })
    } catch (error) {
      console.error('❌ Failed to load project data:', error)
      setDebugInfo((prev: any) => ({ ...prev, error: String(error), lastError: new Date().toISOString() }))
      alert('Failed to load project data')
    } finally {
      setLoading(false)
    }
  }

  const handleBaselineToggle = async () => {
    if (!baseline) return

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}/v1/projects/${projectId}/baseline`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ baseline_ready: !baseline.baseline_ready }),
      })

      if (response.ok) {
        const updated = await response.json()
        setBaseline(updated)
      } else {
        alert('Failed to update baseline status')
      }
    } catch (error) {
      console.error('Failed to toggle baseline:', error)
      alert('Failed to toggle baseline')
    }
  }

  const runAgent = async (agentType: string) => {
    try {
      let response
      switch (agentType) {
        case 'build':
          response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}/v1/state/build`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ project_id: projectId }),
          })
          break
        case 'reconcile':
          response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}/v1/state/reconcile`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ project_id: projectId, include_research: baseline?.baseline_ready }),
          })
          break
        case 'redteam':
          response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}/v1/agents/red-team`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ project_id: projectId, include_research: baseline?.baseline_ready }),
          })
          break
      }

      if (response?.ok) {
        const result = await response.json()
        // Poll job status
        pollJobStatus(result.job_id)
      } else {
        alert(`Failed to run ${agentType} agent`)
      }
    } catch (error) {
      console.error(`Failed to run ${agentType} agent:`, error)
      alert(`Failed to run ${agentType} agent`)
    }
  }

  const pollJobStatus = async (jobId: string) => {
    console.log('🔍 Starting job polling for:', jobId)
    let pollCount = 0
    const maxPolls = 30 // 1 minute max

    const checkStatus = async () => {
      pollCount++
      console.log(`📡 Poll #${pollCount} for job ${jobId}`)

      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}/v1/jobs/${jobId}`)
        if (response.ok) {
          const job = await response.json()
          console.log(`📊 Job status update:`, {
            status: job.status,
            started_at: job.started_at,
            completed_at: job.completed_at,
            error: job.error,
            output: job.output,
          })

          if (job.status === 'completed') {
            console.log('✅ Job completed successfully!')
            alert(`Agent run completed! Output: ${JSON.stringify(job.output, null, 2)}`)
            loadProjectData() // Refresh data
          } else if (job.status === 'failed') {
            console.log('❌ Job failed:', job.error)
            alert(`Agent run failed: ${job.error}`)
          } else if (pollCount >= maxPolls) {
            console.log('⏰ Job polling timeout')
            alert('Job is taking too long. Check server logs.')
          } else {
            console.log('⏳ Job still running, checking again in 2s...')
            // Still running, check again in 2 seconds
            setTimeout(checkStatus, 2000)
          }
        } else {
          console.error(`❌ Job status check failed: ${response.status}`)
          alert(`Failed to check job status: ${response.status}`)
        }
      } catch (error) {
        console.error('❌ Failed to check job status:', error)
        alert(`Job status check failed: ${error}`)
      }
    }
    checkStatus()
  }

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      </div>
    )
  }

  const mvpFeatures = features.filter(f => f.is_mvp)
  const enrichedFeatures = features.filter(f => f.details)
  const enrichedPrdSections = prdSections.filter(s => s.enrichment)
  const enrichedVpSteps = vpSteps.filter(s => s.enrichment)

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Project Dashboard</h1>
            <p className="text-gray-600 mt-1">Project ID: {projectId}</p>
          </div>
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <Settings className="h-5 w-5 text-gray-400" />
              <span className="text-sm text-gray-600">Research Access</span>
              <button
                onClick={handleBaselineToggle}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  baseline?.baseline_ready ? 'bg-green-600' : 'bg-gray-200'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    baseline?.baseline_ready ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
            <button
              onClick={loadProjectData}
              className="btn btn-secondary flex items-center"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </button>
          </div>
        </div>
      </div>

      {/* Signal Input */}
      <SignalInput projectId={projectId} onSignalAdded={loadProjectData} />

      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="card">
          <div className="flex items-center">
            <Target className="h-8 w-8 text-blue-600" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Features</p>
              <p className="text-2xl font-bold text-gray-900">{features.length}</p>
              <p className="text-sm text-gray-500">{mvpFeatures.length} MVP</p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <FileText className="h-8 w-8 text-green-600" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">PRD Sections</p>
              <p className="text-2xl font-bold text-gray-900">{prdSections.length}</p>
              <p className="text-sm text-gray-500">{enrichedPrdSections.length} enriched</p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <Zap className="h-8 w-8 text-purple-600" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">VP Steps</p>
              <p className="text-2xl font-bold text-gray-900">{vpSteps.length}</p>
              <p className="text-sm text-gray-500">{enrichedVpSteps.length} enriched</p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <CheckSquare className="h-8 w-8 text-orange-600" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Confirmations</p>
              <p className="text-2xl font-bold text-gray-900">{confirmations.length}</p>
              <p className="text-sm text-gray-500">open items</p>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <Link href={`/projects/${projectId}/features`} className="card hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Features</h3>
              <p className="text-gray-600 mt-1">Manage product features and requirements</p>
            </div>
            <Target className="h-8 w-8 text-blue-600" />
          </div>
        </Link>

        <Link href={`/projects/${projectId}/prd`} className="card hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">PRD</h3>
              <p className="text-gray-600 mt-1">Product Requirements Document</p>
            </div>
            <FileText className="h-8 w-8 text-green-600" />
          </div>
        </Link>

        <Link href={`/projects/${projectId}/vp`} className="card hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Value Path</h3>
              <p className="text-gray-600 mt-1">Customer journey and value delivery</p>
            </div>
            <Zap className="h-8 w-8 text-purple-600" />
          </div>
        </Link>

        <Link href={`/projects/${projectId}/insights`} className="card hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Insights</h3>
              <p className="text-gray-600 mt-1">Red team analysis and recommendations</p>
            </div>
            <AlertCircle className="h-8 w-8 text-red-600" />
          </div>
        </Link>
      </div>

      {/* Agent Actions */}
      <div className="card mb-8">
        <h3 className="text-lg font-semibold text-gray-900 mb-6">Run Agents</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <button
            onClick={() => runAgent('build')}
            className="btn btn-primary flex items-center justify-center"
          >
            <Play className="h-4 w-4 mr-2" />
            Build State
          </button>
          <button
            onClick={() => runAgent('reconcile')}
            className="btn btn-success flex items-center justify-center"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Reconcile
          </button>
          <button
            onClick={() => runAgent('redteam')}
            className="btn btn-warning flex items-center justify-center"
          >
            <AlertCircle className="h-4 w-4 mr-2" />
            Red Team
          </button>
        </div>
      </div>

      {/* Debug Panel */}
      <div className="card mb-8">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Debug Info</h3>
          <button
            onClick={() => console.log('🔍 Debug Info:', debugInfo)}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            Log to Console
          </button>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="font-medium text-gray-600">Load Time:</span>
            <div className="text-gray-900">{debugInfo.loadTime || 0}ms</div>
          </div>
          <div>
            <span className="font-medium text-gray-600">Features:</span>
            <div className="text-gray-900">{debugInfo.dataCounts?.features || 0}</div>
          </div>
          <div>
            <span className="font-medium text-gray-600">PRD Sections:</span>
            <div className="text-gray-900">{debugInfo.dataCounts?.prdSections || 0}</div>
          </div>
          <div>
            <span className="font-medium text-gray-600">VP Steps:</span>
            <div className="text-gray-900">{debugInfo.dataCounts?.vpSteps || 0}</div>
          </div>
        </div>
        <div className="mt-4 text-xs text-gray-500">
          Last updated: {debugInfo.lastUpdated || 'Never'}
          {debugInfo.error && (
            <div className="text-red-600 mt-1">
              Error: {debugInfo.error}
            </div>
          )}
        </div>
      </div>

      {/* Confirmations */}
      {confirmations.length > 0 && (
        <div className="card">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-gray-900">Open Confirmations</h3>
            <Link href={`/projects/${projectId}/confirmations`} className="btn btn-secondary">
              View All
            </Link>
          </div>
          <div className="space-y-4">
            {confirmations.slice(0, 3).map((confirmation) => (
              <div key={confirmation.id} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h4 className="font-medium text-gray-900">{confirmation.title}</h4>
                    <p className="text-sm text-gray-600 mt-1">{confirmation.ask}</p>
                    <div className="flex items-center mt-2 space-x-4">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        confirmation.priority === 'high' ? 'bg-red-100 text-red-800' :
                        confirmation.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-green-100 text-green-800'
                      }`}>
                        {confirmation.priority}
                      </span>
                      <span className="text-sm text-gray-500">
                        {confirmation.suggested_method}
                      </span>
                    </div>
                  </div>
                  <div className="ml-4">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      {confirmation.kind}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
