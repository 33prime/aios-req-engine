/**
 * PatchCard Component
 *
 * Enhanced A-Team patch card with alternatives, reasoning, and evidence
 */

'use client';

import { useState } from 'react';
import { Wrench, ChevronDown, ChevronUp, CheckCircle2, XCircle, Clock, Star } from 'lucide-react';
import { Evidence, EvidenceChain } from './EvidenceChain';
import { Alternative, AlternativesDisplay } from './AlternativesDisplay';

export interface PatchInsight {
  id: string;
  status: 'open' | 'queued' | 'applied' | 'dismissed';
  patch_data: {
    target_entity_type: 'feature' | 'vp_step' | 'persona' | 'business_driver';
    target_entity_id: string;
    proposed_changes: Record<string, any>;
    rationale: string;

    // Enhanced fields
    alternatives?: Alternative[];
    evidence_chain?: Evidence[];
    reasoning?: string;
    confidence?: number;
  };
  auto_apply_ok: boolean;
  parent_insight_id?: string;
  created_at: string;
}

interface PatchCardProps {
  patch: PatchInsight;
  onAction?: (action: 'apply' | 'dismiss' | 'view_alternatives') => void;
  expanded?: boolean;
}

const ENTITY_TYPE_LABELS: Record<string, string> = {
  feature: 'Feature',
  vp_step: 'Value Path Step',
  persona: 'Persona',
  business_driver: 'Business Driver',
};

export function PatchCard({ patch, onAction, expanded: defaultExpanded = false }: PatchCardProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  const { patch_data } = patch;
  const entityLabel = ENTITY_TYPE_LABELS[patch_data.target_entity_type];

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden bg-white shadow-sm">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-4 hover:bg-gray-50 transition-colors text-left"
      >
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 p-2 bg-indigo-50 rounded-lg">
            <Wrench className="h-5 w-5 text-indigo-600" />
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-2">
              <span className="text-xs font-medium px-2 py-1 bg-indigo-100 text-indigo-700 rounded-full">
                {entityLabel}
              </span>
              {patch.auto_apply_ok && (
                <span className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded-full">
                  Safe to auto-apply
                </span>
              )}
              {patch_data.confidence !== undefined && (
                <span className={`text-xs px-2 py-1 rounded-full ${
                  patch_data.confidence >= 0.8
                    ? 'bg-green-100 text-green-700'
                    : patch_data.confidence >= 0.6
                    ? 'bg-yellow-100 text-yellow-700'
                    : 'bg-red-100 text-red-700'
                }`}>
                  {Math.round(patch_data.confidence * 100)}% confidence
                </span>
              )}
            </div>

            <h3 className="font-semibold text-gray-900 mb-1">
              Patch for {entityLabel}
            </h3>

            {!isExpanded && (
              <p className="text-sm text-gray-600 line-clamp-2">
                {patch_data.rationale}
              </p>
            )}
          </div>

          <div className="flex-shrink-0 flex items-center gap-2">
            {patch.status === 'applied' && (
              <CheckCircle2 className="h-5 w-5 text-green-600" />
            )}
            {patch.status === 'dismissed' && (
              <XCircle className="h-5 w-5 text-gray-400" />
            )}
            {patch.status === 'queued' && (
              <Clock className="h-5 w-5 text-amber-600" />
            )}

            {isExpanded ? (
              <ChevronUp className="h-5 w-5 text-gray-400" />
            ) : (
              <ChevronDown className="h-5 w-5 text-gray-400" />
            )}
          </div>
        </div>
      </button>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="px-4 pb-4 space-y-4 border-t border-gray-100">
          {/* Rationale */}
          <div className="pt-4">
            <h4 className="text-sm font-semibold text-gray-900 mb-2">
              Rationale
            </h4>
            <p className="text-sm text-gray-700">{patch_data.rationale}</p>
          </div>

          {/* Reasoning (why this solution) */}
          {patch_data.reasoning && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-start gap-2">
                <Star className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <h4 className="text-sm font-semibold text-blue-900 mb-2">
                    Why This Solution
                  </h4>
                  <p className="text-sm text-blue-800">{patch_data.reasoning}</p>
                </div>
              </div>
            </div>
          )}

          {/* Proposed Changes */}
          <div>
            <h4 className="text-sm font-semibold text-gray-900 mb-2">
              Proposed Changes
            </h4>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 space-y-3">
              {Object.entries(patch_data.proposed_changes).map(([field, value]) => (
                <div key={field} className="space-y-1">
                  <span className="text-xs font-medium text-gray-600 uppercase">
                    {field.replace(/_/g, ' ')}
                  </span>
                  <div className="text-sm text-gray-900">
                    {typeof value === 'string' ? (
                      <p className="whitespace-pre-wrap">{value}</p>
                    ) : Array.isArray(value) ? (
                      <ul className="list-disc list-inside space-y-1">
                        {value.map((item, i) => (
                          <li key={i}>{String(item)}</li>
                        ))}
                      </ul>
                    ) : (
                      <pre className="text-xs overflow-x-auto">
                        {JSON.stringify(value, null, 2)}
                      </pre>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Alternatives Considered */}
          {patch_data.alternatives && patch_data.alternatives.length > 0 && (
            <AlternativesDisplay
              alternatives={patch_data.alternatives}
              chosenOption={patch_data.reasoning ? 'Current Solution' : undefined}
              reasoning={patch_data.reasoning}
              collapsible={true}
              defaultExpanded={false}
            />
          )}

          {/* Evidence Chain */}
          {patch_data.evidence_chain && patch_data.evidence_chain.length > 0 && (
            <EvidenceChain
              evidence={patch_data.evidence_chain}
              title="Supporting Evidence"
              collapsible={true}
              defaultExpanded={false}
            />
          )}

          {/* Metadata */}
          <div className="pt-4 border-t border-gray-200 text-xs text-gray-500 space-y-1">
            <p>
              Target: <span className="font-mono">{patch_data.target_entity_id}</span>
            </p>
            <p>
              Created:{' '}
              {new Date(patch.created_at).toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
                hour: 'numeric',
                minute: '2-digit',
              })}
            </p>
          </div>

          {/* Actions */}
          <div className="flex gap-2 pt-4 border-t border-gray-200">
            {patch.status === 'queued' && (
              <>
                <button
                  onClick={() => onAction?.('apply')}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors text-sm font-medium"
                >
                  Apply Patch
                </button>
                <button
                  onClick={() => onAction?.('dismiss')}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors text-sm font-medium"
                >
                  Dismiss
                </button>
              </>
            )}
            {patch.status === 'applied' && (
              <span className="text-sm text-green-600 font-medium flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4" />
                Applied successfully
              </span>
            )}
            {patch.status === 'dismissed' && (
              <span className="text-sm text-gray-500 font-medium flex items-center gap-2">
                <XCircle className="h-4 w-4" />
                Dismissed
              </span>
            )}
            {patch.status === 'open' && (
              <span className="text-sm text-blue-600 font-medium">
                Auto-applied
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
