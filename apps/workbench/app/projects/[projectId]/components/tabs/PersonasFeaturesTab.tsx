/**
 * PersonasFeaturesTab Component
 *
 * Combined tab for Personas and Features with expandable cards in responsive grids.
 */

'use client'

import React, { useState, useEffect } from 'react'
import {
  Users,
  Target,
  Loader2,
  Filter
} from 'lucide-react'
import { getPersonas, getFeatures, getVpSteps, updateFeatureStatus, updatePersonaStatus, getPersonaCoverage, buildState, type PersonaFeatureCoverage } from '@/lib/api'
import type { Feature, VpStep } from '@/types/api'
import type { Persona } from '@/lib/persona-utils'
import PersonaCard from '@/components/personas/PersonaCard'
import PersonaModal from '@/components/personas/PersonaModal'
import FeatureTable from '@/components/features/FeatureTable'
import { getRelatedFeatures, getRelatedVpSteps } from '@/lib/persona-utils'
import { AlertTriangle, Info, Lightbulb } from 'lucide-react'

type FeatureFilter = 'all' | 'mvp' | 'other'

interface PersonasFeaturesTabProps {
  projectId: string
  isActive?: boolean // Re-fetch when tab becomes active
}

export function PersonasFeaturesTab({ projectId, isActive = true }: PersonasFeaturesTabProps) {
  // Data state
  const [personas, setPersonas] = useState<Persona[]>([])
  const [features, setFeatures] = useState<Feature[]>([])
  const [vpSteps, setVpSteps] = useState<VpStep[]>([])
  const [loading, setLoading] = useState(true)

  // View state
  const [featureFilter, setFeatureFilter] = useState<FeatureFilter>('all')
  const [selectedPersona, setSelectedPersona] = useState<Persona | null>(null)
  const [featureCoverage, setFeatureCoverage] = useState<PersonaFeatureCoverage | null>(null)
  const [coverageLoading, setCoverageLoading] = useState(false)

  // Refresh data when tab becomes active or project changes
  useEffect(() => {
    if (isActive) {
      loadData()
    }
  }, [projectId, isActive])

  const loadData = async () => {
    try {
      setLoading(true)
      const [personasData, featuresData, vpStepsData] = await Promise.all([
        getPersonas(projectId),
        getFeatures(projectId),
        getVpSteps(projectId)
      ])
      setPersonas(personasData || [])
      setFeatures(featuresData || [])
      setVpSteps(vpStepsData || [])
    } catch (error) {
      console.error('Failed to load data:', error)
    } finally {
      setLoading(false)
    }
  }

  // Handle persona selection and fetch coverage
  const handlePersonaSelect = async (persona: Persona) => {
    setSelectedPersona(persona)
    setFeatureCoverage(null)

    if (persona.id) {
      try {
        setCoverageLoading(true)
        const coverage = await getPersonaCoverage(persona.id)
        setFeatureCoverage(coverage)
      } catch (error) {
        console.error('Failed to load persona coverage:', error)
      } finally {
        setCoverageLoading(false)
      }
    }
  }

  // Handle modal close
  const handleModalClose = () => {
    setSelectedPersona(null)
    setFeatureCoverage(null)
  }

  // Handle feature confirmation
  const handleFeatureConfirmation = async (featureId: string, newStatus: string) => {
    // Optimistic update
    setFeatures(prev =>
      prev.map(f =>
        f.id === featureId ? { ...f, confirmation_status: newStatus as any, status: newStatus } : f
      )
    )

    try {
      await updateFeatureStatus(featureId, newStatus)
    } catch (error) {
      // Revert on error
      console.error('Failed to update feature status:', error)
      loadData()
      throw error
    }
  }

  // Handle persona confirmation
  const handlePersonaConfirmation = async (personaId: string, newStatus: string) => {
    // Optimistic update
    setPersonas(prev =>
      prev.map(p =>
        p.id === personaId ? { ...p, confirmation_status: newStatus as any } : p
      )
    )
    // Update selectedPersona too if it's the one being changed
    if (selectedPersona?.id === personaId) {
      setSelectedPersona(prev => prev ? { ...prev, confirmation_status: newStatus as any } : null)
    }

    try {
      await updatePersonaStatus(personaId, newStatus)
    } catch (error) {
      console.error('Failed to update persona status:', error)
      loadData()
      throw error
    }
  }

  // Handle feature delete
  const handleFeatureDelete = (featureId: string) => {
    setFeatures(prev => prev.filter(f => f.id !== featureId))
  }

  // Handle persona delete
  const handlePersonaDelete = (personaId: string) => {
    setPersonas(prev => prev.filter(p => p.id !== personaId))
    setSelectedPersona(null)
  }

  // Handle bulk rebuild (triggers build_state)
  const handleBulkRebuild = async () => {
    try {
      await buildState(projectId)
      await loadData() // Refresh data after rebuild
    } catch (error) {
      console.error('Failed to rebuild state:', error)
    }
  }

  // Filter features
  const filteredFeatures = features.filter(f => {
    if (featureFilter === 'mvp') return f.is_mvp
    if (featureFilter === 'other') return !f.is_mvp
    return true
  })

  // Calculate insights
  const getInsights = () => {
    const insights: { type: 'warning' | 'info' | 'tip'; message: string }[] = []

    // Check for features without evidence
    const noEvidenceFeatures = features.filter(f => !f.evidence || f.evidence.length === 0)
    if (noEvidenceFeatures.length > 0) {
      insights.push({
        type: 'warning',
        message: `${noEvidenceFeatures.length} feature${noEvidenceFeatures.length !== 1 ? 's' : ''} lack${noEvidenceFeatures.length === 1 ? 's' : ''} evidence. Consider adding client quotes or research to support them.`
      })
    }

    // Check for unenriched features
    const unenrichedFeatures = features.filter(f => !(f as any).enrichment_status || (f as any).enrichment_status === 'none')
    if (unenrichedFeatures.length > 0 && features.length > 0) {
      insights.push({
        type: 'tip',
        message: `${unenrichedFeatures.length} feature${unenrichedFeatures.length !== 1 ? 's' : ''} can be enriched with detailed specifications. Ask the AI assistant to "enrich features".`
      })
    }

    // Check confirmation status
    const draftFeatures = features.filter(f => !f.confirmation_status || f.confirmation_status === 'ai_generated')
    if (draftFeatures.length > 0 && features.length > 0) {
      insights.push({
        type: 'info',
        message: `${draftFeatures.length} of ${features.length} features are still AI drafts. Review and confirm them to solidify your requirements.`
      })
    }

    return insights
  }

  const insights = getInsights()

  // MVP and non-MVP counts
  const mvpCount = features.filter(f => f.is_mvp).length
  const otherCount = features.length - mvpCount

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-3" />
          <p className="text-gray-500">Loading personas and features...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Personas & Features</h1>
          <p className="text-gray-500 text-sm mt-1">
            {personas.length} persona{personas.length !== 1 ? 's' : ''} • {features.length} feature{features.length !== 1 ? 's' : ''}
          </p>
        </div>
      </div>

      {/* AI Insights */}
      {insights.length > 0 && (
        <div className="mb-6 space-y-3">
          {insights.slice(0, 2).map((insight, idx) => {
            const styles = {
              warning: { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-800', icon: AlertTriangle },
              info: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-800', icon: Info },
              tip: { bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-800', icon: Lightbulb },
            }
            const style = styles[insight.type]
            const Icon = style.icon
            return (
              <div key={idx} className={`flex items-start gap-3 px-4 py-3 rounded-lg border ${style.bg} ${style.border}`}>
                <Icon className={`h-5 w-5 ${style.text} flex-shrink-0 mt-0.5`} />
                <p className={`text-sm ${style.text}`}>{insight.message}</p>
              </div>
            )
          })}
        </div>
      )}

      {/* Cards View */}
      <div className="space-y-8">
        {/* Personas Section */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Users className="h-5 w-5 text-gray-600" />
              <h2 className="text-lg font-semibold text-gray-900">Personas</h2>
              <span className="text-sm text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
                {personas.length}
              </span>
            </div>
          </div>

          {personas.length === 0 ? (
            <div className="text-center py-12 bg-gray-50 rounded-lg border-2 border-dashed border-gray-200">
              <Users className="h-12 w-12 text-gray-300 mx-auto mb-3" />
              <h3 className="text-gray-900 font-medium mb-1">No personas yet</h3>
              <p className="text-gray-500 text-sm mb-4">
                Personas help you understand who will use your product.
              </p>
              <p className="text-blue-600 text-sm">
                Ask the AI assistant to create personas from your project description.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {personas.map(persona => (
                <PersonaCard
                  key={persona.id}
                  persona={persona}
                  onClick={() => handlePersonaSelect(persona)}
                />
              ))}
            </div>
          )}
        </section>

        {/* Features Section */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Target className="h-5 w-5 text-gray-600" />
              <h2 className="text-lg font-semibold text-gray-900">Features</h2>
              <span className="text-sm text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
                {features.length}
              </span>
            </div>

            {/* Feature Filters */}
            {features.length > 0 && (
              <div className="flex items-center gap-2">
                <Filter className="h-4 w-4 text-gray-400" />
                <div className="flex items-center gap-1 bg-gray-100 p-0.5 rounded-lg">
                  <button
                    onClick={() => setFeatureFilter('all')}
                    className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                      featureFilter === 'all'
                        ? 'bg-white text-gray-900 shadow-sm'
                        : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    All ({features.length})
                  </button>
                  <button
                    onClick={() => setFeatureFilter('mvp')}
                    className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                      featureFilter === 'mvp'
                        ? 'bg-white text-gray-900 shadow-sm'
                        : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    MVP ({mvpCount})
                  </button>
                  <button
                    onClick={() => setFeatureFilter('other')}
                    className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                      featureFilter === 'other'
                        ? 'bg-white text-gray-900 shadow-sm'
                        : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    Later ({otherCount})
                  </button>
                </div>
              </div>
            )}
          </div>

          {features.length === 0 ? (
            <div className="text-center py-12 bg-gray-50 rounded-lg border-2 border-dashed border-gray-200">
              <Target className="h-12 w-12 text-gray-300 mx-auto mb-3" />
              <h3 className="text-gray-900 font-medium mb-1">No features yet</h3>
              <p className="text-gray-500 text-sm mb-4">
                Features describe what your product will do.
              </p>
              <p className="text-blue-600 text-sm">
                Ask the AI assistant to extract features from your requirements.
              </p>
            </div>
          ) : (
            <FeatureTable
              features={filteredFeatures}
              onConfirmationChange={handleFeatureConfirmation}
              onDelete={handleFeatureDelete}
              onBulkRebuild={handleBulkRebuild}
            />
          )}
        </section>
      </div>

      {/* Persona Modal */}
      <PersonaModal
        persona={selectedPersona}
        relatedFeatures={selectedPersona ? getRelatedFeatures(selectedPersona, features) : []}
        relatedVpSteps={selectedPersona ? getRelatedVpSteps(selectedPersona, vpSteps) : []}
        featureCoverage={featureCoverage || undefined}
        isOpen={selectedPersona !== null}
        onClose={handleModalClose}
        onConfirmationChange={handlePersonaConfirmation}
        onDelete={handlePersonaDelete}
        onBulkRebuild={handleBulkRebuild}
      />
    </div>
  )
}

export default PersonasFeaturesTab
