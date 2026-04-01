/**
 * Project-type-aware labels for BRD sections.
 *
 * The BRD tab structure stays the same but labels adapt:
 * - Internal software: Process Pains, Process Targets, Requirements, etc.
 * - New product: Market Insights, Business Theses, Capabilities, etc.
 */

export type ProjectType = 'internal' | 'new_product' | 'hybrid'

interface SectionLabels {
  painPoints: string
  goals: string
  requirements: string
  workflows: string
  constraints: string
  actors: string
  h1Label: string
  h2Label: string
  h3Label: string
}

const LABELS: Record<ProjectType, SectionLabels> = {
  internal: {
    painPoints: 'Process Pains',
    goals: 'Process Targets',
    requirements: 'Requirements',
    workflows: 'Current → Future State',
    constraints: 'Technical & Structural Constraints',
    actors: 'Roles',
    h1Label: 'Fix It',
    h2Label: 'Extend It',
    h3Label: 'Productize It',
  },
  new_product: {
    painPoints: 'Market Insights',
    goals: 'Business Theses',
    requirements: 'Capabilities',
    workflows: 'Desired Outcome Flows',
    constraints: 'Market & Regulatory Constraints',
    actors: 'Personas',
    h1Label: 'Prove It',
    h2Label: 'Scale It',
    h3Label: 'Platform',
  },
  hybrid: {
    painPoints: 'Pain Points & Market Insights',
    goals: 'Goals & Theses',
    requirements: 'Requirements & Capabilities',
    workflows: 'Workflows',
    constraints: 'Constraints',
    actors: 'Actors',
    h1Label: 'Fix It',
    h2Label: 'Extend & Prove',
    h3Label: 'Platform',
  },
}

export function getProjectLabels(projectType: ProjectType | string | null | undefined): SectionLabels {
  const type = (projectType || 'new_product') as ProjectType
  return LABELS[type] || LABELS.new_product
}
