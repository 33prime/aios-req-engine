/**
 * ResearchBriefCard Component
 *
 * Displays and allows editing of the research creative brief
 * (client name, industry, website, competitors, etc.)
 */

'use client'

import { useState, useEffect } from 'react'
import { Building2, Globe, Users, Target, CheckCircle, AlertCircle, Edit2, Save, X, Plus, Trash2 } from 'lucide-react'

interface ResearchBriefCardProps {
  projectId: string
  onBriefUpdate?: () => void
}

interface ResearchBrief {
  id?: string
  client_name: string | null
  industry: string | null
  website: string | null
  competitors: string[]
  focus_areas: string[]
  custom_questions: string[]
  completeness_score: number
  field_sources: Record<string, string>
}

const EMPTY_BRIEF: ResearchBrief = {
  client_name: null,
  industry: null,
  website: null,
  competitors: [],
  focus_areas: [],
  custom_questions: [],
  completeness_score: 0,
  field_sources: {},
}

export function ResearchBriefCard({ projectId, onBriefUpdate }: ResearchBriefCardProps) {
  const [brief, setBrief] = useState<ResearchBrief>(EMPTY_BRIEF)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [editForm, setEditForm] = useState<ResearchBrief>(EMPTY_BRIEF)
  const [newCompetitor, setNewCompetitor] = useState('')
  const [newFocusArea, setNewFocusArea] = useState('')

  useEffect(() => {
    loadBrief()
  }, [projectId])

  const loadBrief = async () => {
    try {
      setLoading(true)
      const apiBase = process.env.NEXT_PUBLIC_API_BASE || ''
      const response = await fetch(`${apiBase}/v1/creative-brief?project_id=${projectId}`)
      if (response.ok) {
        const data = await response.json()
        if (data) {
          setBrief(data)
          setEditForm(data)
        }
      }
    } catch (error) {
      console.error('Failed to load research brief:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      const apiBase = process.env.NEXT_PUBLIC_API_BASE || ''
      const response = await fetch(`${apiBase}/v1/creative-brief?project_id=${projectId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_name: editForm.client_name,
          industry: editForm.industry,
          website: editForm.website,
          competitors: editForm.competitors,
          focus_areas: editForm.focus_areas,
          custom_questions: editForm.custom_questions,
        }),
      })

      if (response.ok) {
        const updated = await response.json()
        setBrief(updated)
        setEditing(false)
        onBriefUpdate?.()
      }
    } catch (error) {
      console.error('Failed to save research brief:', error)
    } finally {
      setSaving(false)
    }
  }

  const handleAddCompetitor = () => {
    if (newCompetitor.trim()) {
      setEditForm({
        ...editForm,
        competitors: [...editForm.competitors, newCompetitor.trim()],
      })
      setNewCompetitor('')
    }
  }

  const handleRemoveCompetitor = (index: number) => {
    setEditForm({
      ...editForm,
      competitors: editForm.competitors.filter((_, i) => i !== index),
    })
  }

  const handleAddFocusArea = () => {
    if (newFocusArea.trim()) {
      setEditForm({
        ...editForm,
        focus_areas: [...editForm.focus_areas, newFocusArea.trim()],
      })
      setNewFocusArea('')
    }
  }

  const handleRemoveFocusArea = (index: number) => {
    setEditForm({
      ...editForm,
      focus_areas: editForm.focus_areas.filter((_, i) => i !== index),
    })
  }

  const isComplete = brief.completeness_score >= 0.8
  const progressPercent = Math.round(brief.completeness_score * 100)

  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-ui-cardBorder p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-200 rounded w-1/3"></div>
          <div className="h-4 bg-gray-200 rounded w-1/2"></div>
          <div className="h-4 bg-gray-200 rounded w-2/3"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg border border-ui-cardBorder">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-ui-cardBorder">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${isComplete ? 'bg-green-100' : 'bg-amber-100'}`}>
            {isComplete ? (
              <CheckCircle className="h-5 w-5 text-green-600" />
            ) : (
              <AlertCircle className="h-5 w-5 text-amber-600" />
            )}
          </div>
          <div>
            <h3 className="text-lg font-semibold text-ui-bodyText">Research Brief</h3>
            <p className="text-sm text-ui-supportText">
              {isComplete ? 'Ready for research' : 'Complete to enable research'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Progress indicator */}
          <div className="flex items-center gap-2">
            <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all ${isComplete ? 'bg-green-500' : 'bg-amber-500'}`}
                style={{ width: `${progressPercent}%` }}
              />
            </div>
            <span className="text-sm text-ui-supportText">{progressPercent}%</span>
          </div>

          {editing ? (
            <div className="flex items-center gap-2">
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-3 py-1.5 bg-brand-primary hover:bg-brand-primaryHover text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50 flex items-center gap-1"
              >
                <Save className="h-4 w-4" />
                {saving ? 'Saving...' : 'Save'}
              </button>
              <button
                onClick={() => {
                  setEditing(false)
                  setEditForm(brief)
                }}
                className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="h-4 w-4 text-ui-supportText" />
              </button>
            </div>
          ) : (
            <button
              onClick={() => setEditing(true)}
              className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <Edit2 className="h-4 w-4 text-ui-supportText" />
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="px-6 py-4">
        {editing ? (
          <div className="space-y-4">
            {/* Client Name */}
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-ui-bodyText mb-1">
                  Client Name <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-ui-supportText" />
                  <input
                    type="text"
                    value={editForm.client_name || ''}
                    onChange={(e) => setEditForm({ ...editForm, client_name: e.target.value })}
                    className="w-full pl-10 pr-3 py-2 border border-ui-cardBorder rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-primary"
                    placeholder="e.g., Acme Corp"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-ui-bodyText mb-1">
                  Industry <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <Target className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-ui-supportText" />
                  <input
                    type="text"
                    value={editForm.industry || ''}
                    onChange={(e) => setEditForm({ ...editForm, industry: e.target.value })}
                    className="w-full pl-10 pr-3 py-2 border border-ui-cardBorder rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-primary"
                    placeholder="e.g., HR SaaS"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-ui-bodyText mb-1">
                  Website
                </label>
                <div className="relative">
                  <Globe className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-ui-supportText" />
                  <input
                    type="url"
                    value={editForm.website || ''}
                    onChange={(e) => setEditForm({ ...editForm, website: e.target.value })}
                    className="w-full pl-10 pr-3 py-2 border border-ui-cardBorder rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-primary"
                    placeholder="https://example.com"
                  />
                </div>
              </div>
            </div>

            {/* Competitors */}
            <div>
              <label className="block text-sm font-medium text-ui-bodyText mb-1">
                <Users className="inline h-4 w-4 mr-1" />
                Competitors
              </label>
              <div className="flex flex-wrap gap-2 mb-2">
                {editForm.competitors.map((competitor, i) => (
                  <span key={i} className="inline-flex items-center gap-1 px-3 py-1 bg-gray-100 rounded-full text-sm">
                    {competitor}
                    <button onClick={() => handleRemoveCompetitor(i)} className="hover:text-red-500">
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </span>
                ))}
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newCompetitor}
                  onChange={(e) => setNewCompetitor(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAddCompetitor()}
                  className="flex-1 px-3 py-1.5 border border-ui-cardBorder rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-primary"
                  placeholder="Add competitor..."
                />
                <button
                  onClick={handleAddCompetitor}
                  className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm flex items-center gap-1"
                >
                  <Plus className="h-3 w-3" />
                  Add
                </button>
              </div>
            </div>

            {/* Focus Areas */}
            <div>
              <label className="block text-sm font-medium text-ui-bodyText mb-1">
                <Target className="inline h-4 w-4 mr-1" />
                Focus Areas
              </label>
              <div className="flex flex-wrap gap-2 mb-2">
                {editForm.focus_areas.map((area, i) => (
                  <span key={i} className="inline-flex items-center gap-1 px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-sm">
                    {area}
                    <button onClick={() => handleRemoveFocusArea(i)} className="hover:text-red-500">
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </span>
                ))}
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newFocusArea}
                  onChange={(e) => setNewFocusArea(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAddFocusArea()}
                  className="flex-1 px-3 py-1.5 border border-ui-cardBorder rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-primary"
                  placeholder="Add focus area..."
                />
                <button
                  onClick={handleAddFocusArea}
                  className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm flex items-center gap-1"
                >
                  <Plus className="h-3 w-3" />
                  Add
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-3 gap-6">
            <div>
              <div className="flex items-center gap-2 text-sm text-ui-supportText mb-1">
                <Building2 className="h-4 w-4" />
                Client Name
              </div>
              <div className="font-medium text-ui-bodyText">
                {brief.client_name || <span className="text-ui-supportText italic">Not set</span>}
              </div>
            </div>

            <div>
              <div className="flex items-center gap-2 text-sm text-ui-supportText mb-1">
                <Target className="h-4 w-4" />
                Industry
              </div>
              <div className="font-medium text-ui-bodyText">
                {brief.industry || <span className="text-ui-supportText italic">Not set</span>}
              </div>
            </div>

            <div>
              <div className="flex items-center gap-2 text-sm text-ui-supportText mb-1">
                <Globe className="h-4 w-4" />
                Website
              </div>
              <div className="font-medium text-ui-bodyText">
                {brief.website ? (
                  <a href={brief.website} target="_blank" rel="noopener noreferrer" className="text-brand-primary hover:underline">
                    {brief.website}
                  </a>
                ) : (
                  <span className="text-ui-supportText italic">Not set</span>
                )}
              </div>
            </div>

            {brief.competitors.length > 0 && (
              <div className="col-span-3">
                <div className="flex items-center gap-2 text-sm text-ui-supportText mb-2">
                  <Users className="h-4 w-4" />
                  Competitors
                </div>
                <div className="flex flex-wrap gap-2">
                  {brief.competitors.map((competitor, i) => (
                    <span key={i} className="px-3 py-1 bg-gray-100 rounded-full text-sm">
                      {competitor}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {brief.focus_areas.length > 0 && (
              <div className="col-span-3">
                <div className="flex items-center gap-2 text-sm text-ui-supportText mb-2">
                  <Target className="h-4 w-4" />
                  Focus Areas
                </div>
                <div className="flex flex-wrap gap-2">
                  {brief.focus_areas.map((area, i) => (
                    <span key={i} className="px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-sm">
                      {area}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
