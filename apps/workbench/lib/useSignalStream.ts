/**
 * Hook for streaming signal processing with SSE
 *
 * Connects to the signal processing pipeline and provides real-time progress updates
 */

import { useState, useEffect, useCallback, useRef } from 'react';

export type StreamEventType =
  // Standard pipeline phases
  | 'started'
  | 'classification_completed'
  | 'chunking_started'
  | 'chunking_completed'
  | 'build_state_started'
  | 'build_state_completed'
  | 'research_check'
  | 'research_started'
  | 'research_completed'
  | 'a_team_started'
  | 'a_team_completed'
  | 'reconcile_started'
  | 'reconcile_completed'
  | 'completed'
  | 'error'
  | 'progress'
  // Bulk pipeline phases
  | 'bulk_started'
  | 'bulk_extraction_started'
  | 'bulk_extraction_completed'
  | 'bulk_consolidation_started'
  | 'bulk_consolidation_completed'
  | 'bulk_validation_started'
  | 'bulk_validation_completed'
  | 'bulk_proposal_created'
  | 'creative_brief_updated';

export interface StreamEvent {
  type: StreamEventType;
  phase: string;
  data: Record<string, any>;
  progress: number;
}

export interface UseSignalStreamOptions {
  onEvent?: (event: StreamEvent) => void;
  onComplete?: (finalEvent: StreamEvent) => void;
  onError?: (error: Error) => void;
  autoReconnect?: boolean;
}

export interface UseSignalStreamResult {
  isStreaming: boolean;
  progress: number;
  currentPhase: string | null;
  events: StreamEvent[];
  lastEvent: StreamEvent | null;
  error: Error | null;
  start: (signalId: string, projectId: string) => void;
  stop: () => void;
}

export function useSignalStream(
  options: UseSignalStreamOptions = {}
): UseSignalStreamResult {
  const [isStreaming, setIsStreaming] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentPhase, setCurrentPhase] = useState<string | null>(null);
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [lastEvent, setLastEvent] = useState<StreamEvent | null>(null);
  const [error, setError] = useState<Error | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const stop = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  const start = useCallback(
    (signalId: string, projectId: string) => {
      // Clean up any existing connection
      stop();

      // Reset state
      setIsStreaming(true);
      setProgress(0);
      setCurrentPhase(null);
      setEvents([]);
      setLastEvent(null);
      setError(null);

      // Create abort controller for fetch
      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      // Start SSE connection via fetch
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const url = `${apiUrl}/api/v1/stream/process-signal-stream`;

      fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ signal_id: signalId, project_id: projectId }),
        signal: abortController.signal,
      })
        .then(async (response) => {
          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }

          const reader = response.body?.getReader();
          if (!reader) {
            throw new Error('No response body');
          }

          const decoder = new TextDecoder();
          let buffer = '';

          while (true) {
            const { done, value } = await reader.read();

            if (done) {
              setIsStreaming(false);
              break;
            }

            // Decode chunk and add to buffer
            buffer += decoder.decode(value, { stream: true });

            // Process complete SSE messages
            const lines = buffer.split('\n\n');
            buffer = lines.pop() || ''; // Keep incomplete message in buffer

            for (const line of lines) {
              if (!line.trim() || !line.startsWith('data:')) continue;

              try {
                const jsonStr = line.replace(/^data:\s*/, '');
                const event: StreamEvent = JSON.parse(jsonStr);

                // Update state
                setEvents((prev) => [...prev, event]);
                setLastEvent(event);
                setProgress(event.progress);
                setCurrentPhase(event.phase);

                // Call event callback
                options.onEvent?.(event);

                // Handle completion
                if (event.type === 'completed') {
                  setIsStreaming(false);
                  options.onComplete?.(event);
                }

                // Handle errors
                if (event.type === 'error') {
                  const err = new Error(event.data.error || 'Stream error');
                  setError(err);
                  options.onError?.(err);
                }
              } catch (e) {
                console.error('Failed to parse SSE event:', e, line);
              }
            }
          }
        })
        .catch((err) => {
          if (err.name === 'AbortError') {
            console.log('Stream aborted');
            return;
          }
          console.error('Stream error:', err);
          setError(err);
          setIsStreaming(false);
          options.onError?.(err);
        });
    },
    [options, stop]
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stop();
    };
  }, [stop]);

  return {
    isStreaming,
    progress,
    currentPhase,
    events,
    lastEvent,
    error,
    start,
    stop,
  };
}
