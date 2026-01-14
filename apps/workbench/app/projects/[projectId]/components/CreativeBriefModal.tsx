/**
 * CreativeBriefModal Component
 *
 * Centered modal for capturing design/brand/strategy context
 * Replaces the Creative Brief tab
 */

'use client'

import { useState, useEffect } from 'react'
import { X, Save, Plus, Trash2, Palette } from 'lucide-react'

interface CreativeBriefModalProps {
  projectId: string
  isOpen: boolean
  onClose: () => void
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

export function CreativeBriefModal({ projectId, isOpen, onClose }: CreativeBriefModalProps) {
  const [brief, setBrief] = useState<CreativeBrief>(EMPTY_BRIEF)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [newReference, setNewReference] = useState('')
  const [newCriteria, setNewCriteria] = useState('')
  const [newMustHave, setNewMustHave] = useState('')
  const [newOutOfScope, setNewOutOfScope] = useState('')

  useEffect(() => {
    if (isOpen) {
      loadBrief()
    }
  }, [isOpen, projectId])

  const loadBrief = async () => {
    try {
      setLoading(true)
      const apiBase = process.env.NEXT_PUBLIC_API_BASE || ''
      const response = await fetch(`${apiBase}/v1/projects/${projectId}`)
      if (response.ok) {
        const project = await response.json()
        const existingBrief = project.metadata?.creative_brief || EMPTY_BRIEF
        setBrief(existingBrief)
      }
    } catch (error) {
      console.error('Failed to load creative brief:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      const apiBase = process.env.NEXT_PUBLIC_API_BASE || ''
      const response = await fetch(`${apiBase}/v1/projects/${projectId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          metadata: {
            creative_brief: {
              ...brief,
              updated_at: new Date().toISOString(),
            },
          },
        }),
      })

      if (response.ok) {
        alert('Creative brief saved successfully!')
        onClose()
      } else {
        alert('Failed to save creative brief')
      }
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

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-2xl w-full max-w-3xl max-h-[90vh] flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
            <div className="flex items-center gap-2">
              <Palette className="h-6 w-6 text-brand-primary" />
              <h2 className="text-xl font-bold text-ui-bodyText">Creative Brief</h2>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-4 py-2 bg-brand-primary hover:bg-brand-primaryHover text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                <Save className="h-4 w-4" />
                {saving ? 'Saving...' : 'Save'}
              </button>
              <button
                onClick={onClose}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="h-5 w-5 text-ui-supportText" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto px-6 py-4">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-primary"></div>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Design Preferences */}
                <Section title="Design Preferences" subtitle="Visual style, brand tone, and references">
                  <div className="space-y-4">
                    <InputField
                      label="Color Scheme"
                      value={brief.design_preferences.color_scheme}
                      onChange={(v) => setBrief({
                        ...brief,
                        design_preferences: { ...brief.design_preferences, color_scheme: v }
                      })}
                      placeholder="e.g., Modern blues and grays, warm earth tones"
                    />

                    <InputField
                      label="Typography Preferences"
                      value={brief.design_preferences.typography}
                      onChange={(v) => setBrief({
                        ...brief,
                        design_preferences: { ...brief.design_preferences, typography: v }
                      })}
                      placeholder="e.g., Clean sans-serif, Inter or Helvetica"
                    />

                    <TextareaField
                      label="Brand Tone"
                      value={brief.design_preferences.brand_tone}
                      onChange={(v) => setBrief({
                        ...brief,
                        design_preferences: { ...brief.design_preferences, brand_tone: v }
                      })}
                      placeholder="e.g., Professional yet approachable, innovative, trustworthy"
                      rows={3}
                    />

                    <ListField
                      label="Style References (URLs)"
                      items={brief.design_preferences.style_references}
                      newValue={newReference}
                      onNewValueChange={setNewReference}
                      onAdd={() => handleAddItem('design_preferences', newReference, 'style_references')}
                      onRemove={(i) => handleRemoveItem('design_preferences', 'style_references', i)}
                      placeholder="https://example.com/inspiration"
                      type="url"
                    />
                  </div>
                </Section>

                {/* Strategic Context */}
                <Section title="Strategic Context" subtitle="Business drivers and goals">
                  <div className="space-y-4">
                    <TextareaField
                      label="Why Build This?"
                      value={brief.strategic_context.why_build}
                      onChange={(v) => setBrief({
                        ...brief,
                        strategic_context: { ...brief.strategic_context, why_build: v }
                      })}
                      placeholder="e.g., Internal efficiency gain, market opportunity, competitive response"
                      rows={3}
                    />

                    <TextareaField
                      label="Why Now?"
                      value={brief.strategic_context.why_now}
                      onChange={(v) => setBrief({
                        ...brief,
                        strategic_context: { ...brief.strategic_context, why_now: v }
                      })}
                      placeholder="e.g., Fundraising deadline, market window, customer demand"
                      rows={3}
                    />

                    <InputField
                      label="Who to Impress?"
                      value={brief.strategic_context.who_to_impress}
                      onChange={(v) => setBrief({
                        ...brief,
                        strategic_context: { ...brief.strategic_context, who_to_impress: v }
                      })}
                      placeholder="e.g., Board, investors, key customers, internal stakeholders"
                    />

                    <ListField
                      label="Success Criteria"
                      items={brief.strategic_context.success_criteria}
                      newValue={newCriteria}
                      onNewValueChange={setNewCriteria}
                      onAdd={() => handleAddItem('strategic_context', newCriteria, 'success_criteria')}
                      onRemove={(i) => handleRemoveItem('strategic_context', 'success_criteria', i)}
                      placeholder="e.g., Get 3 customer pilots signed"
                    />
                  </div>
                </Section>

                {/* Prototype Goals */}
                <Section title="Prototype Goals" subtitle="Scope, constraints, and preferences">
                  <div className="space-y-4">
                    <ListField
                      label="Must Have (MVP Features)"
                      items={brief.prototype_goals.must_have}
                      newValue={newMustHave}
                      onNewValueChange={setNewMustHave}
                      onAdd={() => handleAddItem('prototype_goals', newMustHave, 'must_have')}
                      onRemove={(i) => handleRemoveItem('prototype_goals', 'must_have', i)}
                      placeholder="e.g., User authentication, Dashboard view"
                      itemClass="bg-green-50 border-green-200"
                    />

                    <ListField
                      label="Explicitly Out of Scope"
                      items={brief.prototype_goals.out_of_scope}
                      newValue={newOutOfScope}
                      onNewValueChange={setNewOutOfScope}
                      onAdd={() => handleAddItem('prototype_goals', newOutOfScope, 'out_of_scope')}
                      onRemove={(i) => handleRemoveItem('prototype_goals', 'out_of_scope', i)}
                      placeholder="e.g., Mobile app, Advanced analytics"
                      itemClass="bg-red-50 border-red-200"
                    />

                    <TextareaField
                      label="Technical Preferences / Constraints"
                      value={brief.prototype_goals.technical_preferences}
                      onChange={(v) => setBrief({
                        ...brief,
                        prototype_goals: { ...brief.prototype_goals, technical_preferences: v }
                      })}
                      placeholder="e.g., Must use React, AWS infrastructure preferred, need mobile-responsive"
                      rows={3}
                    />

                    <InputField
                      label="Timeline & Budget Guardrails"
                      value={brief.prototype_goals.timeline_budget}
                      onChange={(v) => setBrief({
                        ...brief,
                        prototype_goals: { ...brief.prototype_goals, timeline_budget: v }
                      })}
                      placeholder="e.g., 6 weeks, $50k budget, demo needed by Q2"
                    />
                  </div>
                </Section>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  )
}

// Helper Components

function Section({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <div className="border border-gray-200 rounded-lg p-5">
      <h3 className="text-lg font-semibold text-ui-bodyText mb-1">{title}</h3>
      <p className="text-sm text-ui-supportText mb-4">{subtitle}</p>
      {children}
    </div>
  )
}

function InputField({ label, value, onChange, placeholder }: {
  label: string
  value: string
  onChange: (v: string) => void
  placeholder: string
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-ui-bodyText mb-2">{label}</label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 border border-ui-cardBorder rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-primary"
        placeholder={placeholder}
      />
    </div>
  )
}

function TextareaField({ label, value, onChange, placeholder, rows }: {
  label: string
  value: string
  onChange: (v: string) => void
  placeholder: string
  rows: number
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-ui-bodyText mb-2">{label}</label>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={rows}
        className="w-full px-3 py-2 border border-ui-cardBorder rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-primary"
        placeholder={placeholder}
      />
    </div>
  )
}

function ListField({ label, items, newValue, onNewValueChange, onAdd, onRemove, placeholder, type = 'text', itemClass = 'bg-ui-cardBg border-ui-cardBorder' }: {
  label: string
  items: string[]
  newValue: string
  onNewValueChange: (v: string) => void
  onAdd: () => void
  onRemove: (i: number) => void
  placeholder: string
  type?: string
  itemClass?: string
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-ui-bodyText mb-2">{label}</label>
      <div className="space-y-2">
        {items.map((item, i) => (
          <div key={i} className="flex items-center gap-2">
            {type === 'url' ? (
              <a
                href={item}
                target="_blank"
                rel="noopener noreferrer"
                className={`flex-1 px-3 py-2 border rounded-lg text-sm text-brand-primary hover:underline ${itemClass}`}
              >
                {item}
              </a>
            ) : (
              <div className={`flex-1 px-3 py-2 border rounded-lg text-sm ${itemClass}`}>
                {item}
              </div>
            )}
            <button
              onClick={() => onRemove(i)}
              className="p-2 text-ui-supportText hover:text-red-600"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        ))}
        <div className="flex gap-2">
          <input
            type={type}
            value={newValue}
            onChange={(e) => onNewValueChange(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && onAdd()}
            className="flex-1 px-3 py-2 border border-ui-cardBorder rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-primary"
            placeholder={placeholder}
          />
          <button
            onClick={onAdd}
            className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-ui-bodyText rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
          >
            <Plus className="h-4 w-4" />
            Add
          </button>
        </div>
      </div>
    </div>
  )
}
