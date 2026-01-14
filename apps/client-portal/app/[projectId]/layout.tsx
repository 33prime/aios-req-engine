'use client';

import { useEffect, useState } from 'react';
import { useParams, usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@/components/auth/AuthProvider';
import api from '@/lib/api';
import type { PortalProject } from '@/types';
import { ChevronLeft } from 'lucide-react';
import ChatWidget from '@/components/chat/ChatWidget';

export default function ProjectLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const params = useParams();
  const pathname = usePathname();
  const router = useRouter();
  const { user, signOut } = useAuth();
  const projectId = params.projectId as string;

  const [project, setProject] = useState<PortalProject | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadProject = async () => {
      try {
        const data = await api.getProject(projectId) as PortalProject;
        setProject(data);
      } catch (error) {
        console.error('Error loading project:', error);
        router.push('/');
      } finally {
        setLoading(false);
      }
    };

    loadProject();
  }, [projectId, router]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="spinner" />
      </div>
    );
  }

  if (!project) {
    return null;
  }

  const isPreCall = project.portal_phase === 'pre_call';
  const currentTab = pathname?.includes('/context') ? 'context' : 'dashboard';

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.push('/')}
              className="text-gray-500 hover:text-gray-700 flex items-center gap-1 text-sm"
            >
              <ChevronLeft className="w-4 h-4" />
              Projects
            </button>
            <div className="text-xl font-bold text-primary">ReadyToGo.ai</div>
          </div>
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-full bg-primary text-white flex items-center justify-center font-semibold">
              {user?.first_name?.[0] || user?.email?.[0]?.toUpperCase() || 'U'}
            </div>
          </div>
        </div>
      </header>

      {/* Tab Navigation */}
      <nav className="bg-white border-b border-gray-200 sticky top-[65px] z-9">
        <div className="max-w-5xl mx-auto px-6 flex gap-8">
          <button
            onClick={() => router.push(`/${projectId}/dashboard`)}
            className={`nav-tab ${currentTab === 'dashboard' ? 'active' : ''}`}
          >
            Dashboard
          </button>
          {!isPreCall && (
            <button
              onClick={() => router.push(`/${projectId}/context`)}
              className={`nav-tab ${currentTab === 'context' ? 'active' : ''}`}
            >
              Project Context
            </button>
          )}
        </div>
      </nav>

      {/* Main content */}
      <main className="max-w-5xl mx-auto px-6 py-8">
        {children}
      </main>

      {/* Chat Widget */}
      <ChatWidget
        projectId={projectId}
        projectName={project.client_display_name || project.name}
        clientName={user?.first_name}
      />
    </div>
  );
}
