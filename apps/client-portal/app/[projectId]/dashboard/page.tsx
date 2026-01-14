'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import api from '@/lib/api';
import type { DashboardResponse, InfoRequest } from '@/types';
import { Calendar, Clock, CheckCircle, AlertCircle, FileText, MessageSquare } from 'lucide-react';
import ProgressTracker from '@/components/dashboard/ProgressTracker';
import QuestionCard from '@/components/dashboard/QuestionCard';
import DocumentCard from '@/components/dashboard/DocumentCard';

export default function DashboardPage() {
  const params = useParams();
  const projectId = params.projectId as string;

  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadDashboard = async () => {
    try {
      const data = await api.getDashboard(projectId) as DashboardResponse;
      setDashboard(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, [projectId]);

  const handleAnswerSubmit = async (requestId: string, answer: Record<string, unknown>) => {
    try {
      await api.answerInfoRequest(requestId, answer);
      await loadDashboard(); // Refresh
    } catch (err) {
      console.error('Error submitting answer:', err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="spinner" />
      </div>
    );
  }

  if (error || !dashboard) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600">{error || 'Failed to load dashboard'}</p>
      </div>
    );
  }

  const isPreCall = dashboard.phase === 'pre_call';

  // Separate questions and documents
  const questions = dashboard.info_requests.filter(
    (r) => r.request_type === 'question' || r.request_type === 'tribal_knowledge'
  );
  const documents = dashboard.info_requests.filter((r) => r.request_type === 'document');

  return (
    <div>
      {/* Page Title */}
      <h1 className="text-3xl font-bold text-gray-900 mb-2">
        {isPreCall ? 'Discovery Call Preparation' : 'What We Need From You'}
      </h1>
      <p className="text-gray-600 mb-8">
        {isPreCall && dashboard.call_info?.scheduled_date && (
          <>
            {formatDate(dashboard.call_info.scheduled_date)} • {dashboard.call_info.duration_minutes} minutes with {dashboard.call_info.consultant_name}
          </>
        )}
        {!isPreCall && dashboard.call_info?.completed_date && (
          <>
            Discovery call completed {formatDate(dashboard.call_info.completed_date)}
            {dashboard.due_date && <> • Due {formatDate(dashboard.due_date)} to stay on schedule</>}
          </>
        )}
      </p>

      {/* Call Info Card (Pre-call) */}
      {isPreCall && dashboard.call_info && (
        <div className="card mb-6">
          <div className="flex justify-between items-start mb-4">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-1">
                {dashboard.call_info.consultant_name}
              </h3>
              <p className="text-sm text-gray-600">Consultant • ReadyToGo.ai</p>
            </div>
            <button className="btn btn-primary btn-small">
              <Calendar className="w-4 h-4" />
              Add to Calendar
            </button>
          </div>
          <hr className="my-4 border-gray-200" />
          <p className="text-sm text-gray-700">
            This call will clarify your challenges and define the ideal solution.
          </p>
        </div>
      )}

      {/* Call Summary Card (Post-call) */}
      {!isPreCall && (
        <div className="card mb-6">
          <div className="flex justify-between items-center">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-1">
                Discovery Call Complete
              </h3>
              <p className="text-sm text-gray-700">
                Based on our call, we need a few more details to start building.
              </p>
            </div>
            <button className="btn btn-secondary btn-small">
              View Summary
            </button>
          </div>
        </div>
      )}

      {/* Progress Tracker */}
      <ProgressTracker progress={dashboard.progress} />

      {/* Questions Section */}
      {questions.length > 0 && (
        <div className="card">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-gray-900">
              {isPreCall ? 'Questions for You' : 'Action Items'} ({questions.length})
            </h3>
            {isPreCall && <span className="badge badge-ai">AI Generated</span>}
          </div>

          <div className="space-y-4">
            {questions.map((request, index) => (
              <QuestionCard
                key={request.id}
                request={request}
                index={index}
                onAnswer={(answer) => handleAnswerSubmit(request.id, answer)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Documents Section */}
      {documents.length > 0 && (
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Documents That Would Help ({documents.length})
          </h3>

          <div className="space-y-4">
            {documents.map((request) => (
              <DocumentCard
                key={request.id}
                request={request}
                projectId={projectId}
                onUpload={() => loadDashboard()}
              />
            ))}
          </div>
        </div>
      )}

      {/* Footer Note (Pre-call) */}
      {isPreCall && (
        <p className="text-center text-sm text-gray-500 mt-8">
          Not required • Completing this saves 15-20 minutes on the call
        </p>
      )}
    </div>
  );
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });
}
