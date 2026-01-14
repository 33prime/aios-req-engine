/**
 * EvidenceChain Component
 *
 * Displays evidence with source attribution for Red Team insights and A-Team patches
 */

'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, FileText, Search, User, Lightbulb, ExternalLink } from 'lucide-react';

export interface Evidence {
  source_type: 'signal' | 'research' | 'competitive' | 'persona' | 'feature' | 'prd_section' | 'vp_step' | 'user_input';
  source_id: string;
  source_name: string;
  excerpt: string;
  relevance: string;
  created_at: string;
  url?: string;
  view_url?: string;
  confidence?: number;
  tags?: string[];
}

interface EvidenceChainProps {
  evidence: Evidence[];
  title?: string;
  collapsible?: boolean;
  defaultExpanded?: boolean;
}

const SOURCE_TYPE_CONFIG = {
  signal: { icon: FileText, label: 'Client Signal', color: 'blue' },
  research: { icon: Search, label: 'Research', color: 'purple' },
  competitive: { icon: Search, label: 'Competitive', color: 'orange' },
  persona: { icon: User, label: 'Persona', color: 'green' },
  feature: { icon: Lightbulb, label: 'Feature', color: 'indigo' },
  prd_section: { icon: FileText, label: 'PRD', color: 'gray' },
  vp_step: { icon: FileText, label: 'Value Path', color: 'cyan' },
  user_input: { icon: User, label: 'User Input', color: 'pink' },
};

export function EvidenceChain({
  evidence,
  title = 'Evidence',
  collapsible = true,
  defaultExpanded = false,
}: EvidenceChainProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  if (!evidence || evidence.length === 0) {
    return null;
  }

  const content = (
    <div className="space-y-3">
      {evidence.map((item, index) => {
        const config = SOURCE_TYPE_CONFIG[item.source_type] || SOURCE_TYPE_CONFIG.signal;
        const Icon = config.icon;

        return (
          <div
            key={`${item.source_id}-${index}`}
            className="border border-gray-200 rounded-lg p-4 bg-white hover:border-gray-300 transition-colors"
          >
            {/* Header */}
            <div className="flex items-start gap-3 mb-3">
              <div className={`flex-shrink-0 p-2 bg-${config.color}-50 rounded-lg`}>
                <Icon className={`h-4 w-4 text-${config.color}-600`} />
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`text-xs font-medium px-2 py-1 bg-${config.color}-100 text-${config.color}-700 rounded-full`}>
                    {config.label}
                  </span>
                  {item.confidence !== undefined && (
                    <span className="text-xs text-gray-500">
                      {Math.round(item.confidence * 100)}% confidence
                    </span>
                  )}
                </div>

                <h4 className="font-medium text-gray-900 mt-1 truncate">
                  {item.source_name}
                </h4>

                {item.tags && item.tags.length > 0 && (
                  <div className="flex gap-1 mt-1 flex-wrap">
                    {item.tags.map((tag) => (
                      <span
                        key={tag}
                        className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* External link */}
              {(item.url || item.view_url) && (
                <a
                  href={item.url || item.view_url}
                  target={item.url ? '_blank' : undefined}
                  rel={item.url ? 'noopener noreferrer' : undefined}
                  className="flex-shrink-0 p-1 text-gray-400 hover:text-gray-600 transition-colors"
                >
                  <ExternalLink className="h-4 w-4" />
                </a>
              )}
            </div>

            {/* Excerpt */}
            <blockquote className="border-l-3 border-gray-300 pl-4 py-2 my-3">
              <p className="text-sm text-gray-700 italic line-clamp-3">
                "{item.excerpt}"
              </p>
            </blockquote>

            {/* Relevance */}
            <div className="bg-gray-50 rounded-lg p-3 mt-3">
              <p className="text-xs font-medium text-gray-600 mb-1">
                Why this matters:
              </p>
              <p className="text-sm text-gray-700">{item.relevance}</p>
            </div>

            {/* Timestamp */}
            <p className="text-xs text-gray-400 mt-2">
              {new Date(item.created_at).toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
                hour: 'numeric',
                minute: '2-digit',
              })}
            </p>
          </div>
        );
      })}
    </div>
  );

  if (!collapsible) {
    return (
      <div className="space-y-3">
        {title && (
          <h3 className="text-sm font-semibold text-gray-900">{title}</h3>
        )}
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
          <h3 className="text-sm font-semibold text-gray-900">{title}</h3>
          <span className="text-xs px-2 py-1 bg-gray-200 text-gray-600 rounded-full font-medium">
            {evidence.length} {evidence.length === 1 ? 'source' : 'sources'}
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
