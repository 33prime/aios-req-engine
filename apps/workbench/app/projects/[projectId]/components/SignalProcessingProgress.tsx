/**
 * SignalProcessingProgress Component
 *
 * Unified progress display for both standard and bulk signal processing pipelines.
 * Automatically detects pipeline type from events and shows appropriate phases.
 */

'use client';

import { StreamEvent } from '@/lib/useSignalStream';
import {
  CheckCircle2,
  Circle,
  Loader2,
  XCircle,
  AlertCircle,
  Zap,
  FileSearch,
  Users,
  Layers,
  AlertTriangle,
  FileCheck,
  Sparkles,
} from 'lucide-react';

interface SignalProcessingProgressProps {
  isStreaming: boolean;
  progress: number;
  currentPhase: string | null;
  events: StreamEvent[];
  error: Error | null;
  onViewProposal?: (proposalId: string) => void;
}

// Standard (lightweight) pipeline phases
const STANDARD_PHASES = [
  { key: 'classification', label: 'Classification', description: 'Analyzing signal type', icon: Zap },
  { key: 'build_state', label: 'Build State', description: 'Reconciling facts into entities', icon: Layers },
  { key: 'reconcile', label: 'Reconcile', description: 'Updating final state', icon: FileCheck },
];

// Bulk (heavyweight) pipeline phases
const BULK_PHASES = [
  { key: 'classification', label: 'Classification', description: 'Analyzing signal power', icon: Zap },
  { key: 'extraction', label: 'Extraction', description: 'Running parallel extraction agents', icon: FileSearch },
  { key: 'creative_brief', label: 'Creative Brief', description: 'Auto-filling project context', icon: Sparkles },
  { key: 'consolidation', label: 'Consolidation', description: 'Matching & deduplicating entities', icon: Layers },
  { key: 'validation', label: 'Validation', description: 'Checking for contradictions', icon: AlertTriangle },
  { key: 'proposal', label: 'Proposal', description: 'Creating bulk update proposal', icon: FileCheck },
];

