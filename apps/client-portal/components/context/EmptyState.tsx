'use client';

import { Plus } from 'lucide-react';

interface EmptyStateProps {
  prompt: string;
  buttonLabel?: string;
  onAdd: () => void;
}

export default function EmptyState({ prompt, buttonLabel = 'Add information', onAdd }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <p className="mb-3">{prompt}</p>
      <button onClick={onAdd} className="btn btn-secondary btn-small">
        <Plus className="w-3 h-3" />
        {buttonLabel}
      </button>
    </div>
  );
}
