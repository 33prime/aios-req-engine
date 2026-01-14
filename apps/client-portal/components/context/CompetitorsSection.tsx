'use client';

import { useState } from 'react';
import type { ProjectContext, Competitor } from '@/types';
import { Plus, Edit2 } from 'lucide-react';

interface CompetitorsSectionProps {
  context: ProjectContext;
  onUpdate: (data: Record<string, unknown>) => Promise<void>;
}

export default function CompetitorsSection({ context, onUpdate }: CompetitorsSectionProps) {
  const [adding, setAdding] = useState(false);
  const [newCompetitor, setNewCompetitor] = useState<Partial<Competitor>>({
    name: '',
    worked: '',
    didnt_work: '',
    why_left: '',
  });

  const handleAdd = async () => {
    if (!newCompetitor.name?.trim()) return;

    const updated = [
      ...context.competitors,
      {
        name: newCompetitor.name,
        worked: newCompetitor.worked || '',
        didnt_work: newCompetitor.didnt_work || '',
        why_left: newCompetitor.why_left || '',
        source: 'manual' as const,
        locked: false,
      },
    ];

    await onUpdate({ competitors: updated });
    setNewCompetitor({ name: '', worked: '', didnt_work: '', why_left: '' });
    setAdding(false);
  };

  return (
    <div className="context-section">
      <div className="flex items-center gap-2 mb-6">
        <span className="text-2xl">🏢</span>
        <h2 className="text-xl font-semibold text-gray-900">What You&apos;ve Tried</h2>
      </div>

      <h3 className="text-sm font-medium text-gray-700 mb-3">Tools you&apos;ve used before</h3>

      {context.competitors.length > 0 ? (
        <div className="space-y-4 mb-4">
          {context.competitors.map((comp, idx) => (
            <CompetitorCard key={idx} competitor={comp} index={idx} />
          ))}
        </div>
      ) : (
        <div className="empty-state mb-4">
          <p className="mb-3">What tools have you tried before?</p>
        </div>
      )}

      {/* Add form */}
      {adding ? (
        <div className="border border-gray-200 rounded-lg p-4 mb-4">
          <div className="space-y-3 mb-3">
            <input
              type="text"
              placeholder="Tool/solution name"
              value={newCompetitor.name}
              onChange={(e) => setNewCompetitor({ ...newCompetitor, name: e.target.value })}
            />
            <input
              type="text"
              placeholder="What worked about it?"
              value={newCompetitor.worked}
              onChange={(e) => setNewCompetitor({ ...newCompetitor, worked: e.target.value })}
            />
            <input
              type="text"
              placeholder="What didn't work?"
              value={newCompetitor.didnt_work}
              onChange={(e) => setNewCompetitor({ ...newCompetitor, didnt_work: e.target.value })}
            />
            <input
              type="text"
              placeholder="Why you stopped using it"
              value={newCompetitor.why_left}
              onChange={(e) => setNewCompetitor({ ...newCompetitor, why_left: e.target.value })}
            />
          </div>
          <div className="flex gap-2">
            <button onClick={handleAdd} className="btn btn-primary btn-small">
              Add
            </button>
            <button onClick={() => setAdding(false)} className="btn btn-secondary btn-small">
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <button onClick={() => setAdding(true)} className="btn btn-secondary btn-small">
          <Plus className="w-3 h-3" />
          Add another tool
        </button>
      )}
    </div>
  );
}

function CompetitorCard({ competitor, index }: { competitor: Competitor; index: number }) {
  const getSourceTag = () => {
    if (competitor.source === 'call') return '💬 From your call';
    if (competitor.source === 'dashboard') return '💬 From your answers';
    if (competitor.source === 'chat') return '💬 From chat';
    return null;
  };

  const sourceTag = getSourceTag();

  return (
    <div className="user-card">
      {sourceTag && <div className="auto-tag">{sourceTag}</div>}
      <div className="text-base font-semibold text-gray-900 mb-2">
        {index + 1}. {competitor.name}
      </div>

      {competitor.worked && (
        <div className="mb-2">
          <strong className="text-sm">What worked:</strong>
          <p className="text-sm text-gray-700">{competitor.worked}</p>
        </div>
      )}

      {competitor.didnt_work && (
        <div className="mb-2">
          <strong className="text-sm">What didn&apos;t work:</strong>
          <p className="text-sm text-gray-700">{competitor.didnt_work}</p>
        </div>
      )}

      {competitor.why_left && (
        <div className="mb-2">
          <strong className="text-sm">Why you left:</strong>
          <p className="text-sm text-gray-700">{competitor.why_left}</p>
        </div>
      )}

      <button className="btn btn-secondary btn-small mt-2">
        <Edit2 className="w-3 h-3" />
        Edit
      </button>
    </div>
  );
}
