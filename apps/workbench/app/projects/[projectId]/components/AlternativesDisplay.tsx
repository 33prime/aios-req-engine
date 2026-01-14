/**
 * AlternativesDisplay Component
 *
 * Shows alternative solutions considered by A-Team with pros/cons and confidence scores
 */

'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, ThumbsUp, ThumbsDown, Star, AlertCircle } from 'lucide-react';
import { Evidence, EvidenceChain } from './EvidenceChain';

export interface Alternative {
  option: string;
  description: string;
  pros: string[];
  cons: string[];
  confidence: number;
  evidence?: Evidence[];
}

interface AlternativesDisplayProps {
  alternatives: Alternative[];
  chosenOption?: string;
  reasoning?: string;
  collapsible?: boolean;
  defaultExpanded?: boolean;
}

export function AlternativesDisplay({
  alternatives,
  chosenOption,
  reasoning,
  collapsible = true,
  defaultExpanded = false,
}: AlternativesDisplayProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  if (!alternatives || alternatives.length === 0) {
    return null;
  }

  // Sort alternatives by confidence (highest first)
  const sortedAlternatives = [...alternatives].sort((a, b) => b.confidence - a.confidence);

  const content = (
    <div className="space-y-4">
      {/* Reasoning (if chosen option exists) */}
      {chosenOption && reasoning && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start gap-2">
            <Star className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="font-semibold text-blue-900 mb-2">
                Why "{chosenOption}" was chosen:
              </h4>
              <p className="text-sm text-blue-800">{reasoning}</p>
            </div>
          </div>
        </div>
      )}

      {/* Alternatives List */}
      <div className="space-y-3">
        {sortedAlternatives.map((alt, index) => {
          const isChosen = chosenOption === alt.option;

          return (
            <div
              key={index}
              className={`border rounded-lg p-4 ${
                isChosen
                  ? 'border-blue-300 bg-blue-50/50'
                  : 'border-gray-200 bg-white'
              }`}
            >
              {/* Header */}
              <div className="flex items-start justify-between gap-3 mb-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h4 className="font-semibold text-gray-900">
                      {alt.option}
                    </h4>
                    {isChosen && (
                      <span className="text-xs px-2 py-1 bg-blue-600 text-white rounded-full font-medium">
                        ✓ Chosen
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-600 mt-1">
                    {alt.description}
                  </p>
                </div>

                {/* Confidence Badge */}
                <div className="flex-shrink-0">
                  <div className={`px-3 py-1 rounded-full text-sm font-semibold ${
                    alt.confidence >= 0.8
                      ? 'bg-green-100 text-green-700'
                      : alt.confidence >= 0.6
                      ? 'bg-yellow-100 text-yellow-700'
                      : 'bg-red-100 text-red-700'
                  }`}>
                    {Math.round(alt.confidence * 100)}%
                  </div>
                </div>
              </div>

              {/* Pros & Cons */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                {/* Pros */}
                {alt.pros && alt.pros.length > 0 && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <ThumbsUp className="h-4 w-4 text-green-600" />
                      <span className="text-sm font-semibold text-gray-900">
                        Pros
                      </span>
                    </div>
                    <ul className="space-y-1.5">
                      {alt.pros.map((pro, i) => (
                        <li
                          key={i}
                          className="text-sm text-gray-700 flex items-start gap-2"
                        >
                          <span className="text-green-600 flex-shrink-0 mt-0.5">
                            •
                          </span>
                          <span>{pro}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Cons */}
                {alt.cons && alt.cons.length > 0 && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <ThumbsDown className="h-4 w-4 text-red-600" />
                      <span className="text-sm font-semibold text-gray-900">
                        Cons
                      </span>
                    </div>
                    <ul className="space-y-1.5">
                      {alt.cons.map((con, i) => (
                        <li
                          key={i}
                          className="text-sm text-gray-700 flex items-start gap-2"
                        >
                          <span className="text-red-600 flex-shrink-0 mt-0.5">
                            •
                          </span>
                          <span>{con}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* Evidence for this alternative */}
              {alt.evidence && alt.evidence.length > 0 && (
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <EvidenceChain
                    evidence={alt.evidence}
                    title={`Evidence for "${alt.option}"`}
                    collapsible={true}
                    defaultExpanded={false}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Info Note */}
      <div className="flex items-start gap-2 p-3 bg-gray-50 border border-gray-200 rounded-lg">
        <AlertCircle className="h-4 w-4 text-gray-500 flex-shrink-0 mt-0.5" />
        <p className="text-xs text-gray-600">
          A-Team considered {alternatives.length} alternative{alternatives.length !== 1 ? 's' : ''} before selecting the best solution based on evidence and trade-offs.
        </p>
      </div>
    </div>
  );

  if (!collapsible) {
    return (
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-gray-900">
          Alternatives Considered
        </h3>
        {content}
      </div>
    );
  }

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-4 bg-gray-50 hover:bg-gray-100 transition-colors"
      >
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-gray-900">
            Alternatives Considered
          </h3>
          <span className="text-xs px-2 py-1 bg-gray-200 text-gray-600 rounded-full font-medium">
            {alternatives.length} {alternatives.length === 1 ? 'option' : 'options'}
          </span>
        </div>

        {isExpanded ? (
          <ChevronUp className="h-5 w-5 text-gray-400" />
        ) : (
          <ChevronDown className="h-5 w-5 text-gray-400" />
        )}
      </button>

      {isExpanded && <div className="p-4">{content}</div>}
    </div>
  );
}
