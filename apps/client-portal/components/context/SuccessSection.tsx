'use client';

import type { ProjectContext } from '@/types';
import AutoPopulatedBox from './AutoPopulatedBox';
import EmptyState from './EmptyState';

interface SuccessSectionProps {
  context: ProjectContext;
  onUpdate: (data: Record<string, unknown>) => Promise<void>;
}

export default function SuccessSection({ context, onUpdate }: SuccessSectionProps) {
  return (
    <div className="context-section">
      <div className="flex items-center gap-2 mb-6">
        <span className="text-2xl">✨</span>
        <h2 className="text-xl font-semibold text-gray-900">Success Looks Like</h2>
      </div>

      {/* Future state */}
      <h3 className="text-sm font-medium text-gray-700 mb-3">6 months from now, what&apos;s different?</h3>
      {context.success_future ? (
        <AutoPopulatedBox
          content={context.success_future}
          source={context.success_future_source}
          locked={context.success_future_locked}
          onEdit={(newContent) => onUpdate({ future: newContent })}
        />
      ) : (
        <EmptyState
          prompt="Describe your ideal outcome"
          buttonLabel="Add vision"
          onAdd={() => {}}
        />
      )}

      {/* Wow moment */}
      <h3 className="text-sm font-medium text-gray-700 mb-3 mt-6">The &quot;wow&quot; moment</h3>
      {context.success_wow ? (
        <AutoPopulatedBox
          content={context.success_wow}
          source={context.success_wow_source}
          locked={context.success_wow_locked}
          onEdit={(newContent) => onUpdate({ wow: newContent })}
        />
      ) : (
        <EmptyState
          prompt="When will you know this was worth it?"
          buttonLabel="Add your thoughts"
          onAdd={() => {}}
        />
      )}
    </div>
  );
}
