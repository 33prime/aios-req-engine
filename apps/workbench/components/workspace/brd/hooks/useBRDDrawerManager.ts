import { useState, useCallback } from 'react'
import type {
  BRDWorkspaceData,
  StakeholderBRDSummary,
  PersonaBRDSummary,
  ConstraintItem,
  FeatureBRDSummary,
  BusinessDriver,
} from '@/types/workspace'

export function useBRDDrawerManager(data: BRDWorkspaceData | null) {
  // Impact Preview (delete confirmation)
  const [impactPreview, setImpactPreview] = useState<{
    open: boolean
    entityType: string
    entityId: string
    entityName: string
    onDelete: () => void
  }>({ open: false, entityType: '', entityId: '', entityName: '', onDelete: () => {} })

  const showImpactPreview = useCallback((entityType: string, entityId: string, entityName: string, onDelete: () => void) => {
    setImpactPreview({ open: true, entityType, entityId, entityName, onDelete })
  }, [])

  // Stakeholder Detail Drawer
  const [stakeholderDrawer, setStakeholderDrawer] = useState<{
    open: boolean
    stakeholder: StakeholderBRDSummary | null
  }>({ open: false, stakeholder: null })

  // Confidence Drawer
  const [confidenceDrawer, setConfidenceDrawer] = useState<{
    open: boolean
    entityType: string
    entityId: string
    entityName: string
    initialStatus?: string | null
  }>({ open: false, entityType: '', entityId: '', entityName: '' })

  // Workflow Step Detail Drawer
  const [stepDetailDrawer, setStepDetailDrawer] = useState<{
    open: boolean
    stepId: string
  }>({ open: false, stepId: '' })

  // Workflow Detail Drawer
  const [workflowDetailDrawer, setWorkflowDetailDrawer] = useState<{
    open: boolean
    workflowId: string
  }>({ open: false, workflowId: '' })

  // Entity-Specific Drawers
  const [personaDrawer, setPersonaDrawer] = useState<{
    open: boolean; persona: PersonaBRDSummary | null
  }>({ open: false, persona: null })

  const [constraintDrawer, setConstraintDrawer] = useState<{
    open: boolean; constraint: ConstraintItem | null
  }>({ open: false, constraint: null })

  const [featureDrawer, setFeatureDrawer] = useState<{
    open: boolean; feature: FeatureBRDSummary | null
  }>({ open: false, feature: null })

  const [driverDrawer, setDriverDrawer] = useState<{
    open: boolean; driverId: string; driverType: 'pain' | 'goal' | 'kpi'; initialData: BusinessDriver | null
  }>({ open: false, driverId: '', driverType: 'pain', initialData: null })

  // Vision Detail Drawer
  const [visionDrawer, setVisionDrawer] = useState(false)
  const [clientIntelDrawer, setClientIntelDrawer] = useState(false)

  // Data Entity Detail Drawer
  const [dataEntityDrawer, setDataEntityDrawer] = useState<{
    open: boolean
    entityId: string
  }>({ open: false, entityId: '' })

  // Close all drawers
  const closeAllDrawers = useCallback(() => {
    setStakeholderDrawer({ open: false, stakeholder: null })
    setStepDetailDrawer({ open: false, stepId: '' })
    setWorkflowDetailDrawer({ open: false, workflowId: '' })
    setConfidenceDrawer((prev) => ({ ...prev, open: false }))
    setPersonaDrawer({ open: false, persona: null })
    setConstraintDrawer({ open: false, constraint: null })
    setFeatureDrawer({ open: false, feature: null })
    setDriverDrawer({ open: false, driverId: '', driverType: 'pain', initialData: null })
    setVisionDrawer(false)
    setClientIntelDrawer(false)
    setDataEntityDrawer({ open: false, entityId: '' })
  }, [])

  // Route entity click to the appropriate drawer
  const handleOpenConfidence = useCallback((entityType: string, entityId: string, entityName: string, status?: string | null) => {
    if (!data) return

    if (entityType === 'workflow') {
      closeAllDrawers()
      setWorkflowDetailDrawer({ open: true, workflowId: entityId })
      return
    }
    if (entityType === 'business_driver') {
      const allDrivers = [
        ...data.business_context.pain_points.map(d => ({ ...d, _type: 'pain' as const })),
        ...data.business_context.goals.map(d => ({ ...d, _type: 'goal' as const })),
        ...data.business_context.success_metrics.map(d => ({ ...d, _type: 'kpi' as const })),
      ]
      const driver = allDrivers.find(d => d.id === entityId)
      if (driver) {
        closeAllDrawers()
        setDriverDrawer({ open: true, driverId: entityId, driverType: driver._type, initialData: driver })
      }
      return
    }
    if (entityType === 'persona') {
      const persona = data.actors.find(a => a.id === entityId)
      if (persona) {
        closeAllDrawers()
        setPersonaDrawer({ open: true, persona })
        return
      }
    }
    if (entityType === 'constraint') {
      const constraint = data.constraints.find(c => c.id === entityId)
      if (constraint) {
        closeAllDrawers()
        setConstraintDrawer({ open: true, constraint })
        return
      }
    }
    if (entityType === 'feature') {
      const allFeatures = [
        ...data.requirements.must_have,
        ...data.requirements.should_have,
        ...data.requirements.could_have,
        ...data.requirements.out_of_scope,
      ]
      const feature = allFeatures.find(f => f.id === entityId)
      if (feature) {
        closeAllDrawers()
        setFeatureDrawer({ open: true, feature })
        return
      }
    }
    if (entityType === 'data_entity') {
      closeAllDrawers()
      setDataEntityDrawer({ open: true, entityId })
      return
    }
    if (entityType === 'stakeholder') {
      const stakeholder = data.stakeholders.find(s => s.id === entityId)
      if (stakeholder) {
        closeAllDrawers()
        setStakeholderDrawer({ open: true, stakeholder })
        return
      }
    }
    // Fallback to generic confidence drawer
    closeAllDrawers()
    setConfidenceDrawer({ open: true, entityType, entityId, entityName, initialStatus: status })
  }, [data, closeAllDrawers])

  const handleViewStepDetail = useCallback((stepId: string) => {
    setStakeholderDrawer({ open: false, stakeholder: null })
    setConfidenceDrawer((prev) => ({ ...prev, open: false }))
    setWorkflowDetailDrawer({ open: false, workflowId: '' })
    setStepDetailDrawer({ open: true, stepId })
  }, [])

  const handleViewWorkflowDetail = useCallback((workflowId: string) => {
    setStakeholderDrawer({ open: false, stakeholder: null })
    setConfidenceDrawer((prev) => ({ ...prev, open: false }))
    setStepDetailDrawer({ open: false, stepId: '' })
    setWorkflowDetailDrawer({ open: true, workflowId })
  }, [])

  const handleOpenVisionDetail = useCallback(() => {
    setStakeholderDrawer({ open: false, stakeholder: null })
    setConfidenceDrawer((prev) => ({ ...prev, open: false }))
    setStepDetailDrawer({ open: false, stepId: '' })
    setWorkflowDetailDrawer({ open: false, workflowId: '' })
    setClientIntelDrawer(false)
    setVisionDrawer(true)
  }, [])

  const handleOpenBackgroundDetail = useCallback(() => {
    setStakeholderDrawer({ open: false, stakeholder: null })
    setConfidenceDrawer((prev) => ({ ...prev, open: false }))
    setStepDetailDrawer({ open: false, stepId: '' })
    setWorkflowDetailDrawer({ open: false, workflowId: '' })
    setVisionDrawer(false)
    setClientIntelDrawer(true)
  }, [])

  const handleOpenDataEntityDetail = useCallback((entityId: string) => {
    setStakeholderDrawer({ open: false, stakeholder: null })
    setConfidenceDrawer((prev) => ({ ...prev, open: false }))
    setStepDetailDrawer({ open: false, stepId: '' })
    setWorkflowDetailDrawer({ open: false, workflowId: '' })
    setVisionDrawer(false)
    setClientIntelDrawer(false)
    setDataEntityDrawer({ open: true, entityId })
  }, [])

  return {
    // State
    impactPreview,
    setImpactPreview,
    stakeholderDrawer,
    setStakeholderDrawer,
    confidenceDrawer,
    setConfidenceDrawer,
    stepDetailDrawer,
    setStepDetailDrawer,
    workflowDetailDrawer,
    setWorkflowDetailDrawer,
    personaDrawer,
    setPersonaDrawer,
    constraintDrawer,
    setConstraintDrawer,
    featureDrawer,
    setFeatureDrawer,
    driverDrawer,
    setDriverDrawer,
    visionDrawer,
    setVisionDrawer,
    clientIntelDrawer,
    setClientIntelDrawer,
    dataEntityDrawer,
    setDataEntityDrawer,
    // Handlers
    showImpactPreview,
    closeAllDrawers,
    handleOpenConfidence,
    handleViewStepDetail,
    handleViewWorkflowDetail,
    handleOpenVisionDetail,
    handleOpenBackgroundDetail,
    handleOpenDataEntityDetail,
  }
}
