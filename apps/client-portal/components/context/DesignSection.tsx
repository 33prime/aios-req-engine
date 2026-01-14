'use client';

import { useState } from 'react';
import type { ProjectContext, DesignInspiration } from '@/types';
import AutoPopulatedBox from './AutoPopulatedBox';
import EmptyState from './EmptyState';
import { Plus } from 'lucide-react';

interface DesignSectionProps {
  context: ProjectContext;
  onUpdate: (data: Record<string, unknown>) => Promise<void>;
}

export default function DesignSection({ context, onUpdate }: DesignSectionProps) {
  const [adding, setAdding] = useState(false);
  const [newInspiration, setNewInspiration] = useState({ name: '', url: '', what_like: '' });

  const handleAdd = async () => {
    if (!newInspiration.name.trim()) return;

    const updated = [
      ...context.design_love,
      { ...newInspiration, source: 'manual' as const },
    ];

    await onUpdate({ love: updated });
    setNewInspiration({ name: '', url: '', what_like: '' });
    setAdding(false);
  };

  return (
    <div className="context-section">
      <div className="flex items-center gap-2 mb-6">
        <span className="text-2xl">🎨</span>
        <h2 className="text-xl font-semibold text-gray-900">Design Inspiration</h2>
      </div>

      {/* Apps you love */}
      <h3 className="text-sm font-medium text-gray-700 mb-3">Apps or tools you love</h3>
      {context.design_love.length > 0 ? (
        <div className="space-y-2 mb-4">
          {context.design_love.map((item, idx) => (
            <div key={idx} className="auto-populated">
              <div className="text-sm">
                <strong>{item.name}</strong>
                {item.url && (
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline ml-2"
                  >
                    {item.url}
                  </a>
                )}
                {item.what_like && (
                  <p className="text-gray-600 mt-1">What you like: {item.what_like}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState
          prompt="What apps do you love using?"
          buttonLabel="Add design examples"
          onAdd={() => setAdding(true)}
        />
      )}

      {/* Add form */}
      {adding && (
        <div className="border border-gray-200 rounded-lg p-4 mb-4">
          <div className="space-y-3 mb-3">
            <input
              type="text"
              placeholder="App/tool name"
              value={newInspiration.name}
              onChange={(e) => setNewInspiration({ ...newInspiration, name: e.target.value })}
            />
            <input
              type="text"
              placeholder="URL (optional)"
              value={newInspiration.url}
              onChange={(e) => setNewInspiration({ ...newInspiration, url: e.target.value })}
            />
            <input
              type="text"
              placeholder="What do you like about it?"
              value={newInspiration.what_like}
              onChange={(e) => setNewInspiration({ ...newInspiration, what_like: e.target.value })}
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
      )}

      {context.design_love.length > 0 && !adding && (
        <button onClick={() => setAdding(true)} className="btn btn-secondary btn-small mb-6">
          <Plus className="w-3 h-3" />
          Add another
        </button>
      )}

      {/* What to avoid */}
      <h3 className="text-sm font-medium text-gray-700 mb-3 mt-6">What to avoid</h3>
      {context.design_avoid ? (
        <AutoPopulatedBox
          content={context.design_avoid}
          source={context.design_avoid_source}
          locked={context.design_avoid_locked}
          onEdit={(newContent) => onUpdate({ avoid: newContent })}
        />
      ) : (
        <EmptyState
          prompt="Any design styles or patterns to avoid?"
          buttonLabel="Add preferences"
          onAdd={() => {}}
        />
      )}
    </div>
  );
}