export function SignalProcessingProgress({
  isStreaming,
  progress,
  currentPhase,
  events,
  error,
  onViewProposal,
}: SignalProcessingProgressProps) {
  // Detect which pipeline is being used
  const isBulkPipeline = events.some(e =>
    e.type.startsWith('bulk_') ||
    e.data?.using_bulk_pipeline === true ||
    e.data?.pipeline === 'bulk'
  );

  const phases = isBulkPipeline ? BULK_PHASES : STANDARD_PHASES;

  // Get classification result
  const classificationEvent = events.find(e => e.type === 'classification_completed');
  const classificationData = classificationEvent?.data;

  // Get proposal ID if created
  const proposalEvent = events.find(e => e.type === 'bulk_proposal_created');
  const proposalId = proposalEvent?.data?.proposal_id;

  // Determine phase status
  const getPhaseStatus = (phaseKey: string): 'pending' | 'active' | 'completed' | 'error' | 'skipped' => {
    const phaseEvents = events.filter((e) => e.phase === phaseKey);

    if (phaseEvents.some((e) => e.type === 'error')) return 'error';
    if (phaseEvents.some((e) => e.data?.skipped)) return 'skipped';
    if (phaseEvents.some((e) => e.type.includes('completed') || e.type.includes('created') || e.type.includes('updated'))) return 'completed';
    if (currentPhase === phaseKey) return 'active';

    // Check for started events
    if (phaseEvents.some((e) => e.type.includes('started'))) return 'active';

    return 'pending';
  };

  // Get phase data
  const getPhaseData = (phaseKey: string) => {
    const completedEvent = events.find(
      (e) => e.phase === phaseKey && (e.type.includes('completed') || e.type.includes('created') || e.type.includes('updated'))
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
            {isBulkPipeline ? 'Processing Heavyweight Signal' : 'Processing Signal'}
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            {isBulkPipeline
              ? 'Running bulk extraction and consolidation pipeline...'
              : 'Running standard processing pipeline...'}
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

      {/* Classification Summary (if available) */}
      {classificationData && (
        <div className={`flex items-center gap-3 px-4 py-3 rounded-lg ${
          isBulkPipeline
            ? 'bg-amber-50 border border-amber-200'
            : 'bg-green-50 border border-green-200'
        }`}>
          <Zap className={`h-5 w-5 ${isBulkPipeline ? 'text-amber-600' : 'text-green-600'}`} />
          <div className="flex-1">
            <p className={`text-sm font-medium ${isBulkPipeline ? 'text-amber-900' : 'text-green-900'}`}>
              {classificationData.power_level === 'heavyweight' ? 'Heavyweight Signal Detected' : 'Lightweight Signal'}
            </p>
            <p className={`text-xs mt-0.5 ${isBulkPipeline ? 'text-amber-700' : 'text-green-700'}`}>
              {classificationData.reason}
              {classificationData.estimated_entity_count > 0 && (
                <span className="ml-2">• ~{classificationData.estimated_entity_count} entities estimated</span>
              )}
            </p>
          </div>
          {classificationData.power_score && (
            <div className={`text-xs font-medium px-2 py-1 rounded ${
              isBulkPipeline ? 'bg-amber-200 text-amber-800' : 'bg-green-200 text-green-800'
            }`}>
              Power: {Math.round(classificationData.power_score * 100)}%
            </div>
          )}
        </div>
      )}

      {/* Progress Bar */}
      <div className="relative h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`absolute top-0 left-0 h-full transition-all duration-500 ease-out ${
            isBulkPipeline
              ? 'bg-gradient-to-r from-amber-500 to-orange-500'
              : 'bg-gradient-to-r from-blue-500 to-blue-600'
          }`}
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Phase List */}
      <div className="space-y-3">
        {phases.map((phase) => {
          const status = getPhaseStatus(phase.key);
          const phaseData = getPhaseData(phase.key);
          const Icon = phase.icon;

          return (
            <div
              key={phase.key}
              className={`flex items-start gap-3 p-3 rounded-lg transition-colors ${
                status === 'active'
                  ? isBulkPipeline
                    ? 'bg-amber-50 border border-amber-200'
                    : 'bg-blue-50 border border-blue-200'
                  : ''
              }`}
            >
              {/* Icon */}
              <div className="flex-shrink-0 mt-0.5">
                {status === 'completed' && (
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                )}
                {status === 'active' && (
                  <Loader2 className={`h-5 w-5 animate-spin ${isBulkPipeline ? 'text-amber-600' : 'text-blue-600'}`} />
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
                  <Icon className={`h-4 w-4 ${
                    status === 'active'
                      ? isBulkPipeline ? 'text-amber-600' : 'text-blue-600'
                      : status === 'completed'
                        ? 'text-green-600'
                        : 'text-gray-400'
                  }`} />
                  <span
                    className={`font-medium ${
                      status === 'active'
                        ? isBulkPipeline ? 'text-amber-900' : 'text-blue-900'
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
                    status === 'active'
                      ? isBulkPipeline ? 'text-amber-700' : 'text-blue-700'
                      : 'text-gray-500'
                  }`}
                >
                  {phase.description}
                </p>

                {/* Phase-specific data */}
                {phaseData && (
                  <div className="mt-2 text-xs text-gray-600 space-y-1">
                    {/* Build State results */}
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

                    {/* Extraction results */}
                    {phase.key === 'extraction' && (
                      <div className="flex gap-4">
                        {phaseData.features_found > 0 && (
                          <span>✓ {phaseData.features_found} features</span>
                        )}
                        {phaseData.personas_found > 0 && (
                          <span>✓ {phaseData.personas_found} personas</span>
                        )}
                        {phaseData.stakeholders_found > 0 && (
                          <span>✓ {phaseData.stakeholders_found} stakeholders</span>
                        )}
                      </div>
                    )}

                    {/* Creative Brief update */}
                    {phase.key === 'creative_brief' && phaseData.fields_updated && (
                      <div className="flex flex-wrap gap-1">
                        {phaseData.fields_updated.map((field: string) => (
                          <span key={field} className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded">
                            {field}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Consolidation results */}
                    {phase.key === 'consolidation' && (
                      <div>
                        <span>✓ {phaseData.total_changes || 0} changes consolidated</span>
                      </div>
                    )}

                    {/* Validation results */}
                    {phase.key === 'validation' && (
                      <div className="flex gap-4">
                        {phaseData.contradictions > 0 ? (
                          <span className="text-amber-600 font-medium">
                            ⚠ {phaseData.contradictions} contradictions found
                          </span>
                        ) : (
                          <span className="text-green-600">✓ No contradictions</span>
                        )}
                        {phaseData.requires_review && (
                          <span className="text-amber-600">Review recommended</span>
                        )}
                      </div>
                    )}

                    {/* Proposal created */}
                    {phase.key === 'proposal' && phaseData.proposal_id && (
                      <div className="flex items-center gap-2">
                        <span>✓ {phaseData.total_changes} changes in proposal</span>
                        {onViewProposal && (
                          <button
                            onClick={() => onViewProposal(phaseData.proposal_id)}
                            className="text-blue-600 hover:text-blue-700 underline"
                          >
                            View Proposal
                          </button>
                        )}
                      </div>
                    )}

                    {/* Reconcile results */}
                    {phase.key === 'reconcile' && (
                      <div className="flex gap-4 flex-wrap">
                        {phaseData.total_features > 0 && (
                          <span>Features: {phaseData.total_features}</span>
                        )}
                        {phaseData.total_personas > 0 && (
                          <span>Personas: {phaseData.total_personas}</span>
                        )}
                        {phaseData.total_vp_steps > 0 && (
                          <span>VP Steps: {phaseData.total_vp_steps}</span>
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
        <div className={`flex items-center gap-3 p-4 rounded-lg ${
          isBulkPipeline
            ? 'bg-amber-50 border border-amber-200'
            : 'bg-green-50 border border-green-200'
        }`}>
          <CheckCircle2 className={`h-5 w-5 flex-shrink-0 ${
            isBulkPipeline ? 'text-amber-600' : 'text-green-600'
          }`} />
          <div className="flex-1">
            <p className={`font-medium ${isBulkPipeline ? 'text-amber-900' : 'text-green-900'}`}>
              {isBulkPipeline ? 'Bulk Processing Complete!' : 'Processing Complete!'}
            </p>
            <p className={`text-sm mt-1 ${isBulkPipeline ? 'text-amber-700' : 'text-green-700'}`}>
              {isBulkPipeline && proposalId
                ? 'Review the proposal to apply changes to your project.'
                : 'Signal has been fully processed. Check tabs for updates.'}
            </p>
          </div>
          {proposalId && onViewProposal && (
            <button
              onClick={() => onViewProposal(proposalId)}
              className="px-4 py-2 bg-amber-600 text-white text-sm font-medium rounded-lg hover:bg-amber-700 transition-colors"
            >
              Review Proposal
            </button>
          )}
        </div>
      )}
    </div>
  );
}
