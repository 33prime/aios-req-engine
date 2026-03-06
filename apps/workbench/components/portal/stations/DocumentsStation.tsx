'use client'

import { useState, useEffect } from 'react'
import { FileText, Upload } from 'lucide-react'
import { apiRequest } from '@/lib/api/core'

interface ClientDocument {
  id: string
  file_name: string
  file_size: number
  file_type: string
  description?: string | null
  created_at: string
}

interface DocumentsStationProps {
  projectId: string
}

export function DocumentsStation({ projectId }: DocumentsStationProps) {
  const [docs, setDocs] = useState<ClientDocument[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiRequest<ClientDocument[]>(`/portal/projects/${projectId}/documents`)
      .then(setDocs)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [projectId])

  if (loading) {
    return <p className="text-xs text-text-muted text-center py-4">Loading documents...</p>
  }

  if (docs.length === 0) {
    return (
      <div className="text-center py-4">
        <Upload className="w-6 h-6 text-text-placeholder mx-auto mb-2" />
        <p className="text-xs text-text-muted">No documents uploaded yet.</p>
        <p className="text-xs text-text-placeholder mt-1">
          Upload files via the Materials page or chat below about what documents would help.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {docs.map((doc) => (
        <div key={doc.id} className="bg-surface-subtle rounded-lg px-3 py-2 flex items-center gap-2">
          <FileText className="w-4 h-4 text-text-muted flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-text-primary truncate">{doc.file_name}</p>
            <p className="text-[10px] text-text-placeholder">
              {(doc.file_size / 1024).toFixed(0)} KB &middot; {doc.file_type}
            </p>
          </div>
        </div>
      ))}
      <p className="text-[10px] text-text-placeholder text-center pt-1">Chat below to discuss what else to share</p>
    </div>
  )
}
