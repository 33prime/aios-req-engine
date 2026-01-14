'use client';

import type { DashboardProgress } from '@/types';
import { CheckCircle, AlertCircle } from 'lucide-react';

interface ProgressTrackerProps {
  progress: DashboardProgress;
}

export default function ProgressTracker({ progress }: ProgressTrackerProps) {
  const { percentage, total_items, completed_items, status_breakdown } = progress;

  const pendingCount = (status_breakdown.not_started || 0) + (status_breakdown.in_progress || 0);

  return (
    <div className="bg-gradient-to-r from-gray-50 to-gray-100 border border-gray-200 rounded-xl p-4 mb-6">
      <div className="flex justify-between items-center mb-2">
        <span className="text-base font-semibold text-gray-900">
          {percentage}% Complete
        </span>
        <span className="text-sm text-gray-600">
          {completed_items} of {total_items} items done
        </span>
      </div>

      <div className="progress-bar mb-3">
        <div
          className="progress-fill"
          style={{ width: `${percentage}%` }}
        />
      </div>

      <div className="grid grid-cols-2 gap-2 text-sm">
        {completed_items > 0 && (
          <div className="flex items-center gap-2 text-success-text">
            <CheckCircle className="w-4 h-4" />
            {completed_items} item{completed_items !== 1 ? 's' : ''} complete
          </div>
        )}
        {pendingCount > 0 && (
          <div className="flex items-center gap-2 text-warning-text">
            <AlertCircle className="w-4 h-4" />
            {pendingCount} item{pendingCount !== 1 ? 's' : ''} pending
          </div>
        )}
      </div>
    </div>
  );
}
