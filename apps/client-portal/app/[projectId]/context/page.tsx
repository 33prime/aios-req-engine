'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import api from '@/lib/api';
import type { ProjectContext, ClientDocument } from '@/types';
import ContextProgress from '@/components/context/ContextProgress';
import ProblemSection from '@/components/context/ProblemSection';
import SuccessSection from '@/components/context/SuccessSection';
import UsersSection from '@/components/context/UsersSection';
import DesignSection from '@/components/context/DesignSection';
import CompetitorsSection from '@/components/context/CompetitorsSection';
import TribalSection from '@/components/context/TribalSection';
import FilesSection from '@/components/context/FilesSection';

export default function ContextPage() {
  const params = useParams();
  const projectId = params.projectId as string;

  const [context, setContext] = useState<ProjectContext | null>(null);
  const [files, setFiles] = useState<ClientDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadData = async () => {
    try {
      const [contextData, filesData] = await Promise.all([
        api.getContext(projectId) as Promise<ProjectContext>,
        api.getFiles(projectId) as Promise<ClientDocument[]>,
      ]);
      setContext(contextData);
      setFiles(filesData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load context');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [projectId]);

  const handleUpdate = async (section: string, data: Record<string, unknown>) => {
    try {
      const updated = await api.updateContextSection(projectId, section, data) as ProjectContext;
      setContext(updated);
    } catch (err) {
      console.error('Update error:', err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="spinner" />
      </div>
    );
  }

  if (error || !context) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600">{error || 'Failed to load context'}</p>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-2">Project Context</h1>
      <p className="text-gray-600 mb-8">
        Everything we know about your project • Auto-populated • Refine anytime
      </p>

      {/* Progress Overview */}
      <ContextProgress scores={context.completion_scores} />

      {/* Sections */}
      <div className="card">
        <ProblemSection
          context={context}
          onUpdate={(data) => handleUpdate('problem', data)}
        />

        <SuccessSection
          context={context}
          onUpdate={(data) => handleUpdate('success', data)}
        />

        <UsersSection
          context={context}
          onUpdate={(data) => handleUpdate('users', data)}
        />

        <DesignSection
          context={context}
          onUpdate={(data) => handleUpdate('design', data)}
        />

        <CompetitorsSection
          context={context}
          onUpdate={(data) => handleUpdate('competitors', data)}
        />

        <TribalSection
          context={context}
          onUpdate={(data) => handleUpdate('tribal', data)}
        />

        <FilesSection
          files={files}
          projectId={projectId}
          onUpload={loadData}
        />
      </div>
    </div>
  );
}
