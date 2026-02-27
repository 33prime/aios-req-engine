'use client'

import { useEffect, useState } from 'react'
import dynamic from 'next/dynamic'
import { getEvalPromptDiff } from '@/lib/api'
import type { EvalPromptDiff } from '@/types/api'

// Dynamic import — react-diff-viewer-continued uses a regex that breaks Node 20 SSG
const ReactDiffViewer = dynamic(
  () => import('react-diff-viewer-continued').then(mod => mod.default),
  { ssr: false }
)

// Import enum type for compareMethod
enum DiffMethod {
  WORDS = 'diffWords',
}

interface Props {
  versionId: string
}

export function PromptDiffViewer({ versionId }: Props) {
  const [diff, setDiff] = useState<EvalPromptDiff | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    getEvalPromptDiff(versionId)
      .then(setDiff)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [versionId])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-32">
        <div className="w-4 h-4 border-2 border-brand-primary border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!diff) {
    return <p className="text-[13px] text-text-placeholder">Failed to load diff</p>
  }

  return (
    <div className="text-[12px] overflow-x-auto rounded-lg border border-border">
      <ReactDiffViewer
        oldValue={diff.version_a.prompt_text}
        newValue={diff.version_b.prompt_text}
        splitView={false}
        compareMethod={DiffMethod.WORDS}
        leftTitle={`v${diff.version_a.version_number || 'base'}`}
        rightTitle={`v${diff.version_b.version_number}`}
        styles={{
          variables: {
            light: {
              diffViewerBackground: '#fff',
              addedBackground: '#E8F5E9',
              removedBackground: '#FEE2E2',
              wordAddedBackground: '#bbf7d0',
              wordRemovedBackground: '#fecaca',
            },
          },
          contentText: { fontSize: '12px', lineHeight: '1.5' },
        }}
      />
    </div>
  )
}
