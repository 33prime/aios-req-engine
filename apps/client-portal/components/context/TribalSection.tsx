'use client';

import { useState } from 'react';
import type { ProjectContext } from '@/types';
import { Plus } from 'lucide-react';

interface TribalSectionProps {
  context: ProjectContext;
  onUpdate: (data: Record<string, unknown>) => Promise<void>;
}

export default function TribalSection({ context, onUpdate }: TribalSectionProps) {
  const [adding, setAdding] = useState(false);
  const [newKnowledge, setNewKnowledge] = useState('');

  const handleAdd = async () => {
    if (!newKnowledge.trim()) return;

    const updated = [...context.tribal_knowledge, newKnowledge];
    await onUpdate({ knowledge: updated });
    setNewKnowledge('');
    setAdding(false);
  };

  const getSourceTag = () => {
    if (context.tribal_source === 'call') return '💬 From your call';
    if (context.tribal_source === 'dashboard') return '💬 From your answers';
    if (context.tribal_source === 'chat') return '💬 From chat';
    return null;
  };

  const sourceTag = getSourceTag();

  return (
    <div className="context-section">
      <div className="flex items-center gap-2 mb-6">
        <span className="text-2xl">💡</span>
        <h2 className="text-xl font-semibold text-gray-900">Tribal Knowledge</h2>
      </div>

      <h3 className="text-sm font-medium text-gray-700 mb-3">Edge cases, gotchas, unusual scenarios</h3>

      {context.tribal_knowledge.length > 0 ? (
        <div className="auto-populated mb-4">
          {sourceTag && <div className="auto-tag">{sourceTag}</div>}
          <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
            {context.tribal_knowledge.map((item, idx) => (
              <li key={idx}>{item}</li>
            ))}
          </ul>
        </div>
      ) : (
        <div className="empty-state mb-4">
          <p className="mb-3">Any edge cases or special scenarios we should know about?</p>
        </div>
      )}

      {/* Add form */}
      {adding ? (
        <div className="border border-gray-200 rounded-lg p-4 mb-4">
          <textarea
            placeholder="Describe an edge case or unusual scenario..."
            value={newKnowledge}
            onChange={(e) => setNewKnowledge(e.target.value)}
            rows={3}
            className="w-full mb-3"
          />
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
          Add more edge cases
        </button>
      )}
    </div>
  );
}
