/**
 * Realistic card fixture data for each of the 8 QuickActionCards types.
 */

export const GAP_CLOSER_CARD = {
  card_type: 'gap_closer' as const,
  id: 'gap-1',
  data: {
    label: 'Missing user onboarding flow',
    severity: 'high',
    resolution: 'Add an onboarding workflow with first-run wizard steps.',
    actions: [
      { label: 'Create workflow', command: 'Create a new onboarding workflow with 3 steps' },
    ],
    entity_type: 'workflow',
    gap_source: 'structural',
  },
}

export const ACTION_BUTTONS_CARD = {
  card_type: 'action_buttons' as const,
  id: 'ab-1',
  data: {
    buttons: [
      { label: 'Confirm all features', command: 'Confirm all draft features', variant: 'primary' },
      { label: 'Skip', command: 'Skip confirmation for now', variant: 'ghost' },
    ],
  },
}

export const CHOICE_CARD = {
  card_type: 'choice' as const,
  id: 'choice-1',
  data: {
    title: 'Authentication Method',
    question: 'Which auth approach should we use?',
    options: [
      { label: 'OAuth 2.0', command: 'Use OAuth 2.0 for authentication' },
      { label: 'Magic link', command: 'Use magic link email authentication' },
      { label: 'SSO only', command: 'Use SSO-only authentication' },
    ],
  },
}

export const PROPOSAL_CARD = {
  card_type: 'proposal' as const,
  id: 'prop-1',
  data: {
    title: 'Real-time notifications',
    body: 'Push notifications via WebSocket for order status updates.',
    tags: ['feature', 'mvp'],
    bullets: [
      'WebSocket connection per session',
      'Fallback to polling on mobile',
    ],
    actions: [
      { label: 'Approve', command: 'Approve real-time notifications feature', variant: 'primary' },
      { label: 'Modify', command: 'Modify real-time notifications proposal', variant: 'outline' },
      { label: 'Skip', command: 'Skip this proposal', variant: 'ghost' },
    ],
  },
}

export const EMAIL_DRAFT_CARD = {
  card_type: 'email_draft' as const,
  id: 'email-1',
  data: {
    to: 'alice@client.com',
    subject: 'Q1 Planning — open questions',
    body: 'Hi Alice,\n\nFollowing up on our call, we have a few outstanding questions about the payment integration timeline and preferred auth flow.\n\nCould you confirm by Friday?\n\nBest,\nConsultant',
  },
}

export const MEETING_CARD = {
  card_type: 'meeting' as const,
  id: 'meeting-1',
  data: {
    topic: 'Sprint 2 requirements review',
    attendees: ['Alice Chen', 'Bob Smith', 'Consultant'],
    agenda: [
      'Review confirmed features (5 min)',
      'Discuss open auth questions (10 min)',
      'Prioritize backlog items (10 min)',
      'Next steps (5 min)',
    ],
  },
}

export const SMART_SUMMARY_CARD = {
  card_type: 'smart_summary' as const,
  id: 'summary-1',
  data: {
    items: [
      { label: 'User dashboard', type: 'feature', checked: true },
      { label: 'GDPR compliance', type: 'constraint', checked: false },
      { label: 'Schedule client demo', type: 'task', checked: false },
      { label: 'Preferred deployment region?', type: 'question', checked: true },
    ],
  },
}

export const EVIDENCE_CARD = {
  card_type: 'evidence' as const,
  id: 'evidence-1',
  data: {
    items: [
      {
        quote: 'We need real-time sync across all devices — that is non-negotiable.',
        source: 'Kickoff meeting transcript',
        section: 'Core requirements',
      },
      {
        quote: 'Budget ceiling is $250k for Phase 1.',
        source: 'Client email — Jan 15',
      },
    ],
  },
}

/** All 8 card fixtures as an array for batch tests. */
export const ALL_CARDS = [
  GAP_CLOSER_CARD,
  ACTION_BUTTONS_CARD,
  CHOICE_CARD,
  PROPOSAL_CARD,
  EMAIL_DRAFT_CARD,
  MEETING_CARD,
  SMART_SUMMARY_CARD,
  EVIDENCE_CARD,
]
