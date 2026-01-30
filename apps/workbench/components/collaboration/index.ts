/**
 * Collaboration Components
 *
 * Components for the collaboration tab including:
 * - PhaseProgress: Linear phase progress bar with steps and gates
 * - PendingQueue: Queue of items needing client input
 * - PackagePreview: AI-synthesized client package preview
 * - PackageEditor: Edit questions/action items before sending
 * - CurrentFocusSection: Phase-aware content display (legacy)
 * - ClientPortalCard: Compact portal status card
 * - TouchpointHistory: Completed touchpoints accordion
 * - PortalSyncIndicator: Real-time sync progress
 */

// New linear phase workflow components
export { PhaseProgress, PhaseProgressCompact } from './PhaseProgress'
export { PendingQueue } from './PendingQueue'
export { PackagePreview } from './PackagePreview'
export { PackageEditor } from './PackageEditor'

// Portal management
export { ClientPortalModal } from './ClientPortalModal'
export { ClientPortalCard } from './ClientPortalCard'

// Modal flows
export { PendingItemsModal } from './PendingItemsModal'
export { PrepReviewModal } from './PrepReviewModal'
export { SendConfirmModal } from './SendConfirmModal'

// Legacy components (still used)
export { CurrentFocusSection } from './CurrentFocusSection'
export { TouchpointHistory } from './TouchpointHistory'
export { PortalSyncIndicator } from './PortalSyncIndicator'
