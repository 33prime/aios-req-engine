'use client';

import { useState } from 'react';
import type { ProjectContext, KeyUser } from '@/types';
import { Plus, Edit2 } from 'lucide-react';

interface UsersSectionProps {
  context: ProjectContext;
  onUpdate: (data: Record<string, unknown>) => Promise<void>;
}

export default function UsersSection({ context, onUpdate }: UsersSectionProps) {
  const [adding, setAdding] = useState(false);
  const [newUser, setNewUser] = useState<Partial<KeyUser>>({
    name: '',
    role: '',
    frustrations: [],
    helps: [],
  });

  const handleAddUser = async () => {
    if (!newUser.name?.trim()) return;

    const updatedUsers = [
      ...context.key_users,
      {
        name: newUser.name,
        role: newUser.role || '',
        frustrations: newUser.frustrations || [],
        helps: newUser.helps || [],
        source: 'manual' as const,
        locked: false,
      },
    ];

    await onUpdate({ users: updatedUsers });
    setNewUser({ name: '', role: '', frustrations: [], helps: [] });
    setAdding(false);
  };

  return (
    <div className="context-section">
      <div className="flex items-center gap-2 mb-6">
        <span className="text-2xl">👥</span>
        <h2 className="text-xl font-semibold text-gray-900">Key Users</h2>
      </div>

      <h3 className="text-sm font-medium text-gray-700 mb-3">Who will use this daily?</h3>

      {context.key_users.length > 0 ? (
        <div className="space-y-4 mb-4">
          {context.key_users.map((user, idx) => (
            <UserCard key={idx} user={user} index={idx} />
          ))}
        </div>
      ) : (
        <div className="empty-state mb-4">
          <p className="mb-3">Who are the primary users?</p>
        </div>
      )}

      {/* Add user form */}
      {adding ? (
        <div className="border border-gray-200 rounded-lg p-4 mb-4">
          <div className="grid grid-cols-2 gap-3 mb-3">
            <input
              type="text"
              placeholder="Name"
              value={newUser.name}
              onChange={(e) => setNewUser({ ...newUser, name: e.target.value })}
            />
            <input
              type="text"
              placeholder="Role"
              value={newUser.role}
              onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
            />
          </div>
          <div className="flex gap-2">
            <button onClick={handleAddUser} className="btn btn-primary btn-small">
              Add User
            </button>
            <button onClick={() => setAdding(false)} className="btn btn-secondary btn-small">
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <button onClick={() => setAdding(true)} className="btn btn-secondary btn-small">
          <Plus className="w-3 h-3" />
          Add another user type
        </button>
      )}
    </div>
  );
}

function UserCard({ user, index }: { user: KeyUser; index: number }) {
  const getSourceTag = () => {
    if (user.source === 'call') return '💬 From your call';
    if (user.source === 'dashboard') return '💬 From your answers';
    if (user.source === 'chat') return '💬 From chat';
    return null;
  };

  const sourceTag = getSourceTag();

  return (
    <div className="user-card">
      {sourceTag && <div className="auto-tag">{sourceTag}</div>}
      <div className="text-base font-semibold text-gray-900 mb-2">
        {index + 1}. {user.name}{user.role && ` - ${user.role}`}
      </div>

      {user.frustrations.length > 0 && (
        <div className="mb-2">
          <strong className="text-sm">Main frustrations:</strong>
          <ul className="list-disc list-inside text-sm text-gray-700 mt-1">
            {user.frustrations.map((f, i) => (
              <li key={i}>{f}</li>
            ))}
          </ul>
        </div>
      )}

      {user.helps.length > 0 && (
        <div className="mb-2">
          <strong className="text-sm">What would help:</strong>
          <ul className="list-disc list-inside text-sm text-gray-700 mt-1">
            {user.helps.map((h, i) => (
              <li key={i}>{h}</li>
            ))}
          </ul>
        </div>
      )}

      {user.frustrations.length === 0 && user.helps.length === 0 && (
        <p className="text-sm text-gray-500">Basic info captured, needs more detail</p>
      )}

      <button className="btn btn-secondary btn-small mt-2">
        <Edit2 className="w-3 h-3" />
        Edit
      </button>
    </div>
  );
}
