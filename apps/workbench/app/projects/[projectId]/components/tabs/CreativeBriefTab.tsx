/**
 * CreativeBriefTab Component
 *
 * Capture UX/design preferences, brand guidelines, and strategic context
 */

'use client'

import { useState, useEffect } from 'react'
import { Card, CardHeader, Button } from '@/components/ui'
import { Save, Plus, Trash2, Palette } from 'lucide-react'
import { getProjectDetails, updateProject } from '@/lib/api'

interface CreativeBriefTabProps {
  projectId: string
}

interface CreativeBrief {
  design_preferences: {
    color_scheme: string
    typography: string
    style_references: string[]
    brand_tone: string
  }
  strategic_context: {
    why_build: string
    why_now: string
    who_to_impress: string
    success_criteria: string[]
  }
  prototype_goals: {
    must_have: string[]
    out_of_scope: string[]
    technical_preferences: string
    timeline_budget: string
  }
}

const EMPTY_BRIEF: CreativeBrief = {
  design_preferences: {
    color_scheme: '',
    typography: '',
    style_references: [],
    brand_tone: '',
  },
  strategic_context: {
    why_build: '',
    why_now: '',
    who_to_impress: '',
    success_criteria: [],
  },
  prototype_goals: {
    must_have: [],
    out_of_scope: [],
    technical_preferences: '',
    timeline_budget: '',
  },
}

