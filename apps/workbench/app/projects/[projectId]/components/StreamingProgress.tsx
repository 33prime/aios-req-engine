/**
 * StreamingProgress Component
 *
 * Displays real-time progress of signal processing pipeline with phase indicators
 */

'use client';

import { StreamEvent } from '@/lib/useSignalStream';
import { CheckCircle2, Circle, Loader2, XCircle, AlertCircle } from 'lucide-react';

interface StreamingProgressProps {
  isStreaming: boolean;
  progress: number;
  currentPhase: string | null;
  events: StreamEvent[];
  error: Error | null;
}

const PHASES = [
  { key: 'build_state', label: 'Build State', description: 'Reconciling facts into entities' },
  { key: 'research', label: 'Smart Research', description: 'Checking if research needed' },
  { key: 'red_team', label: 'Red Team', description: 'Finding gaps with evidence' },
  { key: 'a_team', label: 'A-Team', description: 'Generating solutions' },
  { key: 'reconcile', label: 'Reconcile', description: 'Updating final state' },
];

export function StreamingProgress({
  isStreaming,
  progress,
  currentPhase,
  events,
  error,
}: StreamingProgressProps) {
  // Determine phase status
  const getPhaseStatus = (phaseKey: string): 'pending' | 'active' | 'completed' | 'error' | 'skipped' => {
    const phaseEvents = events.filter((e) => e.phase === phaseKey);

    if (phaseEvents.some((e) => e.type === 'error')) return 'error';
    if (phaseEvents.some((e) => e.data?.skipped)) return 'skipped';
    if (phaseEvents.some((e) => e.type.includes('completed'))) return 'completed';
    if (currentPhase === phaseKey) return 'active';

    return 'pending';
  };

  // Get phase data
  const getPhaseData = (phaseKey: string) => {
    const completedEvent = events.find(
      (e) => e.phase === phaseKey && e.type.includes('completed')
    );
    return completedEvent?.data;
  };

  if (!isStreaming && events.length === 0) {
    return null;
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">
            Processing Signal
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            Automatic pipeline running...
          </p>
        </div>

        {/* Progress Badge */}
        <div className="flex items-center gap-2">
          {isStreaming && (
            <Loader2 className="h-4 w-4 text-blue-600 animate-spin" />
          )}
          <span className="text-2xl font-bold text-gray-900">
            {progress}%
          </span>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="relative h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="absolute top-0 left-0 h-full bg-gradient-to-r from-blue-500 to-blue-600 transition-all duration-500 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Phase List */}
      <div className="space-y-3">
        {PHASES.map((phase, index) => {
          const status = getPhaseStatus(phase.key);
          const phaseData = getPhaseData(phase.key);

          return (
            <div
              key={phase.key}
              className={`flex items-start gap-3 p-3 rounded-lg transition-colors ${
                status === 'active' ? 'bg-blue-50 border border-blue-200' : ''
              }`}
            >
              {/* Icon */}
              <div className="flex-shrink-0 mt-0.5">
                {status === 'completed' && (
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                )}
                {status === 'active' && (
                  <Loader2 className="h-5 w-5 text-blue-600 animate-spin" />
                )}
                {status === 'error' && (
                  <XCircle className="h-5 w-5 text-red-600" />
                )}
                {status === 'skipped' && (
                  <Circle className="h-5 w-5 text-gray-400" />
                )}
                {status === 'pending' && (
                  <Circle className="h-5 w-5 text-gray-300" />
                )}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span
                    className={`font-medium ${
                      status === 'active'
                        ? 'text-blue-900'
                        : status === 'completed'
                        ? 'text-green-900'
                        : status === 'error'
                        ? 'text-red-900'
                        : 'text-gray-600'
                    }`}
                  >
                    {phase.label}
                  </span>
                  {status === 'skipped' && (
                    <span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full">
                      Skipped
                    </span>
                  )}
                </div>

                <p
                  className={`text-sm mt-0.5 ${
                    status === 'active' ? 'text-blue-700' : 'text-gray-500'
                  }`}
                >
                  {phase.description}
                </p>

                {/* Phase-specific data */}
                {phaseData && (
                  <div className="mt-2 text-xs text-gray-600 space-y-1">
                    {phase.key === 'build_state' && (
                      <div className="flex gap-4">
                        {phaseData.features_created > 0 && (
                          <span>✓ {phaseData.features_created} features</span>
                        )}
                        {phaseData.personas_created > 0 && (
                          <span>✓ {phaseData.personas_created} personas</span>
                        )}
                        {phaseData.vp_steps_created > 0 && (
                          <span>✓ {phaseData.vp_steps_created} VP steps</span>
                        )}
                      </div>
                    )}

                    {phase.key === 'research' && !phaseData.skipped && (
                      <div>
                        ✓ {phaseData.chunks_created || 0} research chunks created
                      </div>
                    )}

                    {phase.key === 'red_team' && (
                      <div className="flex gap-4">
                        <span>✓ {phaseData.insights_found} insights</span>
                        {phaseData.critical_count > 0 && (
                          <span className="text-red-600 font-medium">
                            ⚠ {phaseData.critical_count} critical
                          </span>
                        )}
                      </div>
                    )}

                    {phase.key === 'a_team' && (
                      <div className="flex gap-4">
                        <span>✓ {phaseData.patches_generated} patches</span>
                        {phaseData.patches_auto_applied > 0 && (
                          <span className="text-green-600">
                            {phaseData.patches_auto_applied} auto-applied
                          </span>
                        )}
                        {phaseData.patches_queued > 0 && (
                          <span className="text-amber-600">
                            {phaseData.patches_queued} queued
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Error Display */}
      {error && (
        <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-lg">
          <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-medium text-red-900">Pipeline Error</p>
            <p className="text-sm text-red-700 mt-1">{error.message}</p>
          </div>
        </div>
      )}

      {/* Completion Message */}
      {!isStreaming && progress === 100 && !error && (
        <div className="flex items-center gap-3 p-4 bg-green-50 border border-green-200 rounded-lg">
          <CheckCircle2 className="h-5 w-5 text-green-600 flex-shrink-0" />
          <div className="flex-1">
            <p className="font-medium text-green-900">Processing Complete!</p>
            <p className="text-sm text-green-700 mt-1">
              Signal has been fully processed. Check tabs for updates.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
