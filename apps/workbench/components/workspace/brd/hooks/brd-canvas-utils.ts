/**
 * Pure helper functions for BRDCanvas optimistic updates and counting.
 * No React hooks — safe to call anywhere.
 */

import type { BRDWorkspaceData, MoSCoWGroup } from '@/types/workspace'

export function applyConfirmationUpdate(
  data: BRDWorkspaceData,
  entityType: string,
  entityId: string,
  status: string,
): BRDWorkspaceData {
  const update = { ...data }

  if (entityType === 'business_driver') {
    update.business_context = {
      ...update.business_context,
      pain_points: update.business_context.pain_points.map((p) =>
        p.id === entityId ? { ...p, confirmation_status: status } : p
      ),
      goals: update.business_context.goals.map((g) =>
        g.id === entityId ? { ...g, confirmation_status: status } : g
      ),
      success_metrics: update.business_context.success_metrics.map((m) =>
        m.id === entityId ? { ...m, confirmation_status: status } : m
      ),
    }
  } else if (entityType === 'persona') {
    update.actors = update.actors.map((a) =>
      a.id === entityId ? { ...a, confirmation_status: status } : a
    )
  } else if (entityType === 'vp_step') {
    update.workflows = update.workflows.map((w) =>
      w.id === entityId ? { ...w, confirmation_status: status } : w
    )
  } else if (entityType === 'feature') {
    update.requirements = {
      must_have: update.requirements.must_have.map((f) =>
        f.id === entityId ? { ...f, confirmation_status: status } : f
      ),
      should_have: update.requirements.should_have.map((f) =>
        f.id === entityId ? { ...f, confirmation_status: status } : f
      ),
      could_have: update.requirements.could_have.map((f) =>
        f.id === entityId ? { ...f, confirmation_status: status } : f
      ),
      out_of_scope: update.requirements.out_of_scope.map((f) =>
        f.id === entityId ? { ...f, confirmation_status: status } : f
      ),
    }
  } else if (entityType === 'constraint') {
    update.constraints = update.constraints.map((c) =>
      c.id === entityId ? { ...c, confirmation_status: status } : c
    )
  } else if (entityType === 'workflow') {
    update.workflow_pairs = (update.workflow_pairs || []).map((wp) =>
      wp.id === entityId ? { ...wp, confirmation_status: status } : wp
    )
  } else if (entityType === 'data_entity') {
    update.data_entities = update.data_entities.map((d) =>
      d.id === entityId ? { ...d, confirmation_status: status } : d
    )
  } else if (entityType === 'stakeholder') {
    update.stakeholders = update.stakeholders.map((s) =>
      s.id === entityId ? { ...s, confirmation_status: status } : s
    )
  }
  // solution_flow_step: managed separately by SolutionFlowModal — no BRD data update needed

  return update
}

export function moveFeatureToGroup(
  data: BRDWorkspaceData,
  featureId: string,
  targetGroup: MoSCoWGroup,
): BRDWorkspaceData {
  let movedFeature = null
  const groups: MoSCoWGroup[] = ['must_have', 'should_have', 'could_have', 'out_of_scope']
  const newReqs = { ...data.requirements }

  for (const group of groups) {
    const idx = newReqs[group].findIndex((f) => f.id === featureId)
    if (idx !== -1) {
      movedFeature = { ...newReqs[group][idx], priority_group: targetGroup }
      newReqs[group] = [...newReqs[group].slice(0, idx), ...newReqs[group].slice(idx + 1)]
      break
    }
  }

  if (movedFeature) {
    newReqs[targetGroup] = [...newReqs[targetGroup], movedFeature]
  }

  return { ...data, requirements: newReqs }
}

export function countEntities(data: BRDWorkspaceData): number {
  return (
    data.business_context.pain_points.length +
    data.business_context.goals.length +
    data.business_context.success_metrics.length +
    data.actors.length +
    data.workflows.length +
    data.requirements.must_have.length +
    data.requirements.should_have.length +
    data.requirements.could_have.length +
    data.constraints.length +
    data.data_entities.length +
    data.stakeholders.length
  )
}

export function countConfirmed(data: BRDWorkspaceData): number {
  const isConfirmed = (s: string | null | undefined) =>
    s === 'confirmed_consultant' || s === 'confirmed_client'

  return (
    data.business_context.pain_points.filter((p) => isConfirmed(p.confirmation_status)).length +
    data.business_context.goals.filter((g) => isConfirmed(g.confirmation_status)).length +
    data.business_context.success_metrics.filter((m) => isConfirmed(m.confirmation_status)).length +
    data.actors.filter((a) => isConfirmed(a.confirmation_status)).length +
    data.workflows.filter((w) => isConfirmed(w.confirmation_status)).length +
    data.requirements.must_have.filter((f) => isConfirmed(f.confirmation_status)).length +
    data.requirements.should_have.filter((f) => isConfirmed(f.confirmation_status)).length +
    data.requirements.could_have.filter((f) => isConfirmed(f.confirmation_status)).length +
    data.constraints.filter((c) => isConfirmed(c.confirmation_status)).length +
    data.data_entities.filter((d) => isConfirmed(d.confirmation_status)).length +
    data.stakeholders.filter((s) => isConfirmed(s.confirmation_status)).length
  )
}

export function countStale(data: BRDWorkspaceData): number {
  return (
    data.actors.filter((a) => a.is_stale).length +
    data.workflows.filter((w) => w.is_stale).length +
    data.requirements.must_have.filter((f) => f.is_stale).length +
    data.requirements.should_have.filter((f) => f.is_stale).length +
    data.requirements.could_have.filter((f) => f.is_stale).length +
    data.requirements.out_of_scope.filter((f) => f.is_stale).length +
    data.data_entities.filter((d) => d.is_stale).length
  )
}
