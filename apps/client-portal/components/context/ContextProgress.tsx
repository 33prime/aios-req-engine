'use client';

import type { CompletionScores } from '@/types';

interface ContextProgressProps {
  scores: CompletionScores;
}

const SECTIONS = [
  { key: 'problem', icon: '🎯', name: 'The Problem' },
  { key: 'success', icon: '✨', name: 'Success' },
  { key: 'users', icon: '👥', name: 'Key Users' },
  { key: 'design', icon: '🎨', name: 'Design' },
  { key: 'competitors', icon: '🏢', name: 'Competitors' },
  { key: 'tribal', icon: '💡', name: 'Tribal Knowledge' },
  { key: 'files', icon: '📁', name: 'Files' },
] as const;

export default function ContextProgress({ scores }: ContextProgressProps) {
  const getScoreClass = (score: number) => {
    if (score >= 80) return 'high';
    if (score >= 40) return 'medium';
    return 'low';
  };

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-6 mb-8">
      <div className="flex justify-between items-center mb-4">
        <span className="text-base font-semibold text-gray-900">Context Quality</span>
        <span className="text-sm text-gray-600">{scores.overall}% Complete</span>
      </div>

      <div className="progress-bar mb-4">
        <div className="progress-fill" style={{ width: `${scores.overall}%` }} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
        {SECTIONS.map((section) => {
          const score = scores[section.key as keyof CompletionScores] || 0;
          const scoreClass = getScoreClass(score);

          return (
            <div key={section.key} className="context-progress-item">
              <span className="text-xl">{section.icon}</span>
              <div className="flex-1 min-w-0">
                <div className="text-xs text-gray-700 truncate">{section.name}</div>
                <div className={`context-progress-percent ${scoreClass}`}>
                  {score}%
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
