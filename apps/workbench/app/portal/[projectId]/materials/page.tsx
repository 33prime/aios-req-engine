/**
 * Materials Page
 *
 * Reuses existing file endpoints. Groups: "Your Uploads" vs "Shared by Consultant".
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import { useParams } from 'next/navigation'
import { Spinner } from '@/components/ui/Spinner'
import { apiRequest } from '@/lib/api/core'

interface ClientDocument {
  id: string
  file_name: string
  file_size: number
  file_type: string
  description?: string
  category: 'client_uploaded' | 'consultant_shared'
  uploaded_at: string
  uploaded_by: string
}

export default function MaterialsPage() {
  const params = useParams()
  const projectId = params.projectId as string

  const [loading, setLoading] = useState(true)
  const [documents, setDocuments] = useState<ClientDocument[]>([])
  const [error, setError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)

  const loadDocuments = useCallback(async () => {
    try {
      setError(null)
      const data = await apiRequest<ClientDocument[]>(
        `/portal/projects/${projectId}/files`
      )
      setDocuments(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    loadDocuments()
  }, [loadDocuments])

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)

      await fetch(`/api/v1/portal/projects/${projectId}/files`, {
        method: 'POST',
        body: formData,
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`,
        },
      })
      await loadDocuments()
    } catch (err) {
      console.error('Upload failed:', err)
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  const handleDelete = async (docId: string) => {
    if (!confirm('Delete this file?')) return
    try {
      await apiRequest(`/portal/files/${docId}`, { method: 'DELETE' })
      await loadDocuments()
    } catch (err) {
      console.error('Delete failed:', err)
    }
  }

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Spinner size="lg" label="Loading materials..." />
      </div>
    )
  }

  const myUploads = documents.filter(d => d.category === 'client_uploaded')
  const shared = documents.filter(d => d.category === 'consultant_shared')

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Materials</h1>
          <p className="text-text-muted mt-1">Project documents and files.</p>
        </div>
        <label className="px-4 py-2 bg-brand-primary text-white text-sm font-medium rounded-lg hover:bg-brand-primary-hover transition-colors cursor-pointer">
          {uploading ? 'Uploading...' : 'Upload File'}
          <input
            type="file"
            onChange={handleUpload}
            className="hidden"
            disabled={uploading}
          />
        </label>
      </div>

      {error && (
        <div className="bg-red-50 text-red-600 rounded-lg p-3 text-sm">{error}</div>
      )}

      {/* Your Uploads */}
      <div className="space-y-3">
        <h2 className="text-sm font-medium text-text-muted uppercase tracking-wide">
          Your Uploads ({myUploads.length})
        </h2>

        {myUploads.length === 0 ? (
          <div className="bg-surface-card rounded-lg border border-border p-8 text-center">
            <p className="text-text-placeholder">No files uploaded yet.</p>
          </div>
        ) : (
          myUploads.map(doc => (
            <div key={doc.id} className="bg-surface-card rounded-lg border border-border p-4 flex items-center justify-between shadow-sm">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-10 h-10 bg-surface-subtle rounded-lg flex items-center justify-center flex-shrink-0">
                  <span className="text-xs font-medium text-text-muted uppercase">
                    {doc.file_type?.split('/').pop()?.slice(0, 4) || 'FILE'}
                  </span>
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-text-primary truncate">{doc.file_name}</p>
                  <p className="text-xs text-text-placeholder">
                    {formatSize(doc.file_size)} &middot; {new Date(doc.uploaded_at).toLocaleDateString()}
                  </p>
                </div>
              </div>
              <button
                onClick={() => handleDelete(doc.id)}
                className="text-xs text-red-500 hover:text-red-700 ml-3"
              >
                Delete
              </button>
            </div>
          ))
        )}
      </div>

      {/* Shared by Consultant */}
      <div className="space-y-3">
        <h2 className="text-sm font-medium text-text-muted uppercase tracking-wide">
          Shared by Consultant ({shared.length})
        </h2>

        {shared.length === 0 ? (
          <div className="bg-surface-card rounded-lg border border-border p-8 text-center">
            <p className="text-text-placeholder">No shared materials yet.</p>
          </div>
        ) : (
          shared.map(doc => (
            <div key={doc.id} className="bg-surface-card rounded-lg border border-border p-4 flex items-center gap-3 shadow-sm">
              <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center flex-shrink-0">
                <span className="text-xs font-medium text-blue-600 uppercase">
                  {doc.file_type?.split('/').pop()?.slice(0, 4) || 'FILE'}
                </span>
              </div>
              <div className="min-w-0">
                <p className="text-sm font-medium text-text-primary truncate">{doc.file_name}</p>
                <p className="text-xs text-text-placeholder">
                  {formatSize(doc.file_size)} &middot; {new Date(doc.uploaded_at).toLocaleDateString()}
                </p>
                {doc.description && (
                  <p className="text-xs text-text-muted mt-0.5">{doc.description}</p>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
