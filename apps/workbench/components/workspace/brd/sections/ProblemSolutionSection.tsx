'use client'

import { AlertCircle, Lightbulb } from 'lucide-react'
import { NarrativeEditor } from '../components/NarrativeEditor'

interface ProblemSolutionSectionProps {
  macroOutcome?: string | null
  outcomeThesis?: string | null
  projectId: string
  projectType?: string
  onUpdateMacroOutcome: (value: string) => void
  onUpdateOutcomeThesis: (value: string) => void
}

export function ProblemSolutionSection({
  macroOutcome,
  outcomeThesis,
  projectId,
  projectType = 'new_product',
  onUpdateMacroOutcome,
  onUpdateOutcomeThesis,
}: ProblemSolutionSectionProps) {
  const isInternal = projectType === 'internal'
  const problemLabel = isInternal ? 'Process Problem' : 'Market Problem'
  const solutionLabel = isInternal ? 'Proposed Improvement' : 'Proposed Solution'

  return (
    <section className="space-y-8">
      <div>
        <h2 className="text-lg font-semibold text-text-body mb-3 flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-[#C49A1A]" />
          {problemLabel}
        </h2>
        <div className="bg-white rounded-2xl shadow-md border border-border p-5">
          <NarrativeEditor
            field="macro_outcome"
            label={problemLabel}
            currentValue={macroOutcome}
            projectId={projectId}
            onSave={onUpdateMacroOutcome}
            placeholder={isInternal
              ? "Describe the process problem this initiative addresses..."
              : "Describe the market problem or opportunity this product addresses..."
            }
          />
        </div>
      </div>

      <div>
        <h2 className="text-lg font-semibold text-text-body mb-3 flex items-center gap-2">
          <Lightbulb className="w-5 h-5 text-[#3FAF7A]" />
          {solutionLabel}
        </h2>
        <div className="bg-white rounded-2xl shadow-md border border-border p-5">
          <NarrativeEditor
            field="outcome_thesis"
            label={solutionLabel}
            currentValue={outcomeThesis}
            projectId={projectId}
            onSave={onUpdateOutcomeThesis}
            placeholder={isInternal
              ? "Describe how the proposed improvement addresses the process problem..."
              : "Describe the proposed solution approach and why it will work..."
            }
          />
        </div>
      </div>
    </section>
  )
}
