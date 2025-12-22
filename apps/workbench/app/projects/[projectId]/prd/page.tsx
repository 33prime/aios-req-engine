'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import {
  ArrowLeft,
  FileText,
  Play,
  CheckCircle,
  AlertCircle,
  Info,
  ExternalLink
} from 'lucide-react'
import { getPrdSections, getBaselineStatus, enrichPrd, getSignal, getSignalChunks } from '@/lib/api'
import { PrdSection, BaselineStatus, Signal, SignalChunk } from '@/types/api'
import PrdDetailCard from '@/components/PrdDetailCard'

export default function PrdPage() {
  const params = useParams()
  const projectId = params.projectId as string

  const [sections, setSections] = useState<PrdSection[]>([])
  const [baseline, setBaseline] = useState<BaselineStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null)
  const [signalChunks, setSignalChunks] = useState<SignalChunk[]>([])

  useEffect(() => {
    loadData()
  }, [projectId])

  const loadData = async () => {
    try {
      setLoading(true)
      console.log('🔄 Loading PRD sections...')
      const [sectionsData, baselineData] = await Promise.all([
        getPrdSections(projectId),
        getBaselineStatus(projectId),
      ])
      console.log('✅ Loaded PRD sections:', sectionsData.length)
      console.log('✅ Sections data:', sectionsData)
      console.log('✅ Baseline status:', baselineData)
      setSections(sectionsData)
      setBaseline(baselineData)
    } catch (error) {
      console.error('❌ Failed to load PRD sections:', error)
      alert('Failed to load PRD sections')
    } finally {
      setLoading(false)
    }
  }

  const handleEnrichPrd = async () => {
    try {
      console.log('🚀 Starting PRD enrichment...')
      setRunning(true)
      const result = await enrichPrd(projectId, baseline?.baseline_ready)
      console.log('✅ PRD enrichment started:', result)

      // Poll job status and refresh data when complete
      pollJobStatus(result.job_id)
    } catch (error) {
      console.error('❌ Failed to enrich PRD:', error)
      alert('Failed to enrich PRD')
      setRunning(false)
    }
  }

      // Poll job status
      pollJobStatus(result.job_id)
    } catch (error) {
      console.error('❌ Failed to enrich PRD:', error)
      alert('Failed to enrich PRD')
      setRunning(false)
    }
  }

  const pollJobStatus = async (jobId: string) => {
    console.log('🔍 Starting job polling for:', jobId)
    const checkStatus = async () => {
      try {
        console.log('📡 Checking job status...')
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}/v1/jobs/${jobId}`)
        if (response.ok) {
          const job = await response.json()
          console.log('📊 Job status:', job.status, job)

          if (job.status === 'completed') {
            console.log('✅ Job completed!')
            alert('PRD enrichment completed!')
            loadData() // Refresh data
            setRunning(false)
          } else if (job.status === 'failed') {
            console.log('❌ Job failed:', job.error)
            alert(`PRD enrichment failed: ${job.error}`)
            setRunning(false)
          } else {
            console.log('⏳ Job still running, checking again in 2s...')
            // Still running, check again in 2 seconds
            setTimeout(checkStatus, 2000)
          }
        } else {
          console.error('❌ Failed to check job status, response:', response.status)
          setRunning(false)
        }
      } catch (error) {
        console.error('❌ Failed to check job status:', error)
        setRunning(false)
      }
    }
    checkStatus()
  }

  const viewEvidence = async (chunkId: string) => {
    try {
      console.log('🔍 Viewing evidence for chunk:', chunkId)
      const signalId = chunkId.split('-')[0]

      const [signal, chunks] = await Promise.all([
        getSignal(signalId),
        getSignalChunks(signalId)
      ])

      console.log('✅ Loaded evidence:', { signal, chunks: chunks.chunks })
      setSelectedSignal(signal)
      setSignalChunks(chunks.chunks)
    } catch (error) {
      console.error('❌ Failed to load evidence:', error)
      alert('Failed to load evidence details')
    }
  }

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <span className="ml-4 text-gray-600">Loading PRD sections...</span>
        </div>
      </div>
    )
  }

  const enrichedSections = sections.filter(s => s.enrichment)

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
              <h1 className="text-3xl font-bold text-gray-900">PRD Sections</h1>
              <p className="text-gray-600 mt-1">
                {sections.length} sections • {enrichedSections.length} enriched
              </p>
            </div>
          </div>

          <div className="flex space-x-3">
            <button
              onClick={() => {
                console.log('🔄 Manual refresh triggered')
                loadData()
              }}
              className="btn btn-secondary"
            >
              <Info className="h-4 w-4 mr-2" />
              Refresh Data
            </button>
            <button
              onClick={handleEnrichPrd}
              disabled={running}
              className="btn btn-primary"
            >
              {running ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
              ) : (
                <Play className="h-4 w-4 mr-2" />
              )}
              Enrich PRD Sections
            </button>
          </div>
        </div>
      </div>

      {/* Sections List */}
      <div className="space-y-6">
        {sections.map((section) => (
          <PrdDetailCard
            key={section.id}
            section={section}
            onViewEvidence={viewEvidence}
          />
        ))}
      </div>

      {sections.length === 0 && (
        <div className="text-center py-12">
          <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No PRD sections found</h3>
          <p className="text-gray-600">Run the build state agent to extract PRD sections from your signals.</p>
        </div>
      )}

      {/* Evidence Modal */}
      {selectedSignal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-4xl w-full max-h-[80vh] overflow-hidden">
            <div className="p-6 border-b">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">Evidence Source</h3>
                <button
                  onClick={() => {
                    setSelectedSignal(null)
                    setSignalChunks([])
                  }}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ✕
                </button>
              </div>
              <div className="mt-2 text-sm text-gray-600">
                <p><strong>Source:</strong> {selectedSignal.source}</p>
                <p><strong>Type:</strong> {selectedSignal.signal_type}</p>
                <p><strong>Date:</strong> {new Date(selectedSignal.created_at).toLocaleString()}</p>
              </div>
            </div>

            <div className="p-6 overflow-y-auto max-h-96">
              <div className="space-y-4">
                {signalChunks.map((chunk, idx) => (
                  <div key={idx} className="border border-gray-200 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-gray-700">
                        Chunk {chunk.chunk_index + 1}
                      </span>
                      <span className="text-xs text-gray-500">
                        Characters {chunk.start_char}-{chunk.end_char}
                      </span>
                    </div>
                    <p className="text-sm text-gray-700">{chunk.content}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
