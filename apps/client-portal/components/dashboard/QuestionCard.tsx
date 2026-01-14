'use client';

import { useState } from 'react';
import type { InfoRequest } from '@/types';
import { CheckCircle, User, Lightbulb } from 'lucide-react';

interface QuestionCardProps {
  request: InfoRequest;
  index: number;
  onAnswer: (answer: Record<string, unknown>) => Promise<void>;
}

export default function QuestionCard({ request, index, onAnswer }: QuestionCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [answer, setAnswer] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const isComplete = request.status === 'complete';
  const existingAnswer = request.answer_data?.text as string | undefined;

  const handleSubmit = async () => {
    if (!answer.trim()) return;

    setSubmitting(true);
    try {
      await onAnswer({ text: answer });
      setIsEditing(false);
    } catch (error) {
      console.error('Error submitting:', error);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className={`info-item ${isComplete ? 'complete' : ''}`}>
      <div className="flex gap-3">
        {/* Number/Check */}
        <div className={`text-xl font-semibold ${isComplete ? 'text-success-text' : 'text-gray-400'}`}>
          {isComplete ? <CheckCircle className="w-6 h-6" /> : index + 1}
        </div>

        {/* Content */}
        <div className="flex-1">
          <h4 className="text-sm font-semibold text-gray-900 mb-2">
            {request.title}
          </h4>

          {/* Context from call (post-call only) */}
          {request.context_from_call && (
            <p className="text-sm text-gray-700 mb-2">
              <span className="font-medium">From call:</span> &quot;{request.context_from_call}&quot;
            </p>
          )}

          {/* Meta info */}
          <div className="flex flex-wrap gap-3 text-xs text-gray-600 mb-3">
            {request.best_answered_by && (
              <span className="flex items-center gap-1">
                <User className="w-3 h-3" />
                Best answered by: <strong>{request.best_answered_by}</strong>
              </span>
            )}
          </div>

          {/* Why important */}
          {request.why_asking && (
            <div className="why-important">
              <div className="why-important-label">
                <Lightbulb className="w-3 h-3" />
                Why this is important
              </div>
              <p className="why-important-text">{request.why_asking}</p>
            </div>
          )}

          {/* Answer display or form */}
          {isComplete && existingAnswer ? (
            <div className="mt-3 bg-white rounded-lg p-3">
              <p className="text-sm font-medium text-gray-900 mb-1">Your answer:</p>
              <p className="text-sm text-gray-700">{existingAnswer}</p>
              {request.completed_at && (
                <p className="text-xs text-gray-500 mt-2">
                  Answered {formatTimeAgo(request.completed_at)}
                </p>
              )}
            </div>
          ) : isEditing ? (
            <div className="mt-3">
              {request.example_answer && (
                <p className="text-xs text-gray-500 mb-2">
                  <strong>Example:</strong> {request.example_answer}
                </p>
              )}
              <textarea
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                placeholder="Type your answer here..."
                rows={4}
                className="w-full mb-2"
              />
              <div className="flex gap-2">
                <button
                  onClick={handleSubmit}
                  disabled={submitting || !answer.trim()}
                  className="btn btn-primary btn-small"
                >
                  {submitting ? <span className="spinner w-4 h-4" /> : 'Save Answer'}
                </button>
                <button
                  onClick={() => setIsEditing(false)}
                  className="btn btn-secondary btn-small"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={() => setIsEditing(true)}
              className="btn btn-secondary btn-small mt-3"
            >
              Answer This Question
            </button>
          )}

          {/* Pro tip */}
          {request.pro_tip && !isComplete && (
            <p className="text-xs text-gray-500 mt-3">
              <strong>Pro tip:</strong> {request.pro_tip}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function formatTimeAgo(dateStr: string) {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffHrs = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffHrs / 24);

  if (diffDays > 0) {
    return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
  } else if (diffHrs > 0) {
    return `${diffHrs} hour${diffHrs !== 1 ? 's' : ''} ago`;
  } else {
    return 'just now';
  }
}
