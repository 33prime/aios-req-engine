'use client';

import { useState, useRef } from 'react';
import type { InfoRequest } from '@/types';
import api from '@/lib/api';
import { FileText, Upload, CheckCircle, User, Lightbulb, X } from 'lucide-react';

interface DocumentCardProps {
  request: InfoRequest;
  projectId: string;
  onUpload: () => void;
}

export default function DocumentCard({ request, projectId, onUpload }: DocumentCardProps) {
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isComplete = request.status === 'complete';
  const uploadedFiles = request.answer_data?.file_ids as string[] | undefined;

  const handleFileSelect = async (file: File) => {
    setUploading(true);
    try {
      await api.uploadFile(projectId, file, undefined, request.id);
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

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  const getPriorityBadge = () => {
    switch (request.priority) {
      case 'high':
        return <span className="badge badge-high">HIGH PRIORITY</span>;
      case 'medium':
        return <span className="badge badge-medium">MEDIUM</span>;
      case 'low':
        return <span className="badge badge-low">LOW</span>;
      default:
        return null;
    }
  };

  const getIcon = () => {
    // Map file types to icons
    const type = request.title.toLowerCase();
    if (type.includes('database') || type.includes('spreadsheet')) return '📊';
    if (type.includes('report')) return '📈';
    return '📄';
  };

  return (
    <div className={`info-item ${isComplete ? 'complete' : ''}`}>
      <div className="flex gap-3">
        {/* Icon */}
        <div className="text-2xl">{getIcon()}</div>

        {/* Content */}
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <h4 className="text-sm font-semibold text-gray-900">{request.title}</h4>
            {getPriorityBadge()}
          </div>

          {request.description && (
            <p className="text-sm text-gray-600 mb-2">{request.description}</p>
          )}

          {/* Meta info */}
          <div className="flex flex-wrap gap-3 text-xs text-gray-600 mb-3">
            {request.best_answered_by && (
              <span className="flex items-center gap-1">
                <User className="w-3 h-3" />
                Best provided by: <strong>{request.best_answered_by}</strong>
              </span>
            )}
          </div>

          {/* Why important */}
          {request.why_asking && (
            <div className="why-important">
              <div className="why-important-label">
                <Lightbulb className="w-3 h-3" />
                Why this is important
              </div>
              <p className="why-important-text">{request.why_asking}</p>
            </div>
          )}

          {/* Example formats hint */}
          {request.example_formats && request.example_formats.length > 0 && !isComplete && (
            <div className="mt-2 px-3 py-2 bg-gray-50 rounded-lg">
              <p className="text-xs text-gray-500">
                <span className="font-medium">Examples:</span>{' '}
                {request.example_formats.join(', ')}
              </p>
            </div>
          )}

          {/* Upload area or completion status */}
          {isComplete ? (
            <div className="mt-3 bg-white rounded-lg p-3 flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-success-text" />
              <span className="text-sm text-gray-900 font-medium">
                File uploaded
              </span>
              {request.completed_at && (
                <span className="text-xs text-gray-500 ml-auto">
                  {new Date(request.completed_at).toLocaleDateString()}
                </span>
              )}
            </div>
          ) : (
            <div
              className={`mt-3 border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
                dragOver ? 'border-primary bg-primary/5' : 'border-gray-300'
              }`}
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
            >
              {uploading ? (
                <div className="flex flex-col items-center gap-2">
                  <div className="spinner" />
                  <p className="text-sm text-gray-600">Uploading...</p>
                </div>
              ) : (
                <>
                  <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                  <p className="text-sm text-gray-600 mb-2">
                    Drag and drop a file, or
                  </p>
                  <input
                    ref={fileInputRef}
                    type="file"
                    onChange={handleInputChange}
                    className="hidden"
                  />
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="btn btn-secondary btn-small"
                  >
                    Choose File
                  </button>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
