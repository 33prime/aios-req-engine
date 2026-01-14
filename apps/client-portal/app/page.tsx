'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/components/auth/AuthProvider';
import api from '@/lib/api';
import type { PortalProject } from '@/types';
import { ChevronRight, Calendar, Clock } from 'lucide-react';

export default function HomePage() {
  const { user } = useAuth();
  const router = useRouter();
  const [projects, setProjects] = useState<PortalProject[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user needs to see welcome screen
    if (user && !user.has_seen_welcome) {
      router.push('/welcome');
      return;
    }

    const loadProjects = async () => {
      try {
        const data = await api.getProjects() as { projects: PortalProject[] };
        setProjects(data.projects);

        // If only one project, redirect directly to it
        if (data.projects.length === 1) {
          router.push(`/${data.projects[0].id}/dashboard`);
        }
      } catch (error) {
        console.error('Error loading projects:', error);
      } finally {
        setLoading(false);
      }
    };

    loadProjects();
  }, [user, router]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="spinner" />
      </div>
    );
  }

  if (projects.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header />
        <main className="max-w-3xl mx-auto px-6 py-12">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-gray-900 mb-4">No Projects Yet</h1>
            <p className="text-gray-600">
              You&apos;ll see your projects here once your consultant sets them up.
            </p>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main className="max-w-3xl mx-auto px-6 py-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Your Projects</h1>
        <p className="text-gray-600 mb-8">Select a project to view details and collaborate.</p>

        <div className="space-y-4">
          {projects.map((project) => (
            <ProjectCard key={project.id} project={project} />
          ))}
        </div>
      </main>
    </div>
  );
}

function Header() {
  const { user, signOut } = useAuth();

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
      <div className="max-w-3xl mx-auto px-6 py-4 flex items-center justify-between">
        <div className="text-xl font-bold text-primary">ReadyToGo.ai</div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-600">{user?.email}</span>
          <button
            onClick={signOut}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            Sign out
          </button>
        </div>
      </div>
    </header>
  );
}

function ProjectCard({ project }: { project: PortalProject }) {
  const router = useRouter();

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return null;
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const getPhaseLabel = (phase: string) => {
    switch (phase) {
      case 'pre_call':
        return { label: 'Discovery Prep', color: 'bg-blue-100 text-blue-800' };
      case 'post_call':
        return { label: 'In Progress', color: 'bg-yellow-100 text-yellow-800' };
      case 'building':
        return { label: 'Building', color: 'bg-purple-100 text-purple-800' };
      case 'testing':
        return { label: 'Testing', color: 'bg-green-100 text-green-800' };
      default:
        return { label: phase, color: 'bg-gray-100 text-gray-800' };
    }
  };

  const phase = getPhaseLabel(project.portal_phase);

  return (
    <button
      onClick={() => router.push(`/${project.id}/dashboard`)}
      className="w-full card hover:border-primary transition-colors text-left flex items-center justify-between"
    >
      <div>
        <div className="flex items-center gap-3 mb-2">
          <h2 className="text-lg font-semibold text-gray-900">
            {project.client_display_name || project.name}
          </h2>
          <span className={`badge ${phase.color}`}>{phase.label}</span>
        </div>

        <div className="flex items-center gap-4 text-sm text-gray-500">
          {project.discovery_call_date && (
            <span className="flex items-center gap-1">
              <Calendar className="w-4 h-4" />
              {project.call_completed_at ? 'Call completed' : 'Call'}: {formatDate(project.discovery_call_date)}
            </span>
          )}
          {project.prototype_expected_date && (
            <span className="flex items-center gap-1">
              <Clock className="w-4 h-4" />
              Expected: {formatDate(project.prototype_expected_date)}
            </span>
          )}
        </div>
      </div>

      <ChevronRight className="w-5 h-5 text-gray-400" />
    </button>
  );
}
