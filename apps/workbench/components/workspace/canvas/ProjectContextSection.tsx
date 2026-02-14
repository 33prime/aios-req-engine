'use client'

import { useState } from 'react'
import {
  FileText,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Download,
} from 'lucide-react'
import type { ProjectContext } from '@/types/workspace'

interface ProjectContextSectionProps {
  projectId: string
  context: ProjectContext | null
  onGenerate: () => Promise<void>
  isGenerating: boolean
}

function relativeTime(dateStr: string): string {
  const now = Date.now()
  const then = new Date(dateStr).getTime()
  const diffMs = now - then
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHr = Math.floor(diffMin / 60)
  if (diffHr < 24) return `${diffHr}h ago`
  const diffDay = Math.floor(diffHr / 24)
  if (diffDay === 1) return 'yesterday'
  if (diffDay < 30) return `${diffDay}d ago`
  const diffMonth = Math.floor(diffDay / 30)
  return `${diffMonth}mo ago`
}

function buildMarkdown(context: ProjectContext): string {
  const lines: string[] = []
  lines.push('# Software Summary\n')

  if (context.product_vision) {
    lines.push('## Vision\n')
    lines.push(context.product_vision + '\n')
  }
  if (context.target_users) {
    lines.push('## Target Users\n')
    lines.push(context.target_users + '\n')
  }
  if (context.core_value_proposition) {
    lines.push('## Value Proposition\n')
    lines.push(context.core_value_proposition + '\n')
  }
  if (context.key_workflows) {
    lines.push('## Key Workflows\n')
    lines.push(context.key_workflows + '\n')
  }
  if (context.data_landscape) {
    lines.push('## Data Landscape\n')
    lines.push(context.data_landscape + '\n')
  }
  if (context.technical_boundaries) {
    lines.push('## Constraints\n')
    lines.push(context.technical_boundaries + '\n')
  }
  if (context.design_principles) {
    lines.push('## Design Direction\n')
    lines.push(context.design_principles + '\n')
  }
  if (context.assumptions.length > 0) {
    lines.push('## Assumptions\n')
    context.assumptions.forEach((a) => lines.push(`- ${a}`))
    lines.push('')
  }
  if (context.open_questions.length > 0) {
    lines.push('## Open Questions\n')
    context.open_questions.forEach((q) => lines.push(`- ${q}`))
    lines.push('')
  }

  lines.push(`---\n`)
  lines.push(`*v${context.version} · ${context.source_count} sources*\n`)

  return lines.join('\n')
}

