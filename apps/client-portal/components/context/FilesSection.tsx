'use client';

import { useRef, useState } from 'react';
import type { ClientDocument } from '@/types';
import api from '@/lib/api';
import { FileText, Upload, Download, Trash2 } from 'lucide-react';

interface FilesSectionProps {
  files: ClientDocument[];
  projectId: string;
  onUpload: () => void;
}

export default function FilesSection({ files, projectId, onUpload }: FilesSectionProps) {
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const clientFiles = files.filter((f) => f.category === 'client_uploaded');
  const consultantFiles = files.filter((f) => f.category === 'consultant_shared');

  const handleFileSelect = async (file: File) => {
    setUploading(true);
    try {
      await api.uploadFile(projectId, file);
      onUpload();
    } catch (error) {
      console.error('Upload error:', error);
    } finally {
      setUploading(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  const handleDelete = async (documentId: string) => {
    if (!confirm('Delete this file?')) return;
    try {
      await api.deleteFile(documentId);
      onUpload();
    } catch (error) {
      console.error('Delete error:', error);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getFileIcon = (type: string) => {
    if (type.includes('spreadsheet') || type === 'xlsx' || type === 'csv') return '📊';
    if (type.includes('pdf') || type === 'pdf') return '📈';
    return '📄';
  };

  return (
    <div className="context-section">
      <div className="flex items-center gap-2 mb-6">
        <span className="text-2xl">📁</span>
        <h2 className="text-xl font-semibold text-gray-900">Files & Assets</h2>
      </div>

      <h3 className="text-sm font-medium text-gray-700 mb-3">Documents and examples</h3>

      {/* Client uploaded files */}
      {clientFiles.length > 0 && (
        <div className="mb-6">
          <p className="text-sm font-semibold text-gray-900 mb-3">
            Uploaded by You ({clientFiles.length})
          </p>
          <div className="space-y-2">
            {clientFiles.map((file) => (
              <FileItem
                key={file.id}
                file={file}
                icon={getFileIcon(file.file_type)}
                formatSize={formatFileSize}
                onDelete={() => handleDelete(file.id)}
                canDelete
              />
            ))}
          </div>
        </div>
      )}

      {/* Upload button */}
      <div className="mb-6">
        <input
          ref={fileInputRef}
          type="file"
          onChange={handleInputChange}
          className="hidden"
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="btn btn-secondary btn-small"
        >
          {uploading ? (
            <span className="spinner w-4 h-4" />
          ) : (
            <>
              <Upload className="w-3 h-3" />
              Upload file
            </>
          )}
        </button>
      </div>

      {/* Consultant shared files */}
      {consultantFiles.length > 0 && (
        <div>
          <p className="text-sm font-semibold text-gray-900 mb-3">
            Shared by Matt ({consultantFiles.length})
          </p>
          <div className="space-y-2">
            {consultantFiles.map((file) => (
              <FileItem
                key={file.id}
                file={file}
                icon={getFileIcon(file.file_type)}
                formatSize={formatFileSize}
              />
            ))}
          </div>
        </div>
      )}

      {files.length === 0 && (
        <div className="empty-state">
          <p>No files uploaded yet</p>
        </div>
      )}
    </div>
  );
}

function FileItem({
  file,
  icon,
  formatSize,
  onDelete,
  canDelete = false,
}: {
  file: ClientDocument;
  icon: string;
  formatSize: (bytes: number) => string;
  onDelete?: () => void;
  canDelete?: boolean;
}) {
  return (
    <div className="file-item">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 bg-emerald-50 rounded-lg flex items-center justify-center text-lg">
          {icon}
        </div>
        <div>
          <div className="text-sm font-medium text-gray-900">{file.file_name}</div>
          <div className="text-xs text-gray-500">
            {formatSize(file.file_size)} • {new Date(file.uploaded_at).toLocaleDateString()}
          </div>
        </div>
      </div>
      <div className="flex gap-2">
        <button className="btn btn-secondary btn-small">
          <Download className="w-3 h-3" />
        </button>
        {canDelete && onDelete && (
          <button
            onClick={onDelete}
            className="btn btn-secondary btn-small text-red-600 hover:bg-red-50"
          >
            <Trash2 className="w-3 h-3" />
          </button>
        )}
      </div>
    </div>
  );
}
