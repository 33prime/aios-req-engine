'use client';

import { useState } from 'react';
import type { ProjectContext } from '@/types';
import AutoPopulatedBox from './AutoPopulatedBox';
import EmptyState from './EmptyState';
import { Target, Plus } from 'lucide-react';

interface ProblemSectionProps {
  context: ProjectContext;
  onUpdate: (data: Record<string, unknown>) => Promise<void>;
}

export default function ProblemSection({ context, onUpdate }: ProblemSectionProps) {
  const [addingMetric, setAddingMetric] = useState(false);
  const [newMetric, setNewMetric] = useState({ metric: '', current: '', goal: '' });

  const handleAddMetric = async () => {
    if (!newMetric.metric.trim()) return;

    const updatedMetrics = [
      ...context.metrics,
      { ...newMetric, source: 'manual' as const, locked: false },
    ];

    await onUpdate({ metrics: updatedMetrics });
    setNewMetric({ metric: '', current: '', goal: '' });
    setAddingMetric(false);
  };

  return (
    <div className="context-section">
      <div className="flex items-center gap-2 mb-6">
        <span className="text-2xl">🎯</span>
        <h2 className="text-xl font-semibold text-gray-900">The Problem</h2>
      </div>

      {/* What's broken */}
      <h3 className="text-sm font-medium text-gray-700 mb-3">What&apos;s broken or missing today?</h3>
      {context.problem_main ? (
        <AutoPopulatedBox
          content={context.problem_main}
          source={context.problem_main_source}
          locked={context.problem_main_locked}
          onEdit={(newContent) => onUpdate({ main: newContent })}
        />
      ) : (
        <EmptyState
          prompt="What challenges are you facing?"
          buttonLabel="Add problem description"
          onAdd={() => {}}
        />
      )}

      {/* Why now */}
      <h3 className="text-sm font-medium text-gray-700 mb-3 mt-6">Why tackle this now?</h3>
      {context.problem_why_now ? (
        <AutoPopulatedBox
          content={context.problem_why_now}
          source={context.problem_why_now_source}
          locked={context.problem_why_now_locked}
          onEdit={(newContent) => onUpdate({ why_now: newContent })}
        />
      ) : (
        <EmptyState
          prompt="What's driving the urgency?"
          buttonLabel="Add urgency"
          onAdd={() => {}}
        />
      )}

      {/* Metrics */}
      <h3 className="text-sm font-medium text-gray-700 mb-3 mt-6">Key Metrics</h3>
      {context.metrics.length > 0 ? (
        <div className="space-y-2 mb-4">
          {context.metrics.map((m, idx) => (
            <div key={idx} className="auto-populated">
              {m.source && m.source !== 'manual' && (
                <div className="auto-tag">
                  💬 From {m.source === 'call' ? 'your call' : 'your answers'}
                </div>
              )}
              <div className="text-sm">
                <strong>{m.metric}</strong>
                <br />
                Current: {m.current || 'N/A'} → Goal: {m.goal || 'N/A'}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState
          prompt="What metrics matter most?"
          buttonLabel="Add metric"
          onAdd={() => setAddingMetric(true)}
        />
      )}

      {/* Add metric form */}
      {addingMetric && (
        <div className="border border-gray-200 rounded-lg p-4 mb-4">
          <div className="grid grid-cols-3 gap-3 mb-3">
            <input
              type="text"
              placeholder="Metric name"
              value={newMetric.metric}
              onChange={(e) => setNewMetric({ ...newMetric, metric: e.target.value })}
            />
            <input
              type="text"
              placeholder="Current value"
              value={newMetric.current}
              onChange={(e) => setNewMetric({ ...newMetric, current: e.target.value })}
            />
            <input
              type="text"
              placeholder="Goal value"
              value={newMetric.goal}
              onChange={(e) => setNewMetric({ ...newMetric, goal: e.target.value })}
            />
          </div>
          <div className="flex gap-2">
            <button onClick={handleAddMetric} className="btn btn-primary btn-small">
              Add Metric
            </button>
            <button
              onClick={() => setAddingMetric(false)}
              className="btn btn-secondary btn-small"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {context.metrics.length > 0 && !addingMetric && (
        <button
          onClick={() => setAddingMetric(true)}
          className="btn btn-secondary btn-small"
        >
          <Plus className="w-3 h-3" />
          Add another metric
        </button>
      )}
    </div>
  );
}
