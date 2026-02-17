import { posthog } from './posthog'

function track(event: string, properties?: Record<string, unknown>) {
  if (typeof window === 'undefined') return
  try {
    posthog.capture(event, properties)
  } catch {
    // Silent fail — analytics should never break the app
  }
}

export const analytics = {
  // Auth
  signedIn: (method: string) =>
    track('signed_in', { method }),

  // Projects
  projectCreated: (projectId: string) =>
    track('project_created', { project_id: projectId }),
  projectViewed: (projectId: string) =>
    track('project_viewed', { project_id: projectId }),

  // Signals
  signalSubmitted: (projectId: string, signalType: string) =>
    track('signal_submitted', { project_id: projectId, signal_type: signalType }),

  // BRD
  brdViewed: (projectId: string) =>
    track('brd_viewed', { project_id: projectId }),

  // Confirmations
  entityConfirmed: (entityType: string, projectId: string) =>
    track('entity_confirmed', { entity_type: entityType, project_id: projectId }),

  // Discovery
  discoveryCheckRun: (projectId: string, score: number) =>
    track('discovery_check_run', { project_id: projectId, score }),

  // Prototypes
  prototypeGenerated: (projectId: string, prototypeId: string) =>
    track('prototype_generated', { project_id: projectId, prototype_id: prototypeId }),
  prototypeReviewed: (prototypeId: string) =>
    track('prototype_reviewed', { prototype_id: prototypeId }),

  // Consultant Enrichment
  profileEnrichmentStarted: () =>
    track('profile_enrichment_started'),
  profileEnrichmentCompleted: (completeness: number) =>
    track('profile_enrichment_completed', { profile_completeness: completeness }),

  // Workspace
  workspacePhaseChanged: (projectId: string, phase: string) =>
    track('workspace_phase_changed', { project_id: projectId, phase }),

  // Chat
  chatMessageSent: (projectId: string) =>
    track('chat_message_sent', { project_id: projectId }),
}
