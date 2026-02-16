'use client'

import { useState } from 'react'
import { FileText } from 'lucide-react'
import type { ProcessDocumentSummary } from '@/types/workspace'
import { ProcessDocumentCard } from './ProcessDocumentCard'
import { ProcessDocumentDetailDrawer } from './ProcessDocumentDetailDrawer'

interface ClientDocumentsTabProps {
  docs: ProcessDocumentSummary[]
}

export function ClientDocumentsTab({ docs }: ClientDocumentsTabProps) {
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null)

  const drafts = docs.filter((d) => d.status === 'draft')
  const confirmed = docs.filter((d) => d.status === 'confirmed')
  const others = docs.filter((d) => d.status !== 'draft' && d.status !== 'confirmed')

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl border border-[#E5E5E5] shadow-md p-6">
        <div className="flex items-center gap-2 mb-1">
          <FileText className="w-4 h-4 text-[#666]" />
          <h3 className="text-[14px] font-semibold text-[#333]">Process Documents</h3>
          <span className="text-[11px] text-[#999]">{docs.length} total</span>
        </div>
        <p className="text-[12px] text-[#999] mb-5">
          Structured business process documentation generated from knowledge base items.
        </p>

        {docs.length === 0 ? (
          <div className="text-center py-12">
            <FileText className="w-8 h-8 text-[#CCC] mx-auto mb-2" />
            <p className="text-[13px] text-[#666]">No documents yet</p>
            <p className="text-[12px] text-[#999] mt-1">
              Generate documents from KB items in the Overview tab
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {confirmed.length > 0 && (
              <div>
                <p className="text-[12px] font-semibold text-[#999] uppercase tracking-wide mb-3">Confirmed</p>
                <div className="space-y-2">
                  {confirmed.map((doc) => (
                    <ProcessDocumentCard key={doc.id} doc={doc} onClick={() => setSelectedDocId(doc.id)} />
                  ))}
                </div>
              </div>
            )}
            {drafts.length > 0 && (
              <div>
                {confirmed.length > 0 && (
                  <p className="text-[12px] font-semibold text-[#999] uppercase tracking-wide mb-3">Drafts</p>
                )}
                <div className="space-y-2">
                  {drafts.map((doc) => (
                    <ProcessDocumentCard key={doc.id} doc={doc} onClick={() => setSelectedDocId(doc.id)} />
                  ))}
                </div>
              </div>
            )}
            {others.length > 0 && (
              <div>
                <p className="text-[12px] font-semibold text-[#999] uppercase tracking-wide mb-3">Other</p>
                <div className="space-y-2">
                  {others.map((doc) => (
                    <ProcessDocumentCard key={doc.id} doc={doc} onClick={() => setSelectedDocId(doc.id)} />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {selectedDocId && (
        <ProcessDocumentDetailDrawer
          docId={selectedDocId}
          onClose={() => setSelectedDocId(null)}
        />
      )}
    </div>
  )
}
