/**
 * DocumentUploadModal Component
 *
 * Modal for uploading documents to a project.
 * Supports drag-and-drop and file picker.
 */

'use client'

import { useState, useRef, useCallback } from 'react'
import { X, Upload, FileText, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'
import { uploadDocument, processDocument, type DocumentUploadResponse } from '@/lib/api'

interface DocumentUploadModalProps {
  projectId: string
  isOpen: boolean
  onClose: () => void
  onUploadComplete?: () => void
}

const ACCEPTED_TYPES = {
  'application/pdf': 'PDF',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'Word',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'Excel',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'PowerPoint',
  'image/png': 'PNG',
  'image/jpeg': 'JPEG',
  'image/webp': 'WebP',
  'image/gif': 'GIF',
}

const MAX_FILE_SIZE = 15 * 1024 * 1024 // 15MB

type UploadStatus = 'idle' | 'uploading' | 'processing' | 'success' | 'error'

interface FileUpload {
  file: File
  status: UploadStatus
  progress: number
  error?: string
  result?: DocumentUploadResponse
}

export function DocumentUploadModal({
  projectId,
  isOpen,
  onClose,
  onUploadComplete,
}: DocumentUploadModalProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [uploads, setUploads] = useState<FileUpload[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const validateFile = (file: File): string | null => {
    if (!Object.keys(ACCEPTED_TYPES).includes(file.type)) {
      return `Unsupported file type: ${file.type || 'unknown'}`
    }
    if (file.size > MAX_FILE_SIZE) {
      return `File too large: ${(file.size / 1024 / 1024).toFixed(1)}MB (max 15MB)`
    }
    return null
  }

  const uploadFile = async (fileUpload: FileUpload, index: number) => {
    try {
      // Update status to uploading
      setUploads(prev => prev.map((u, i) =>
        i === index ? { ...u, status: 'uploading' as UploadStatus, progress: 10 } : u
      ))

      // Upload the file
      const result = await uploadDocument(projectId, fileUpload.file)

      // Update with result
      setUploads(prev => prev.map((u, i) =>
        i === index ? { ...u, status: 'processing' as UploadStatus, progress: 50, result } : u
      ))

      // Trigger processing if not a duplicate
      if (!result.is_duplicate && result.processing_status === 'pending') {
        await processDocument(result.id)
      }

      // Mark as success
      setUploads(prev => prev.map((u, i) =>
        i === index ? { ...u, status: 'success' as UploadStatus, progress: 100 } : u
      ))

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Upload failed'
      setUploads(prev => prev.map((u, i) =>
        i === index ? { ...u, status: 'error' as UploadStatus, error: errorMessage } : u
      ))
    }
  }

  const handleFiles = async (files: FileList | File[]) => {
    const fileArray = Array.from(files).slice(0, 5) // Max 5 files

    // Create upload objects with validation
    const newUploads: FileUpload[] = fileArray.map(file => {
      const error = validateFile(file)
      return {
        file,
        status: error ? 'error' as UploadStatus : 'idle' as UploadStatus,
        progress: 0,
        error: error || undefined,
      }
    })

    setUploads(prev => [...prev, ...newUploads])

    // Upload valid files
    const startIndex = uploads.length
    for (let i = 0; i < newUploads.length; i++) {
      if (!newUploads[i].error) {
        await uploadFile(newUploads[i], startIndex + i)
      }
    }
  }

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    handleFiles(e.dataTransfer.files)
  }, [uploads.length])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      handleFiles(e.target.files)
    }
  }

  const handleClose = () => {
    // Check if any uploads completed
    const hasCompleted = uploads.some(u => u.status === 'success')
    if (hasCompleted && onUploadComplete) {
      onUploadComplete()
    }
    setUploads([])
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="relative bg-white rounded-xl shadow-xl w-full max-w-lg mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Upload Documents</h2>
          <button
            onClick={handleClose}
            className="p-1 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {/* Drop zone */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`
              border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors
              ${isDragging
                ? 'border-brand-primary bg-brand-primary/5'
                : 'border-gray-300 hover:border-gray-400'
              }
            `}
          >
            <Upload className={`w-10 h-10 mx-auto mb-3 ${isDragging ? 'text-brand-primary' : 'text-gray-400'}`} />
            <p className="text-sm text-gray-600 mb-1">
              <span className="font-medium text-brand-primary">Click to upload</span> or drag and drop
            </p>
            <p className="text-xs text-gray-400">
              PDF, Word, Excel, PowerPoint, or images (max 15MB)
            </p>
          </div>

          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept={Object.keys(ACCEPTED_TYPES).join(',')}
            onChange={handleFileSelect}
            className="hidden"
          />

          {/* Upload list */}
          {uploads.length > 0 && (
            <div className="mt-4 space-y-2">
              {uploads.map((upload, index) => (
                <div
                  key={index}
                  className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg"
                >
                  <FileText className="w-5 h-5 text-gray-400 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {upload.file.name}
                    </p>
                    {upload.error && (
                      <p className="text-xs text-red-600">{upload.error}</p>
                    )}
                    {upload.status === 'processing' && (
                      <p className="text-xs text-gray-500">Processing...</p>
                    )}
                    {upload.result?.is_duplicate && (
                      <p className="text-xs text-amber-600">Duplicate file</p>
                    )}
                  </div>
                  <div className="flex-shrink-0">
                    {upload.status === 'uploading' && (
                      <Loader2 className="w-5 h-5 text-brand-primary animate-spin" />
                    )}
                    {upload.status === 'processing' && (
                      <Loader2 className="w-5 h-5 text-brand-primary animate-spin" />
                    )}
                    {upload.status === 'success' && (
                      <CheckCircle className="w-5 h-5 text-green-500" />
                    )}
                    {upload.status === 'error' && (
                      <AlertCircle className="w-5 h-5 text-red-500" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200">
          <button
            onClick={handleClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900"
          >
            {uploads.some(u => u.status === 'success') ? 'Done' : 'Cancel'}
          </button>
        </div>
      </div>
    </div>
  )
}
