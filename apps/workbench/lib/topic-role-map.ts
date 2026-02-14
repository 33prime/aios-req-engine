/**
 * Topic-to-role mapping for "Who Has The Data" intelligence.
 * Ported from app/agents/stakeholder_suggester.py TOPIC_ROLE_MAP.
 */

export const TOPIC_ROLE_MAP: Record<string, string[]> = {
  // Business and strategic topics
  budget: ['CFO', 'Finance Director', 'Budget Owner', 'VP Finance'],
  financial: ['CFO', 'Finance Director', 'Controller', 'VP Finance'],
  roi: ['CFO', 'Finance Director', 'Business Sponsor', 'VP Finance'],
  strategy: ['CEO', 'VP Strategy', 'Business Development', 'COO'],
  'business goals': ['CEO', 'Business Sponsor', 'VP Strategy', 'Product Owner'],
  kpis: ['Business Sponsor', 'Product Owner', 'VP Operations', 'Analytics Lead'],
  metrics: ['Product Owner', 'Analytics Lead', 'VP Operations', 'Business Analyst'],
  // Technical topics
  technical: ['CTO', 'Tech Lead', 'Engineering Manager', 'IT Director'],
  architecture: ['CTO', 'Tech Lead', 'Solutions Architect', 'Engineering Manager'],
  integration: ['Tech Lead', 'Integration Engineer', 'IT Director', 'Solutions Architect'],
  api: ['Tech Lead', 'Engineering Manager', 'Integration Engineer', 'Developer'],
  security: ['CISO', 'Security Lead', 'IT Director', 'Compliance Officer'],
  infrastructure: ['IT Director', 'DevOps Lead', 'CTO', 'SysAdmin'],
  database: ['Database Admin', 'Tech Lead', 'Engineering Manager', 'Data Engineer'],
  // Process and operations
  process: ['Operations Manager', 'Process Owner', 'COO', 'Business Analyst'],
  workflow: ['Operations Manager', 'Process Owner', 'Product Owner', 'Team Lead'],
  operations: ['COO', 'Operations Manager', 'VP Operations', 'Process Owner'],
  compliance: ['Compliance Officer', 'Legal Counsel', 'Risk Manager', 'CISO'],
  regulatory: ['Compliance Officer', 'Legal Counsel', 'Risk Manager', 'VP Legal'],
  // User and customer topics
  users: ['Product Manager', 'Customer Success Lead', 'UX Lead', 'Support Manager'],
  customer: ['Customer Success Lead', 'Product Manager', 'Sales Lead', 'Support Manager'],
  support: ['Support Manager', 'Customer Success Lead', 'Service Desk Lead'],
  training: ['Training Manager', 'HR Lead', 'Operations Manager', 'Change Manager'],
  // Design and experience
  design: ['Design Lead', 'UX Lead', 'Brand Manager', 'Creative Director'],
  ux: ['UX Lead', 'Product Designer', 'Design Lead', 'Product Manager'],
  brand: ['Brand Manager', 'Marketing Lead', 'Creative Director', 'CMO'],
  // Product and requirements
  requirements: ['Product Owner', 'Product Manager', 'Business Analyst', 'Project Manager'],
  features: ['Product Owner', 'Product Manager', 'Engineering Manager', 'Tech Lead'],
  roadmap: ['Product Manager', 'Product Owner', 'VP Product', 'CEO'],
  priorities: ['Product Owner', 'Product Manager', 'Business Sponsor', 'CEO'],
  scope: ['Product Owner', 'Project Manager', 'Business Sponsor', 'Product Manager'],
  // Data topics
  data: ['Data Analyst', 'Database Admin', 'Data Engineer', 'Business Analyst'],
  analytics: ['Analytics Lead', 'Data Analyst', 'Business Intelligence', 'Product Manager'],
  reporting: ['Business Analyst', 'Analytics Lead', 'Finance Director', 'Operations Manager'],
  // Legal and HR
  legal: ['Legal Counsel', 'VP Legal', 'Compliance Officer', 'Contract Manager'],
  hr: ['HR Director', 'HR Manager', 'People Ops Lead', 'Talent Lead'],
  contracts: ['Legal Counsel', 'Contract Manager', 'Procurement Lead', 'VP Legal'],
  // Project management
  timeline: ['Project Manager', 'Program Manager', 'Product Owner', 'Business Sponsor'],
  milestones: ['Project Manager', 'Program Manager', 'Product Manager', 'Business Sponsor'],
  resources: ['Resource Manager', 'Project Manager', 'HR Director', 'Operations Manager'],
}

export const ARTIFACT_SUGGESTIONS: Record<string, string[]> = {
  budget: ['Budget spreadsheet', 'Financial projections', 'Capex approval forms'],
  financial: ['Financial reports', 'P&L statements', 'Cost analysis'],
  roi: ['ROI calculator', 'Business case document', 'Investment summary'],
  strategy: ['Strategic plan', 'Vision document', 'Competitive analysis'],
  technical: ['Architecture diagrams', 'API specs', 'Tech stack docs'],
  architecture: ['System design docs', 'Architecture decision records', 'Integration diagrams'],
  security: ['Security assessment', 'Risk register', 'Compliance checklist'],
  process: ['Process maps', 'SOPs', 'Training materials'],
  workflow: ['Workflow diagrams', 'Process documentation', 'RACI matrix'],
  operations: ['Operations manual', 'SLA documents', 'Capacity plan'],
  compliance: ['Regulatory frameworks', 'Audit reports', 'Privacy policies'],
  regulatory: ['Compliance matrix', 'Regulatory filings', 'Audit trail'],
  users: ['User research', 'Persona documents', 'Journey maps'],
  customer: ['Customer feedback', 'NPS reports', 'Support tickets analysis'],
  data: ['Data dictionary', 'ERD', 'Database schema'],
  analytics: ['Analytics dashboards', 'KPI reports', 'Data models'],
  requirements: ['Requirements doc', 'User stories', 'Acceptance criteria'],
  features: ['Feature specs', 'Product backlog', 'Feature comparison'],
  timeline: ['Project plan', 'Gantt chart', 'Sprint schedule'],
  legal: ['Legal review', 'Contract templates', 'Terms of service'],
}

/**
 * Get topics relevant to a business driver type.
 */
export function getTopicsForDriverType(driverType: 'pain' | 'goal' | 'kpi'): string[] {
  switch (driverType) {
    case 'pain':
      return ['process', 'operations', 'users', 'workflow']
    case 'goal':
      return ['strategy', 'business goals', 'requirements', 'roadmap']
    case 'kpi':
      return ['metrics', 'kpis', 'analytics', 'reporting']
    default:
      return ['requirements']
  }
}

/**
 * Extract additional topics from text by keyword matching.
 */
export function inferTopicsFromText(text: string): string[] {
  const textLower = text.toLowerCase()
  const matched: string[] = []
  for (const topic of Object.keys(TOPIC_ROLE_MAP)) {
    if (textLower.includes(topic)) {
      matched.push(topic)
    }
  }
  return matched
}
