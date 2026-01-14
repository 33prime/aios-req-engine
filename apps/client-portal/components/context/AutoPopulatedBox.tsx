'use client';

import { useState } from 'react';
import { MessageSquare, Edit2, Plus } from 'lucide-react';
import type { ContextSource } from '@/types';

interface AutoPopulatedBoxProps {
  content: string;
  source?: ContextSource;
  locked?: boolean;
  onEdit?: (newContent: string) => void;
  onAdd?: () => void;
}

export default function AutoPopulatedBox({
  content,
  source,
  locked,
  onEdit,
  onAdd,
}: AutoPopulatedBoxProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(content);

  const getSourceLabel = () => {
    switch (source) {
      case 'call':
        return '💬 From your call with Matt';
      case 'dashboard':
        return '💬 From your answers';
      case 'chat':
        return '💬 From your conversations';
      case 'manual':
        return null; // Don't show tag for manual edits
      default:
        return null;
    }
  };

  const handleSave = () => {
    if (onEdit) {
      onEdit(editValue);
    }
    setIsEditing(false);
  };

  const sourceLabel = getSourceLabel();

  if (isEditing) {
    return (
      <div className="auto-populated">
        <textarea
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          rows={4}
          className="w-full mb-2"
        />
        <div className="flex gap-2">
          <button onClick={handleSave} className="btn btn-primary btn-small">
            Save
          </button>
          <button
            onClick={() => {
              setEditValue(content);
              setIsEditing(false);
            }}
            className="btn btn-secondary btn-small"
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="auto-populated">
      {sourceLabel && <div className="auto-tag">{sourceLabel}</div>}
      <p className="text-sm text-gray-700 leading-relaxed mb-3">{content}</p>
      <div className="flex gap-2">
        {onEdit && (
          <button
            onClick={() => setIsEditing(true)}
            className="btn btn-secondary btn-small"
          >
            <Edit2 className="w-3 h-3" />
            Edit
          </button>
        )}
        {onAdd && (
          <button onClick={onAdd} className="btn btn-secondary btn-small">
            <Plus className="w-3 h-3" />
            Add more
          </button>
        )}
      </div>
      {locked && (
        <p className="text-xs text-gray-500 mt-2">
          ✓ Your edit is saved. Auto-updates won&apos;t overwrite this.
        </p>
      )}
    </div>
  );
}
