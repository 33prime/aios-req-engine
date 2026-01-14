/**
 * InsightCard Component
 *
 * Enhanced Red Team insight card with evidence chain, reasoning, suggested questions, and confidence
 */

'use client';

import { useState } from 'react';
import { AlertTriangle, AlertCircle, Info, ChevronDown, ChevronUp, HelpCircle, Brain } from 'lucide-react';
import { Evidence, EvidenceChain } from './EvidenceChain';

export interface Insight {
  id: string;
  severity: 'minor' | 'important' | 'critical';
  gate: 'completeness' | 'validation' | 'assumption' | 'scope' | 'wow';
  category: string;
  title: string;
  finding: string;
  why: string;
  suggested_action: string;
  status: 'open' | 'queued' | 'applied' | 'dismissed';
  targets?: Array<{ kind: string; id: string; label: string }>;

  // Enhanced evidence-based fields
  evidence_chain?: Evidence[];
  reasoning?: string;
  suggested_questions?: string[];
  confidence?: number;

  created_at: string;
}

interface InsightCardProps {
  insight: Insight;
  onAction?: (action: 'queue' | 'dismiss' | 'view_evidence') => void;
  expanded?: boolean;
}

const SEVERITY_CONFIG = {
  critical: {
    icon: AlertTriangle,
    color: 'red',
    bg: 'bg-red-50',
    border: 'border-red-300',
    text: 'text-red-900',
    badge: 'bg-red-600 text-white',
  },
  important: {
    icon: AlertCircle,
    color: 'amber',
    bg: 'bg-amber-50',
    border: 'border-amber-300',
    text: 'text-amber-900',
    badge: 'bg-amber-600 text-white',
  },
  minor: {
    icon: Info,
    color: 'blue',
    bg: 'bg-blue-50',
    border: 'border-blue-300',
    text: 'text-blue-900',
    badge: 'bg-blue-600 text-white',
  },
};

const GATE_LABELS = {
  completeness: 'Completeness',
  validation: 'Market Validation',
  assumption: 'Assumption Testing',
  scope: 'Scope Protection',
  wow: 'Wow Factor',
};

export function InsightCard({ insight, onAction, expanded: defaultExpanded = false }: InsightCardProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  const config = SEVERITY_CONFIG[insight.severity];
  const Icon = config.icon;

  return (
    <div className={`border ${config.border} rounded-lg overflow-hidden ${config.bg}`}>
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-4 hover:bg-opacity-80 transition-colors text-left"
      >
        <div className="flex items-start gap-3">
          <Icon className={`h-5 w-5 text-${config.color}-600 flex-shrink-0 mt-0.5`} />

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-2">
              <span className={`text-xs font-semibold px-2 py-1 ${config.badge} rounded-full uppercase`}>
                {insight.severity}
              </span>
              <span className="text-xs px-2 py-1 bg-gray-200 text-gray-700 rounded-full">
                {GATE_LABELS[insight.gate as keyof typeof GATE_LABELS] || insight.gate}
              </span>
              {insight.confidence !== undefined && (
                <span className={`text-xs px-2 py-1 rounded-full ${
                  insight.confidence >= 0.8
                    ? 'bg-green-100 text-green-700'
                    : insight.confidence >= 0.6
                    ? 'bg-yellow-100 text-yellow-700'
                    : 'bg-red-100 text-red-700'
                }`}>
                  {Math.round(insight.confidence * 100)}% confidence
                </span>
              )}
            </div>

            <h3 className={`font-semibold ${config.text} mb-1`}>
              {insight.title}
            </h3>

            {!isExpanded && (
              <p className="text-sm text-gray-700 line-clamp-2">
                {insight.finding}
              </p>
            )}
          </div>

          {isExpanded ? (
            <ChevronUp className="h-5 w-5 text-gray-400 flex-shrink-0" />
          ) : (
            <ChevronDown className="h-5 w-5 text-gray-400 flex-shrink-0" />
          )}
        </div>
      </button>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="px-4 pb-4 space-y-4 bg-white">
          {/* Finding */}
          <div>
            <h4 className="text-sm font-semibold text-gray-900 mb-2">
              What's Wrong
            </h4>
            <p className="text-sm text-gray-700">{insight.finding}</p>
          </div>

          {/* Why it matters */}
          <div>
            <h4 className="text-sm font-semibold text-gray-900 mb-2">
              Why It Matters
            </h4>
            <p className="text-sm text-gray-700">{insight.why}</p>
          </div>

          {/* Reasoning (evidence-based) */}
          {insight.reasoning && (
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
              <div className="flex items-start gap-2">
                <Brain className="h-5 w-5 text-purple-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <h4 className="text-sm font-semibold text-purple-900 mb-2">
                    Detailed Reasoning
                  </h4>
                  <p className="text-sm text-purple-800">{insight.reasoning}</p>
                </div>
              </div>
            </div>
          )}

          {/* Suggested Questions */}
          {insight.suggested_questions && insight.suggested_questions.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <HelpCircle className="h-4 w-4 text-gray-500" />
                <h4 className="text-sm font-semibold text-gray-900">
                  Questions to Resolve This Gap
                </h4>
              </div>
              <ul className="space-y-2">
                {insight.suggested_questions.map((question, index) => (
                  <li
                    key={index}
                    className="text-sm text-gray-700 flex items-start gap-2 p-3 bg-gray-50 rounded-lg"
                  >
                    <span className="text-blue-600 font-semibold flex-shrink-0">
                      Q{index + 1}:
                    </span>
                    <span>{question}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Evidence Chain */}
          {insight.evidence_chain && insight.evidence_chain.length > 0 && (
            <EvidenceChain
              evidence={insight.evidence_chain}
              title="Supporting Evidence"
              collapsible={true}
              defaultExpanded={false}
            />
          )}

          {/* Targets */}
          {insight.targets && insight.targets.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-gray-900 mb-2">
                Affected Entities
              </h4>
              <div className="flex gap-2 flex-wrap">
                {insight.targets.map((target, index) => (
                  <span
                    key={index}
                    className="text-xs px-3 py-1 bg-gray-100 text-gray-700 rounded-full"
                  >
                    {target.kind}: {target.label}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-2 pt-4 border-t border-gray-200">
            {insight.status === 'open' && (
              <>
                <button
                  onClick={() => onAction?.('queue')}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
                >
                  Queue for Review
                </button>
                <button
                  onClick={() => onAction?.('dismiss')}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors text-sm font-medium"
                >
                  Dismiss
                </button>
              </>
            )}
            {insight.status === 'queued' && (
              <span className="text-sm text-amber-600 font-medium">
                ⏳ Queued for review
              </span>
            )}
            {insight.status === 'applied' && (
              <span className="text-sm text-green-600 font-medium">
                ✓ Applied
              </span>
            )}
            {insight.status === 'dismissed' && (
              <span className="text-sm text-gray-500 font-medium">
                Dismissed
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
