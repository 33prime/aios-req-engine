'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import {
  ArrowLeft,
  Target,
  Play,
  CheckCircle,
  AlertCircle,
  Info,
  ExternalLink
} from 'lucide-react'
import { getFeatures, getBaselineStatus, enrichFeatures } from '@/lib/api'
import { Feature, BaselineStatus } from '@/types/api'

export default function FeaturesPage() {
  const params = useParams()
  const projectId = params.projectId as string

  const [features, setFeatures] = useState<Feature[]>([])
  const [baseline, setBaseline] = useState<BaselineStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)

  useEffect(() => {
    loadData()
  }, [projectId])

  const loadData = async () => {
    try {
      setLoading(true)
      const [featuresData, baselineData] = await Promise.all([
        getFeatures(projectId),
        getBaselineStatus(projectId),
      ])
      setFeatures(featuresData)
      setBaseline(baselineData)
    } catch (error) {
      console.error('Failed to load features:', error)
      alert('Failed to load features')
    } finally {
      setLoading(false)
    }
  }

  const handleEnrichFeatures = async (onlyMvp = false) => {
    try {
      setRunning(true)
      const result = await enrichFeatures(projectId, {
        onlyMvp,
        includeResearch: baseline?.baseline_ready,
      })

      // Poll job status
      pollJobStatus(result.job_id)
    } catch (error) {
      console.error('Failed to enrich features:', error)
      alert('Failed to enrich features')
      setRunning(false)
    }
  }

  const pollJobStatus = async (jobId: string) => {
    const checkStatus = async () => {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}/v1/jobs/${jobId}`)
        if (response.ok) {
          const job = await response.json()
          if (job.status === 'completed') {
            alert('Feature enrichment completed!')
            loadData() // Refresh data
            setRunning(false)
          } else if (job.status === 'failed') {
            alert(`Feature enrichment failed: ${job.error}`)
            setRunning(false)
          } else {
            // Still running, check again in 2 seconds
            setTimeout(checkStatus, 2000)
          }
        }
      } catch (error) {
        console.error('Failed to check job status:', error)
        setRunning(false)
      }
    }
    checkStatus()
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'confirmed_client':
        return 'bg-green-100 text-green-800'
      case 'confirmed_consultant':
        return 'bg-blue-100 text-blue-800'
      case 'needs_confirmation':
        return 'bg-yellow-100 text-yellow-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getConfidenceColor = (confidence: string) => {
    switch (confidence) {
      case 'high':
        return 'text-green-600'
      case 'medium':
        return 'text-yellow-600'
      case 'low':
        return 'text-red-600'
      default:
        return 'text-gray-600'
    }
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

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Link href={`/projects/${projectId}`} className="btn btn-secondary">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Dashboard
            </Link>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Features</h1>
              <p className="text-gray-600 mt-1">
                {features.length} features • {mvpFeatures.length} MVP • {enrichedFeatures.length} enriched
              </p>
            </div>
          </div>

          <div className="flex space-x-4">
            <button
              onClick={() => handleEnrichFeatures(true)}
              disabled={running}
              className="btn btn-primary"
            >
              {running ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
              ) : (
                <Play className="h-4 w-4 mr-2" />
              )}
              Enrich MVP Features
            </button>
            <button
              onClick={() => handleEnrichFeatures(false)}
              disabled={running}
              className="btn btn-secondary"
            >
              {running ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600 mr-2"></div>
              ) : (
                <Play className="h-4 w-4 mr-2" />
              )}
              Enrich All Features
            </button>
          </div>
        </div>
      </div>

      {/* Features Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {features.map((feature) => (
          <div key={feature.id} className="card">
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1">
                <div className="flex items-center space-x-2 mb-2">
                  <h3 className="text-lg font-semibold text-gray-900">{feature.name}</h3>
                  {feature.is_mvp && (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      MVP
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-600 mb-2">{feature.category}</p>
                <div className="flex items-center space-x-4 mb-3">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(feature.status)}`}>
                    {feature.status}
                  </span>
                  <span className={`text-sm font-medium ${getConfidenceColor(feature.confidence)}`}>
                    {feature.confidence} confidence
                  </span>
                </div>
              </div>
              <Target className="h-6 w-6 text-blue-600 flex-shrink-0" />
            </div>

            {/* Enrichment Details */}
            {feature.details && (
              <div className="border-t border-gray-200 pt-4">
                <div className="flex items-center mb-3">
                  <Info className="h-4 w-4 text-blue-600 mr-2" />
                  <span className="text-sm font-medium text-gray-700">AI Enrichment</span>
                </div>

                <div className="space-y-3">
                  {feature.details.summary && (
                    <div>
                      <p className="text-sm text-gray-600">{feature.details.summary}</p>
                    </div>
                  )}

                  {feature.details.business_rules && feature.details.business_rules.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-1">Business Rules</h4>
                      <ul className="text-sm text-gray-600 space-y-1">
                        {feature.details.business_rules.slice(0, 2).map((rule: any, idx: number) => (
                          <li key={idx} className="flex items-start">
                            <CheckCircle className="h-3 w-3 text-green-600 mr-2 mt-0.5 flex-shrink-0" />
                            <span className="text-xs">{rule.title}</span>
                          </li>
                        ))}
                        {feature.details.business_rules.length > 2 && (
                          <li className="text-xs text-gray-500">
                            +{feature.details.business_rules.length - 2} more rules
                          </li>
                        )}
                      </ul>
                    </div>
                  )}

                  {feature.details.risks && feature.details.risks.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-1">Risks</h4>
                      <ul className="text-sm text-gray-600 space-y-1">
                        {feature.details.risks.slice(0, 2).map((risk: any, idx: number) => (
                          <li key={idx} className="flex items-start">
                            <AlertCircle className={`h-3 w-3 mr-2 mt-0.5 flex-shrink-0 ${
                              risk.severity === 'high' ? 'text-red-600' :
                              risk.severity === 'medium' ? 'text-yellow-600' : 'text-green-600'
                            }`} />
                            <span className="text-xs">{risk.title}</span>
                          </li>
                        ))}
                        {feature.details.risks.length > 2 && (
                          <li className="text-xs text-gray-500">
                            +{feature.details.risks.length - 2} more risks
                          </li>
                        )}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Evidence */}
            {feature.evidence && feature.evidence.length > 0 && (
              <div className="border-t border-gray-200 pt-4 mt-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">
                    {feature.evidence.length} evidence item{feature.evidence.length !== 1 ? 's' : ''}
                  </span>
                  <button className="text-sm text-blue-600 hover:text-blue-800 flex items-center">
                    View <ExternalLink className="h-3 w-3 ml-1" />
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {features.length === 0 && (
        <div className="text-center py-12">
          <Target className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No features found</h3>
          <p className="text-gray-600">Run the build state agent to extract features from your signals.</p>
        </div>
      )}
    </div>
  )
}
