/**
 * RequirementsCanvas - Main canvas view for Discovery phase
 *
 * Layout:
 * - Stats micro-bar at top
 * - Story (pitch line)
 * - Actors (personas) row with color indicators
 * - Journey (value path steps with features)
 * - Unmapped Features pool
 * - Detail drawers for personas and VP steps
 */

'use client'

import { useState } from 'react'
import {
  DndContext,
  DragOverlay,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragStartEvent,
  DragEndEvent,
} from '@dnd-kit/core'
import { StoryEditor } from './StoryEditor'
import { PersonaRow } from './PersonaRow'
import { JourneyFlow } from './JourneyFlow'
import { UnmappedFeatures } from './UnmappedFeatures'
import { FeatureChip } from './FeatureChip'
import { PersonaDetailDrawer } from './PersonaDetailDrawer'
import { VpStepDetailDrawer } from './VpStepDetailDrawer'
import type { CanvasData, FeatureSummary } from '@/types/workspace'

interface RequirementsCanvasProps {
  data: CanvasData
  projectId: string
  onUpdatePitchLine: (pitchLine: string) => Promise<void>
  onMapFeatureToStep: (featureId: string, stepId: string | null) => Promise<void>
  onRefresh?: () => void
}

// Auto-assign colors for persona-step indicators
const PERSONA_COLORS = [
  'bg-brand-teal',
  'bg-blue-500',
  'bg-purple-500',
  'bg-amber-500',
  'bg-rose-500',
  'bg-emerald-500',
  'bg-indigo-500',
  'bg-orange-500',
]

export function RequirementsCanvas({
  data,
  projectId,
  onUpdatePitchLine,
  onMapFeatureToStep,
  onRefresh,
}: RequirementsCanvasProps) {
  const [activeFeature, setActiveFeature] = useState<FeatureSummary | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [selectedPersonaId, setSelectedPersonaId] = useState<string | null>(null)
  const [selectedStepId, setSelectedStepId] = useState<string | null>(null)

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor)
  )

  const handleDragStart = (event: DragStartEvent) => {
    const { active } = event
    const feature = data.features.find((f) => f.id === active.id) ||
                    data.unmapped_features.find((f) => f.id === active.id)
    if (feature) {
      setActiveFeature(feature)
    }
  }

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event
    setActiveFeature(null)

    if (!over) return

    const featureId = active.id as string
    const targetId = over.id as string

    // Check if dropping on a step or the unmapped pool
    if (targetId === 'unmapped-pool') {
      await handleMapFeature(featureId, null)
    } else if (targetId.startsWith('step-')) {
      const stepId = targetId.replace('step-', '')
      await handleMapFeature(featureId, stepId)
    }
  }

  const handleMapFeature = async (featureId: string, stepId: string | null) => {
    setIsSaving(true)
    try {
      await onMapFeatureToStep(featureId, stepId)
    } catch (error) {
      console.error('Failed to map feature:', error)
    } finally {
      setIsSaving(false)
    }
  }

  // Stats calculations
  const totalFeatures = data.features.length + data.unmapped_features.length
  const mvpFeatures = [...data.features, ...data.unmapped_features].filter((f) => f.is_mvp).length
  const mappedFeatures = data.features.length
  const mappedPct = totalFeatures > 0 ? Math.round((mappedFeatures / totalFeatures) * 100) : 0
  const readinessPct = Math.round(data.readiness_score)

  // Build persona color map for indicators
  const personaColorMap = new Map<string, string>()
  data.personas.forEach((p, i) => {
    personaColorMap.set(p.id, PERSONA_COLORS[i % PERSONA_COLORS.length])
  })

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="space-y-6">
        {/* Stats Micro-bar */}
        <div className="flex items-center justify-end gap-4 text-[11px] text-ui-supportText">
          <span>Features: <strong className="text-ui-bodyText">{totalFeatures}</strong>{mvpFeatures > 0 && <> (<strong className="text-amber-600">{mvpFeatures} MVP</strong>)</>}</span>
          <span className="w-px h-3 bg-ui-cardBorder" />
          <span>Steps: <strong className="text-ui-bodyText">{data.vp_steps.length}</strong></span>
          <span className="w-px h-3 bg-ui-cardBorder" />
          <span>Mapped: <strong className="text-ui-bodyText">{mappedFeatures}/{totalFeatures}</strong> ({mappedPct}%)</span>
          <span className="w-px h-3 bg-ui-cardBorder" />
          <span>Readiness: <strong className={readinessPct >= 70 ? 'text-green-600' : readinessPct >= 40 ? 'text-amber-600' : 'text-red-600'}>{readinessPct}%</strong></span>
        </div>

        {/* Story Section */}
        <section>
          <StoryEditor
            pitchLine={data.pitch_line || ''}
            onSave={onUpdatePitchLine}
          />
        </section>

        {/* Actors Section */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-3">
              <h2 className="text-section text-ui-headingDark">Actors</h2>
              {/* Persona color dots legend */}
              <div className="flex items-center gap-1">
                {data.personas.map((p) => (
                  <div
                    key={p.id}
                    className={`w-2.5 h-2.5 rounded-full ${personaColorMap.get(p.id)}`}
                    title={p.name}
                  />
                ))}
              </div>
            </div>
            <span className="text-support text-ui-supportText">
              {data.personas.length} persona{data.personas.length !== 1 ? 's' : ''}
            </span>
          </div>
          <PersonaRow
            personas={data.personas}
            onPersonaClick={(id) => setSelectedPersonaId(id)}
          />
        </section>

        {/* Journey Section */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-section text-ui-headingDark">Journey</h2>
            <span className="text-support text-ui-supportText">
              {data.vp_steps.length} step{data.vp_steps.length !== 1 ? 's' : ''}
            </span>
          </div>
          <JourneyFlow
            steps={data.vp_steps}
            isSaving={isSaving}
            onStepClick={(id) => setSelectedStepId(id)}
          />
        </section>

        {/* Unmapped Features */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-section text-ui-headingDark">Unmapped Features</h2>
            <span className="text-support text-ui-supportText">
              {data.unmapped_features.length} feature{data.unmapped_features.length !== 1 ? 's' : ''}
            </span>
          </div>
          <UnmappedFeatures features={data.unmapped_features} />
        </section>
      </div>

      {/* Drag Overlay */}
      <DragOverlay>
        {activeFeature && (
          <FeatureChip
            feature={activeFeature}
            isDragging
          />
        )}
      </DragOverlay>

      {/* Persona Detail Drawer */}
      {selectedPersonaId && (
        <PersonaDetailDrawer
          personaId={selectedPersonaId}
          projectId={projectId}
          canvasData={data}
          onClose={() => setSelectedPersonaId(null)}
        />
      )}

      {/* VP Step Detail Drawer */}
      {selectedStepId && (
        <VpStepDetailDrawer
          stepId={selectedStepId}
          projectId={projectId}
          canvasData={data}
          onClose={() => setSelectedStepId(null)}
        />
      )}
    </DndContext>
  )
}

export default RequirementsCanvas