function triggerDownload(content: string, filename: string) {
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export function ProjectContextSection({
  projectId,
  context,
  onGenerate,
  isGenerating,
}: ProjectContextSectionProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  const hasContext = context !== null && context.version > 0
  const version = context?.version ?? 0
  const isStale = context?.is_stale ?? false

  const handleExport = () => {
    if (!context) return
    const md = buildMarkdown(context)
    triggerDownload(md, `software-summary-v${context.version}.md`)
  }

  const handleGenerate = async () => {
    await onGenerate()
  }

  // Truncated vision for collapsed preview
  const visionPreview =
    context?.product_vision && context.product_vision.length > 160
      ? context.product_vision.slice(0, 160).trimEnd() + '...'
      : context?.product_vision || ''

  return (
    <section>
      <div
        className={`bg-white rounded-2xl shadow-md border overflow-hidden transition-all ${
          isStale ? 'border-gray-300' : 'border-[#E5E5E5]'
        }`}
      >
        {/* Clickable header */}
        <button
          type="button"
          onClick={() => hasContext && setIsExpanded((prev) => !prev)}
          className={`w-full flex items-center gap-3 px-5 py-4 text-left ${
            hasContext ? 'cursor-pointer hover:bg-[#FAFAFA]' : 'cursor-default'
          } transition-colors`}
        >
          <div className="flex items-center gap-2.5 shrink-0">
            <FileText className="w-4.5 h-4.5 text-[#3FAF7A]" />
            <h2 className="text-[16px] font-semibold text-[#333333]">Software Summary</h2>
            {hasContext && (
              <span className="px-2 py-0.5 text-[11px] font-medium bg-[#E8F5E9] text-[#25785A] rounded-full">
                v{version}
              </span>
            )}
          </div>

          <div className="flex-1 min-w-0 mx-3">
            {hasContext ? (
              <p className="text-[13px] text-[#666666] truncate">{visionPreview}</p>
            ) : (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  handleGenerate()
                }}
                disabled={isGenerating}
                className="inline-flex items-center gap-1.5 px-4 py-1.5 text-[12px] font-medium text-white bg-[#3FAF7A] rounded-xl hover:bg-[#25785A] transition-colors disabled:opacity-50"
              >
                {isGenerating ? (
                  <>
                    <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5" />
                    Generate Summary
                  </>
                )}
              </button>
            )}
          </div>

          {hasContext && (
            <div className="flex items-center gap-2 shrink-0">
              {isStale && (
                <span className="px-2 py-0.5 text-[11px] font-medium bg-[#F0F0F0] text-[#666666] rounded-full">
                  Stale
                </span>
              )}
              {isExpanded ? (
                <ChevronUp className="w-4 h-4 text-[#999999]" />
              ) : (
                <ChevronDown className="w-4 h-4 text-[#999999]" />
              )}
            </div>
          )}
        </button>

        {/* Expanded content */}
        <div
          className="overflow-hidden transition-[max-height] duration-300 ease-in-out"
          style={{ maxHeight: isExpanded ? '2000px' : '0px' }}
        >
          {hasContext && context && (
            <div className="border-t border-[#E5E5E5] px-6 py-5">
              {/* Vision — hero section */}
              {context.product_vision && (
                <p className="text-[15px] text-[#333333] leading-relaxed mb-5 whitespace-pre-line">
                  {context.product_vision}
                </p>
              )}

              {/* Clean grid of sections */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4">
                <ContextField label="Target Users" content={context.target_users} />
                <ContextField label="Value Proposition" content={context.core_value_proposition} />
                <ContextField label="Key Workflows" content={context.key_workflows} />
                <ContextField label="Data Landscape" content={context.data_landscape} />
                {context.technical_boundaries && (
                  <ContextField label="Constraints" content={context.technical_boundaries} />
                )}
                {context.design_principles && (
                  <ContextField label="Design Direction" content={context.design_principles} />
                )}
              </div>

              {/* Assumptions & Questions — inline chips */}
              {(context.assumptions.length > 0 || context.open_questions.length > 0) && (
                <div className="mt-5 pt-4 border-t border-[#F0F0F0]">
                  {context.assumptions.length > 0 && (
                    <div className="mb-3">
                      <span className="text-[11px] font-semibold text-[#999999] uppercase tracking-wide">
                        Assumptions
                      </span>
                      <ul className="mt-1.5 space-y-1">
                        {context.assumptions.map((a, i) => (
                          <li key={i} className="flex items-start gap-2">
                            <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-[#E5E5E5] shrink-0" />
                            <span className="text-[13px] text-[#666666] leading-relaxed">{a}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {context.open_questions.length > 0 && (
                    <div>
                      <span className="text-[11px] font-semibold text-[#25785A] uppercase tracking-wide">
                        Open Questions
                      </span>
                      <ul className="mt-1.5 space-y-1">
                        {context.open_questions.map((q, i) => (
                          <li key={i} className="flex items-start gap-2">
                            <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-[#3FAF7A] shrink-0" />
                            <span className="text-[13px] text-[#666666] leading-relaxed">{q}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* Footer */}
              <div className="mt-5 pt-4 border-t border-[#E5E5E5] flex items-center justify-between flex-wrap gap-3">
                <span className="text-[12px] text-[#999999]">
                  v{version}
                  {context.generated_at && ` · Updated ${relativeTime(context.generated_at)}`}
                </span>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleGenerate()
                    }}
                    disabled={isGenerating}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-[#3FAF7A] bg-white border border-[#3FAF7A] rounded-xl hover:bg-[#E8F5E9] transition-colors disabled:opacity-50"
                  >
                    {isGenerating ? (
                      <>
                        <div className="w-3 h-3 border-2 border-[#3FAF7A] border-t-transparent rounded-full animate-spin" />
                        Regenerating...
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-3.5 h-3.5" />
                        Regenerate
                      </>
                    )}
                  </button>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleExport()
                    }}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-[#666666] bg-white border border-[#E5E5E5] rounded-xl hover:bg-gray-50 transition-colors"
                  >
                    <Download className="w-3.5 h-3.5" />
                    Export
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}

function ContextField({ label, content }: { label: string; content: string }) {
  if (!content) return null
  return (
    <div>
      <span className="text-[11px] font-semibold text-[#999999] uppercase tracking-wide">
        {label}
      </span>
      <p className="text-[13px] text-[#666666] leading-relaxed mt-1 whitespace-pre-line">{content}</p>
    </div>
  )
}
