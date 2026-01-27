/**
 * PackagePreview Component
 *
 * Shows the AI-synthesized client package with:
 * - Questions with hints and suggested answerers
 * - Action items (document requests)
 * - Suggested assets for high inference value
 */

'use client'

import React, { useState } from 'react'
import {
  MessageSquare,
  FileText,
  Sparkles,
  User,
  Lightbulb,
  ChevronDown,
  ChevronUp,
  Edit2,
  Send,
  Package,
  Info,
  Layers,
} from 'lucide-react'
import type {
  ClientPackage,
  SynthesizedQuestion,
  ActionItem,
  AssetSuggestion,
} from '@/types/api'

interface PackagePreviewProps {
  package_: ClientPackage
  onEdit?: () => void
  onSend?: () => void
  isSending?: boolean
}

export function PackagePreview({
  package_,
  onEdit,
  onSend,
  isSending = false,
}: PackagePreviewProps) {
  const [showAssets, setShowAssets] = useState(false)

  const isDraft = package_.status === 'draft'
  const isSent = package_.status === 'sent' || package_.status === 'responses_received'

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Package className="w-5 h-5 text-[#009b87]" />
          <h3 className="text-lg font-semibold text-gray-900">
            {isDraft ? 'Draft Package' : 'Client Package'}
          </h3>
          <span
            className={`px-2 py-0.5 text-xs font-medium rounded-full ${
              isDraft
                ? 'bg-amber-100 text-amber-700'
                : isSent
                ? 'bg-green-100 text-green-700'
                : 'bg-gray-100 text-gray-600'
            }`}
          >
            {package_.status.replace('_', ' ')}
          </span>
        </div>

        {/* Summary stats */}
        <div className="flex items-center gap-4 text-sm text-gray-500">
          <span className="flex items-center gap-1">
            <MessageSquare className="w-4 h-4" />
            {package_.questions_count} questions
          </span>
          <span className="flex items-center gap-1">
            <FileText className="w-4 h-4" />
            {package_.action_items_count} action items
          </span>
          {package_.source_items_count > 0 && (
            <span className="flex items-center gap-1">
              <Layers className="w-4 h-4" />
              covers {package_.source_items_count} items
            </span>
          )}
        </div>
      </div>

      {/* Questions */}
      <div className="space-y-4 mb-6">
        <h4 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
          <MessageSquare className="w-4 h-4 text-[#009b87]" />
          Questions ({package_.questions.length})
        </h4>

        {package_.questions.map((question, index) => (
          <QuestionCard key={question.id} question={question} index={index + 1} />
        ))}
      </div>

      {/* Action Items */}
      {package_.action_items.length > 0 && (
        <div className="space-y-3 mb-6">
          <h4 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
            <FileText className="w-4 h-4 text-[#009b87]" />
            Action Items ({package_.action_items.length})
          </h4>

          {package_.action_items.map((item) => (
            <ActionItemCard key={item.id} item={item} />
          ))}
        </div>
      )}

      {/* Asset Suggestions (collapsible) */}
      {package_.suggested_assets && package_.suggested_assets.length > 0 && (
        <div className="mb-6">
          <button
            onClick={() => setShowAssets(!showAssets)}
            className="w-full flex items-center justify-between text-sm font-semibold text-gray-700 py-2"
          >
            <span className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-amber-500" />
              Suggested Assets ({package_.suggested_assets.length})
              <span className="font-normal text-gray-400">- high inference value</span>
            </span>
            {showAssets ? (
              <ChevronUp className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            )}
          </button>

          {showAssets && (
            <div className="space-y-3 mt-2">
              {package_.suggested_assets.map((asset) => (
                <AssetSuggestionCard key={asset.id} asset={asset} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Actions */}
      {isDraft && (
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-100">
          {onEdit && (
            <button
              onClick={onEdit}
              className="inline-flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-900 text-sm font-medium"
            >
              <Edit2 className="w-4 h-4" />
              Edit Package
            </button>
          )}
          {onSend && (
            <button
              onClick={onSend}
              disabled={isSending}
              className="inline-flex items-center gap-2 px-4 py-2 bg-[#009b87] text-white text-sm font-medium rounded-lg hover:bg-[#008775] disabled:opacity-50 transition-colors"
            >
              <Send className="w-4 h-4" />
              {isSending ? 'Sending...' : 'Send to Client Portal'}
            </button>
          )}
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Sub-components
// ============================================================================

interface QuestionCardProps {
  question: SynthesizedQuestion
  index: number
}

function QuestionCard({ question, index }: QuestionCardProps) {
  return (
    <div className="bg-gray-50 rounded-lg p-4 border border-gray-100">
      <div className="flex items-start gap-3">
        <span className="flex-shrink-0 w-6 h-6 bg-[#009b87] text-white rounded-full flex items-center justify-center text-xs font-medium">
          {index}
        </span>
        <div className="flex-1">
          <p className="text-gray-900 font-medium mb-2">{question.question_text}</p>

          {/* Hint */}
          {question.hint && (
            <div className="flex items-start gap-2 text-sm text-gray-600 mb-2">
              <Lightbulb className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
              <span>{question.hint}</span>
            </div>
          )}

          {/* Suggested answerer */}
          {question.suggested_answerer && (
            <div className="flex items-center gap-2 text-sm text-gray-500 mb-2">
              <User className="w-4 h-4 text-gray-400" />
              <span>Best answered by: {question.suggested_answerer}</span>
            </div>
          )}

          {/* Coverage */}
          {question.covers_summary && (
            <div className="flex items-center gap-2 text-xs text-gray-400">
              <Layers className="w-3.5 h-3.5" />
              <span>{question.covers_summary}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

interface ActionItemCardProps {
  item: ActionItem
}

function ActionItemCard({ item }: ActionItemCardProps) {
  return (
    <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg border border-gray-100">
      <FileText className="w-5 h-5 text-gray-400 flex-shrink-0 mt-0.5" />
      <div className="flex-1">
        <p className="font-medium text-gray-900">{item.title}</p>
        {item.description && (
          <p className="text-sm text-gray-600 mt-1">{item.description}</p>
        )}
        {item.hint && (
          <p className="text-xs text-gray-500 mt-1 flex items-center gap-1">
            <Info className="w-3 h-3" />
            {item.hint}
          </p>
        )}
      </div>
      <span
        className={`text-xs px-2 py-1 rounded-full ${
          item.item_type === 'document'
            ? 'bg-blue-100 text-blue-700'
            : item.item_type === 'task'
            ? 'bg-green-100 text-green-700'
            : 'bg-purple-100 text-purple-700'
        }`}
      >
        {item.item_type}
      </span>
    </div>
  )
}

interface AssetSuggestionCardProps {
  asset: AssetSuggestion
}

function AssetSuggestionCard({ asset }: AssetSuggestionCardProps) {
  const categoryStyles: Record<string, string> = {
    sample_data: 'bg-blue-100 text-blue-700',
    process: 'bg-green-100 text-green-700',
    data_systems: 'bg-purple-100 text-purple-700',
    integration: 'bg-orange-100 text-orange-700',
  }

  return (
    <div className="p-3 bg-amber-50 rounded-lg border border-amber-100">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span
              className={`text-xs px-2 py-0.5 rounded-full ${
                categoryStyles[asset.category] || 'bg-gray-100 text-gray-700'
              }`}
            >
              {asset.category.replace('_', ' ')}
            </span>
            <span
              className={`text-xs px-2 py-0.5 rounded-full ${
                asset.priority === 'high'
                  ? 'bg-red-100 text-red-700'
                  : asset.priority === 'medium'
                  ? 'bg-amber-100 text-amber-700'
                  : 'bg-gray-100 text-gray-600'
              }`}
            >
              {asset.priority}
            </span>
          </div>
          <p className="font-medium text-gray-900">{asset.title}</p>
          <p className="text-sm text-gray-600 mt-1">{asset.description}</p>
          <p className="text-sm text-amber-700 mt-2 flex items-center gap-1">
            <Sparkles className="w-3.5 h-3.5" />
            {asset.why_valuable}
          </p>
          {asset.examples.length > 0 && (
            <p className="text-xs text-gray-500 mt-1">
              Examples: {asset.examples.join(', ')}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

export default PackagePreview