export function CreativeBriefTab({ projectId }: CreativeBriefTabProps) {
  const [brief, setBrief] = useState<CreativeBrief>(EMPTY_BRIEF)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [newReference, setNewReference] = useState('')
  const [newCriteria, setNewCriteria] = useState('')
  const [newMustHave, setNewMustHave] = useState('')
  const [newOutOfScope, setNewOutOfScope] = useState('')

  useEffect(() => {
    loadBrief()
  }, [projectId])

  const loadBrief = async () => {
    try {
      setLoading(true)
      const project = await getProjectDetails(projectId)
      const existingBrief = project.metadata?.creative_brief || EMPTY_BRIEF
      setBrief(existingBrief)
    } catch (error) {
      console.error('Failed to load creative brief:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      await updateProject(projectId, {
        metadata: {
          creative_brief: {
            ...brief,
            updated_at: new Date().toISOString(),
          },
        },
      })
      alert('Creative brief saved successfully!')
    } catch (error) {
      console.error('Failed to save creative brief:', error)
      alert('Failed to save creative brief')
    } finally {
      setSaving(false)
    }
  }

  const handleAddItem = (field: keyof CreativeBrief, value: string, subfield: string) => {
    if (!value.trim()) return

    setBrief({
      ...brief,
      [field]: {
        ...brief[field],
        [subfield]: [...(brief[field] as any)[subfield], value.trim()],
      },
    })

    // Clear input
    if (field === 'design_preferences' && subfield === 'style_references') setNewReference('')
    if (field === 'strategic_context' && subfield === 'success_criteria') setNewCriteria('')
    if (field === 'prototype_goals' && subfield === 'must_have') setNewMustHave('')
    if (field === 'prototype_goals' && subfield === 'out_of_scope') setNewOutOfScope('')
  }

  const handleRemoveItem = (field: keyof CreativeBrief, subfield: string, index: number) => {
    setBrief({
      ...brief,
      [field]: {
        ...brief[field],
        [subfield]: (brief[field] as any)[subfield].filter((_: any, i: number) => i !== index),
      },
    })
  }

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-primary"></div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header with save button */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Palette className="h-6 w-6 text-brand-primary" />
          <h1 className="text-2xl font-bold text-ui-bodyText">Creative Brief</h1>
        </div>
        <Button
          variant="primary"
          icon={<Save className="h-4 w-4" />}
          onClick={handleSave}
          loading={saving}
        >
          Save Changes
        </Button>
      </div>

      {/* Design Preferences */}
      <Card>
        <CardHeader title="Design Preferences" subtitle="Visual style, brand tone, and references" />

        <div className="space-y-4">
          {/* Color Scheme */}
          <div>
            <label className="block text-sm font-medium text-ui-bodyText mb-2">
              Color Scheme
            </label>
            <input
              type="text"
              value={brief.design_preferences.color_scheme}
              onChange={(e) => setBrief({
                ...brief,
                design_preferences: { ...brief.design_preferences, color_scheme: e.target.value }
              })}
              className="w-full px-3 py-2 border border-ui-cardBorder rounded-lg"
              placeholder="e.g., Modern blues and grays, warm earth tones"
            />
          </div>

          {/* Typography */}
          <div>
            <label className="block text-sm font-medium text-ui-bodyText mb-2">
              Typography Preferences
            </label>
            <input
              type="text"
              value={brief.design_preferences.typography}
              onChange={(e) => setBrief({
                ...brief,
                design_preferences: { ...brief.design_preferences, typography: e.target.value }
              })}
              className="w-full px-3 py-2 border border-ui-cardBorder rounded-lg"
              placeholder="e.g., Clean sans-serif, Inter or Helvetica"
            />
          </div>

          {/* Brand Tone */}
          <div>
            <label className="block text-sm font-medium text-ui-bodyText mb-2">
              Brand Tone
            </label>
            <textarea
              value={brief.design_preferences.brand_tone}
              onChange={(e) => setBrief({
                ...brief,
                design_preferences: { ...brief.design_preferences, brand_tone: e.target.value }
              })}
              rows={3}
              className="w-full px-3 py-2 border border-ui-cardBorder rounded-lg"
              placeholder="e.g., Professional yet approachable, innovative, trustworthy"
            />
          </div>

          {/* Style References */}
          <div>
            <label className="block text-sm font-medium text-ui-bodyText mb-2">
              Style References (URLs)
            </label>
            <div className="space-y-2">
              {brief.design_preferences.style_references.map((ref, i) => (
                <div key={i} className="flex items-center gap-2">
                  <a
                    href={ref}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1 px-3 py-2 bg-ui-cardBg border border-ui-cardBorder rounded-lg text-sm text-brand-primary hover:underline"
                  >
                    {ref}
                  </a>
                  <button
                    onClick={() => handleRemoveItem('design_preferences', 'style_references', i)}
                    className="p-2 text-ui-supportText hover:text-red-600"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
              <div className="flex gap-2">
                <input
                  type="url"
                  value={newReference}
                  onChange={(e) => setNewReference(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAddItem('design_preferences', newReference, 'style_references')}
                  className="flex-1 px-3 py-2 border border-ui-cardBorder rounded-lg text-sm"
                  placeholder="https://example.com/inspiration"
                />
                <Button
                  onClick={() => handleAddItem('design_preferences', newReference, 'style_references')}
                  variant="secondary"
                  size="sm"
                  icon={<Plus className="h-4 w-4" />}
                >
                  Add
                </Button>
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* Strategic Context */}
      <Card>
        <CardHeader title="Strategic Context" subtitle="Business drivers and goals" />

        <div className="space-y-4">
          {/* Why Build */}
          <div>
            <label className="block text-sm font-medium text-ui-bodyText mb-2">
              Why Build This?
            </label>
            <textarea
              value={brief.strategic_context.why_build}
              onChange={(e) => setBrief({
                ...brief,
                strategic_context: { ...brief.strategic_context, why_build: e.target.value }
              })}
              rows={3}
              className="w-full px-3 py-2 border border-ui-cardBorder rounded-lg"
              placeholder="e.g., Internal efficiency gain, market opportunity, competitive response"
            />
          </div>

          {/* Why Now */}
          <div>
            <label className="block text-sm font-medium text-ui-bodyText mb-2">
              Why Now?
            </label>
            <textarea
              value={brief.strategic_context.why_now}
              onChange={(e) => setBrief({
                ...brief,
                strategic_context: { ...brief.strategic_context, why_now: e.target.value }
              })}
              rows={3}
              className="w-full px-3 py-2 border border-ui-cardBorder rounded-lg"
              placeholder="e.g., Fundraising deadline, market window, customer demand"
            />
          </div>

          {/* Who to Impress */}
          <div>
            <label className="block text-sm font-medium text-ui-bodyText mb-2">
              Who to Impress?
            </label>
            <input
              type="text"
              value={brief.strategic_context.who_to_impress}
              onChange={(e) => setBrief({
                ...brief,
                strategic_context: { ...brief.strategic_context, who_to_impress: e.target.value }
              })}
              className="w-full px-3 py-2 border border-ui-cardBorder rounded-lg"
              placeholder="e.g., Board, investors, key customers, internal stakeholders"
            />
          </div>

          {/* Success Criteria */}
          <div>
            <label className="block text-sm font-medium text-ui-bodyText mb-2">
              Success Criteria
            </label>
            <div className="space-y-2">
              {brief.strategic_context.success_criteria.map((criteria, i) => (
                <div key={i} className="flex items-center gap-2">
                  <div className="flex-1 px-3 py-2 bg-ui-cardBg border border-ui-cardBorder rounded-lg text-sm">
                    {criteria}
                  </div>
                  <button
                    onClick={() => handleRemoveItem('strategic_context', 'success_criteria', i)}
                    className="p-2 text-ui-supportText hover:text-red-600"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newCriteria}
                  onChange={(e) => setNewCriteria(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAddItem('strategic_context', newCriteria, 'success_criteria')}
                  className="flex-1 px-3 py-2 border border-ui-cardBorder rounded-lg text-sm"
                  placeholder="e.g., Get 3 customer pilots signed"
                />
                <Button
                  onClick={() => handleAddItem('strategic_context', newCriteria, 'success_criteria')}
                  variant="secondary"
                  size="sm"
                  icon={<Plus className="h-4 w-4" />}
                >
                  Add
                </Button>
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* Prototype Goals */}
      <Card>
        <CardHeader title="Prototype Goals" subtitle="Scope, constraints, and preferences" />

        <div className="space-y-4">
          {/* Must Have */}
          <div>
            <label className="block text-sm font-medium text-ui-bodyText mb-2">
              Must Have (MVP Features)
            </label>
            <div className="space-y-2">
              {brief.prototype_goals.must_have.map((item, i) => (
                <div key={i} className="flex items-center gap-2">
                  <div className="flex-1 px-3 py-2 bg-green-50 border border-green-200 rounded-lg text-sm">
                    {item}
                  </div>
                  <button
                    onClick={() => handleRemoveItem('prototype_goals', 'must_have', i)}
                    className="p-2 text-ui-supportText hover:text-red-600"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newMustHave}
                  onChange={(e) => setNewMustHave(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAddItem('prototype_goals', newMustHave, 'must_have')}
                  className="flex-1 px-3 py-2 border border-ui-cardBorder rounded-lg text-sm"
                  placeholder="e.g., User authentication, Dashboard view"
                />
                <Button
                  onClick={() => handleAddItem('prototype_goals', newMustHave, 'must_have')}
                  variant="secondary"
                  size="sm"
                  icon={<Plus className="h-4 w-4" />}
                >
                  Add
                </Button>
              </div>
            </div>
          </div>

          {/* Out of Scope */}
          <div>
            <label className="block text-sm font-medium text-ui-bodyText mb-2">
              Explicitly Out of Scope
            </label>
            <div className="space-y-2">
              {brief.prototype_goals.out_of_scope.map((item, i) => (
                <div key={i} className="flex items-center gap-2">
                  <div className="flex-1 px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-sm">
                    {item}
                  </div>
                  <button
                    onClick={() => handleRemoveItem('prototype_goals', 'out_of_scope', i)}
                    className="p-2 text-ui-supportText hover:text-red-600"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newOutOfScope}
                  onChange={(e) => setNewOutOfScope(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAddItem('prototype_goals', newOutOfScope, 'out_of_scope')}
                  className="flex-1 px-3 py-2 border border-ui-cardBorder rounded-lg text-sm"
                  placeholder="e.g., Mobile app, Advanced analytics"
                />
                <Button
                  onClick={() => handleAddItem('prototype_goals', newOutOfScope, 'out_of_scope')}
                  variant="secondary"
                  size="sm"
                  icon={<Plus className="h-4 w-4" />}
                >
                  Add
                </Button>
              </div>
            </div>
          </div>

          {/* Technical Preferences */}
          <div>
            <label className="block text-sm font-medium text-ui-bodyText mb-2">
              Technical Preferences / Constraints
            </label>
            <textarea
              value={brief.prototype_goals.technical_preferences}
              onChange={(e) => setBrief({
                ...brief,
                prototype_goals: { ...brief.prototype_goals, technical_preferences: e.target.value }
              })}
              rows={3}
              className="w-full px-3 py-2 border border-ui-cardBorder rounded-lg"
              placeholder="e.g., Must use React, AWS infrastructure preferred, need mobile-responsive"
            />
          </div>

          {/* Timeline/Budget */}
          <div>
            <label className="block text-sm font-medium text-ui-bodyText mb-2">
              Timeline & Budget Guardrails
            </label>
            <input
              type="text"
              value={brief.prototype_goals.timeline_budget}
              onChange={(e) => setBrief({
                ...brief,
                prototype_goals: { ...brief.prototype_goals, timeline_budget: e.target.value }
              })}
              className="w-full px-3 py-2 border border-ui-cardBorder rounded-lg"
              placeholder="e.g., 6 weeks, $50k budget, demo needed by Q2"
            />
          </div>
        </div>
      </Card>
    </div>
  )
}
