/**
 * Summarize CI agent tool results into human-readable strings.
 */

type ToolResult = Record<string, unknown> | null | undefined

export function summarizeToolResult(toolName: string, result: ToolResult): string {
  if (!result) return formatToolName(toolName)

  switch (toolName) {
    case 'enrich_firmographics': {
      const fields = result.fields_enriched as string[] | undefined
      const source = result.enrichment_source as string | undefined
      if (fields?.length) {
        return `Enriched ${fields.length} field${fields.length > 1 ? 's' : ''}${source ? ` via ${source}` : ''}`
      }
      return 'Enriched firmographic data'
    }

    case 'analyze_stakeholder_map': {
      const count = result.stakeholder_count as number | undefined
      const projects = result.project_count as number | undefined
      if (count !== undefined) {
        return `Mapped ${count} stakeholder${count !== 1 ? 's' : ''} across ${projects ?? '?'} project${projects !== 1 ? 's' : ''}`
      }
      return 'Analyzed stakeholder map'
    }

    case 'identify_role_gaps': {
      const missing = result.missing_roles as unknown[] | undefined
      if (missing?.length) {
        return `Found ${missing.length} missing role${missing.length > 1 ? 's' : ''}`
      }
      return 'Assessed role coverage'
    }

    case 'synthesize_constraints': {
      const constraints = result.constraints as unknown[] | undefined
      const cats = result.category_summary as Record<string, string> | undefined
      const catCount = cats ? Object.keys(cats).filter(k => cats[k]).length : 0
      if (constraints?.length) {
        return `Identified ${constraints.length} constraint${constraints.length > 1 ? 's' : ''} across ${catCount || '?'} categor${catCount !== 1 ? 'ies' : 'y'}`
      }
      return 'Synthesized constraints'
    }

    case 'synthesize_vision': {
      const clarity = result.clarity_score as number | undefined
      if (clarity !== undefined) {
        return `Synthesized vision (clarity: ${Math.round(clarity * 100)}%)`
      }
      return 'Synthesized vision statement'
    }

    case 'analyze_data_landscape': {
      const count = result.entity_count as number | undefined
      if (count !== undefined) {
        return `Analyzed ${count} data entit${count !== 1 ? 'ies' : 'y'}`
      }
      return 'Analyzed data landscape'
    }

    case 'assess_organizational_context': {
      const style = result.decision_making_style as string | undefined
      const readiness = result.change_readiness as string | undefined
      const parts: string[] = []
      if (style && style !== 'unknown') parts.push(`${style.replace(/_/g, ' ')} decisions`)
      if (readiness && readiness !== 'unknown') parts.push(`${readiness.replace(/_/g, ' ')} change readiness`)
      if (parts.length) return `Assessed: ${parts.join(', ')}`
      return 'Assessed organizational context'
    }

    case 'assess_portfolio_health': {
      const projects = result.project_count as number | undefined
      const summary = result.summary as string | undefined
      if (projects !== undefined) {
        return `Portfolio: ${summary || `${projects} project${projects !== 1 ? 's' : ''}`}`
      }
      return 'Assessed portfolio health'
    }

    case 'update_profile_completeness': {
      const score = result.score as number | undefined
      const label = result.label as string | undefined
      if (score !== undefined) {
        return `Updated score: ${score}/100 (${label || '?'})`
      }
      return 'Updated profile completeness'
    }

    case 'extract_knowledge_base': {
      const bp = result.business_processes_count as number | undefined
      const sops = result.sops_count as number | undefined
      const tk = result.tribal_knowledge_count as number | undefined
      const total = (bp || 0) + (sops || 0) + (tk || 0)
      if (total > 0) {
        return `Extracted ${total} knowledge item${total !== 1 ? 's' : ''}`
      }
      return 'Extracted knowledge base items'
    }

    default:
      return formatToolName(toolName)
  }
}

function formatToolName(toolName: string): string {
  return toolName.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

/**
 * Extract key data points from a tool result for expanded detail view.
 */
export function getToolResultDetails(toolName: string, result: ToolResult): Array<{ label: string; value: string }> {
  if (!result) return []

  const details: Array<{ label: string; value: string }> = []

  switch (toolName) {
    case 'enrich_firmographics': {
      const fields = result.fields_enriched as string[] | undefined
      if (fields?.length) details.push({ label: 'Fields', value: fields.join(', ') })
      if (result.enrichment_source) details.push({ label: 'Source', value: String(result.enrichment_source) })
      break
    }

    case 'analyze_stakeholder_map': {
      const analysis = result.analysis as Record<string, unknown> | undefined
      if (analysis?.decision_makers) {
        details.push({ label: 'Decision Makers', value: (analysis.decision_makers as string[]).join(', ') })
      }
      if (analysis?.alignment_notes) {
        details.push({ label: 'Alignment', value: String(analysis.alignment_notes) })
      }
      if (analysis?.engagement_assessment) {
        details.push({ label: 'Engagement', value: String(analysis.engagement_assessment) })
      }
      break
    }

    case 'identify_role_gaps': {
      const missing = result.missing_roles as Array<{ role: string; urgency: string }> | undefined
      if (missing?.length) {
        details.push({ label: 'Missing Roles', value: missing.map(r => `${r.role} (${r.urgency})`).join(', ') })
      }
      if (result.recommendation) details.push({ label: 'Recommendation', value: String(result.recommendation) })
      break
    }

    case 'synthesize_constraints': {
      if (result.risk_assessment) details.push({ label: 'Risk Assessment', value: String(result.risk_assessment) })
      const cats = result.category_summary as Record<string, string> | undefined
      if (cats) {
        Object.entries(cats).forEach(([cat, summary]) => {
          if (summary) details.push({ label: cat.charAt(0).toUpperCase() + cat.slice(1), value: summary })
        })
      }
      break
    }

    case 'synthesize_vision': {
      if (result.synthesized_vision) details.push({ label: 'Vision', value: String(result.synthesized_vision) })
      if (result.clarity_assessment) details.push({ label: 'Clarity', value: String(result.clarity_assessment) })
      const criteria = result.success_criteria as string[] | undefined
      if (criteria?.length) details.push({ label: 'Success Criteria', value: criteria.join('; ') })
      break
    }

    case 'assess_organizational_context': {
      if (result.key_insight) details.push({ label: 'Key Insight', value: String(result.key_insight) })
      const pitfalls = result.watch_out_for as string[] | undefined
      if (pitfalls?.length) details.push({ label: 'Watch Out For', value: pitfalls.join('; ') })
      if (result.political_dynamics) details.push({ label: 'Politics', value: String(result.political_dynamics) })
      break
    }

    case 'assess_portfolio_health': {
      if (result.summary) details.push({ label: 'Summary', value: String(result.summary) })
      const projects = result.projects as Array<{ name: string; feature_count: number }> | undefined
      if (projects?.length) {
        details.push({
          label: 'Projects',
          value: projects.map(p => `${p.name} (${p.feature_count} features)`).join(', '),
        })
      }
      break
    }

    case 'update_profile_completeness': {
      const sections = result.sections as Record<string, number> | undefined
      if (sections) {
        details.push({
          label: 'Section Scores',
          value: Object.entries(sections)
            .map(([k, v]) => `${k.replace(/_/g, ' ')}: ${v}`)
            .join(', '),
        })
      }
      break
    }

    default: {
      // Show top-level string/number values
      Object.entries(result).forEach(([key, val]) => {
        if (typeof val === 'string' || typeof val === 'number') {
          details.push({ label: key.replace(/_/g, ' '), value: String(val) })
        }
      })
    }
  }

  return details.slice(0, 6) // Cap at 6 details
}
