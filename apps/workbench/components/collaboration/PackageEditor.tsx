/**
 * PackageEditor Component
 *
 * Allows editing questions and action items before sending a package.
 * Uses drag-and-drop for reordering and inline editing.
 */

'use client'

import React, { useState } from 'react'
import {
  MessageSquare,
  FileText,
  Sparkles,
  User,
  Lightbulb,
  GripVertical,
  Trash2,
  Plus,
  Save,
  X,
  ArrowLeft,
} from 'lucide-react'
import type {
  ClientPackage,
  SynthesizedQuestion,
  ActionItem,
} from '@/types/api'

interface PackageEditorProps {
  package_: ClientPackage
  onSave: (updates: {
    questions?: Partial<SynthesizedQuestion>[]
    action_items?: Partial<ActionItem>[]
  }) => Promise<void>
  onCancel: () => void
  isSaving?: boolean
}

export function PackageEditor({
  package_,
  onSave,
  onCancel,
  isSaving = false,
}: PackageEditorProps) {
  const [questions, setQuestions] = useState<Partial<SynthesizedQuestion>[]>(
    package_.questions.map((q) => ({ ...q }))
  )
  const [actionItems, setActionItems] = useState<Partial<ActionItem>[]>(
    package_.action_items.map((item) => ({ ...item }))
  )
  const [hasChanges, setHasChanges] = useState(false)

  // Question handlers
  const updateQuestion = (index: number, updates: Partial<SynthesizedQuestion>) => {
    const newQuestions = [...questions]
    newQuestions[index] = { ...newQuestions[index], ...updates }
    setQuestions(newQuestions)
    setHasChanges(true)
  }

  const removeQuestion = (index: number) => {
    setQuestions(questions.filter((_, i) => i !== index))
    setHasChanges(true)
  }

  const addQuestion = () => {
    setQuestions([
      ...questions,
      {
        question_text: '',
        hint: '',
        suggested_answerer: '',
        covers_items: [],
      },
    ])
    setHasChanges(true)
  }

  const moveQuestion = (fromIndex: number, toIndex: number) => {
    const newQuestions = [...questions]
    const [moved] = newQuestions.splice(fromIndex, 1)
    newQuestions.splice(toIndex, 0, moved)
    setQuestions(newQuestions)
    setHasChanges(true)
  }

  // Action item handlers
  const updateActionItem = (index: number, updates: Partial<ActionItem>) => {
    const newItems = [...actionItems]
    newItems[index] = { ...newItems[index], ...updates }
    setActionItems(newItems)
    setHasChanges(true)
  }

  const removeActionItem = (index: number) => {
    setActionItems(actionItems.filter((_, i) => i !== index))
    setHasChanges(true)
  }

  const addActionItem = () => {
    setActionItems([
      ...actionItems,
      {
        title: '',
        description: '',
        item_type: 'document',
        hint: '',
      },
    ])
    setHasChanges(true)
  }

  // Save handler
  const handleSave = async () => {
    await onSave({
      questions: questions.map((q, i) => ({
        ...q,
        sequence_order: i,
      })),
      action_items: actionItems.map((item, i) => ({
        ...item,
        sequence_order: i,
      })),
    })
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6 pb-4 border-b border-gray-100">
        <div className="flex items-center gap-3">
          <button
            onClick={onCancel}
            className="p-1.5 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <h3 className="text-lg font-semibold text-gray-900">Edit Package</h3>
          {hasChanges && (
            <span className="text-xs px-2 py-0.5 bg-amber-100 text-amber-700 rounded-full">
              Unsaved changes
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-gray-600 hover:text-gray-900 text-sm font-medium"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving || !hasChanges}
            className="inline-flex items-center gap-2 px-4 py-2 bg-[#009b87] text-white text-sm font-medium rounded-lg hover:bg-[#008775] disabled:opacity-50 transition-colors"
          >
            <Save className="w-4 h-4" />
            {isSaving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>

      {/* Questions Section */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h4 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-[#009b87]" />
            Questions ({questions.length})
          </h4>
          <button
            onClick={addQuestion}
            className="inline-flex items-center gap-1 text-sm text-[#009b87] hover:underline"
          >
            <Plus className="w-4 h-4" />
            Add Question
          </button>
        </div>

        <div className="space-y-4">
          {questions.map((question, index) => (
            <QuestionEditor
              key={index}
              question={question}
              index={index}
              onChange={(updates) => updateQuestion(index, updates)}
              onRemove={() => removeQuestion(index)}
              onMoveUp={index > 0 ? () => moveQuestion(index, index - 1) : undefined}
              onMoveDown={
                index < questions.length - 1
                  ? () => moveQuestion(index, index + 1)
                  : undefined
              }
            />
          ))}

          {questions.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              <MessageSquare className="w-8 h-8 mx-auto mb-2 text-gray-300" />
              <p>No questions yet. Click "Add Question" to create one.</p>
            </div>
          )}
        </div>
      </div>

      {/* Action Items Section */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h4 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
            <FileText className="w-4 h-4 text-[#009b87]" />
            Action Items ({actionItems.length})
          </h4>
          <button
            onClick={addActionItem}
            className="inline-flex items-center gap-1 text-sm text-[#009b87] hover:underline"
          >
            <Plus className="w-4 h-4" />
            Add Action Item
          </button>
        </div>

        <div className="space-y-4">
          {actionItems.map((item, index) => (
            <ActionItemEditor
              key={index}
              item={item}
              index={index}
              onChange={(updates) => updateActionItem(index, updates)}
              onRemove={() => removeActionItem(index)}
            />
          ))}

          {actionItems.length === 0 && (
            <div className="text-center py-6 text-gray-500">
              <FileText className="w-8 h-8 mx-auto mb-2 text-gray-300" />
              <p>No action items. Click "Add Action Item" to request documents.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// Question Editor
// ============================================================================

interface QuestionEditorProps {
  question: Partial<SynthesizedQuestion>
  index: number
  onChange: (updates: Partial<SynthesizedQuestion>) => void
  onRemove: () => void
  onMoveUp?: () => void
  onMoveDown?: () => void
}

function QuestionEditor({
  question,
  index,
  onChange,
  onRemove,
  onMoveUp,
  onMoveDown,
}: QuestionEditorProps) {
  return (
    <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
      <div className="flex items-start gap-3">
        {/* Drag handle and number */}
        <div className="flex flex-col items-center gap-1">
          <div className="flex flex-col gap-0.5">
            {onMoveUp && (
              <button
                onClick={onMoveUp}
                className="p-0.5 text-gray-400 hover:text-gray-600"
                title="Move up"
              >
                <GripVertical className="w-4 h-4 rotate-90" />
              </button>
            )}
            {onMoveDown && (
              <button
                onClick={onMoveDown}
                className="p-0.5 text-gray-400 hover:text-gray-600"
                title="Move down"
              >
                <GripVertical className="w-4 h-4 -rotate-90" />
              </button>
            )}
          </div>
          <span className="flex-shrink-0 w-6 h-6 bg-[#009b87] text-white rounded-full flex items-center justify-center text-xs font-medium">
            {index + 1}
          </span>
        </div>

        {/* Question fields */}
        <div className="flex-1 space-y-3">
          {/* Question text */}
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">
              Question
            </label>
            <textarea
              value={question.question_text || ''}
              onChange={(e) => onChange({ question_text: e.target.value })}
              placeholder="What would you like to ask the client?"
              rows={2}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#009b87] focus:border-transparent resize-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            {/* Hint */}
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1 flex items-center gap-1">
                <Lightbulb className="w-3 h-3 text-amber-500" />
                Hint for Client
              </label>
              <input
                type="text"
                value={question.hint || ''}
                onChange={(e) => onChange({ hint: e.target.value })}
                placeholder="Context to help answer"
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#009b87] focus:border-transparent"
              />
            </div>

            {/* Suggested answerer */}
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1 flex items-center gap-1">
                <User className="w-3 h-3 text-gray-400" />
                Best Answered By
              </label>
              <input
                type="text"
                value={question.suggested_answerer || ''}
                onChange={(e) => onChange({ suggested_answerer: e.target.value })}
                placeholder="e.g., Operations Manager"
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#009b87] focus:border-transparent"
              />
            </div>
          </div>

          {/* Coverage info (read-only) */}
          {question.covers_summary && (
            <p className="text-xs text-gray-400 italic">
              Covers: {question.covers_summary}
            </p>
          )}
        </div>

        {/* Remove button */}
        <button
          onClick={onRemove}
          className="p-1.5 text-gray-400 hover:text-red-500 rounded-lg hover:bg-red-50"
          title="Remove question"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}

// ============================================================================
// Action Item Editor
// ============================================================================

interface ActionItemEditorProps {
  item: Partial<ActionItem>
  index: number
  onChange: (updates: Partial<ActionItem>) => void
  onRemove: () => void
}

function ActionItemEditor({
  item,
  index,
  onChange,
  onRemove,
}: ActionItemEditorProps) {
  const itemTypes = [
    { value: 'document', label: 'Document' },
    { value: 'task', label: 'Task' },
    { value: 'meeting', label: 'Meeting' },
  ]

  return (
    <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
      <div className="flex items-start gap-3">
        <FileText className="w-5 h-5 text-gray-400 flex-shrink-0 mt-2" />

        <div className="flex-1 space-y-3">
          <div className="grid grid-cols-3 gap-3">
            {/* Title */}
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Title
              </label>
              <input
                type="text"
                value={item.title || ''}
                onChange={(e) => onChange({ title: e.target.value })}
                placeholder="What do you need?"
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#009b87] focus:border-transparent"
              />
            </div>

            {/* Type */}
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Type
              </label>
              <select
                value={item.item_type || 'document'}
                onChange={(e) => onChange({ item_type: e.target.value as ActionItem['item_type'] })}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#009b87] focus:border-transparent"
              >
                {itemTypes.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            {/* Description */}
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Description
              </label>
              <input
                type="text"
                value={item.description || ''}
                onChange={(e) => onChange({ description: e.target.value })}
                placeholder="Additional details"
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#009b87] focus:border-transparent"
              />
            </div>

            {/* Hint */}
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Hint
              </label>
              <input
                type="text"
                value={item.hint || ''}
                onChange={(e) => onChange({ hint: e.target.value })}
                placeholder="Where to find it"
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#009b87] focus:border-transparent"
              />
            </div>
          </div>
        </div>

        {/* Remove button */}
        <button
          onClick={onRemove}
          className="p-1.5 text-gray-400 hover:text-red-500 rounded-lg hover:bg-red-50"
          title="Remove item"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}

export default PackageEditor
