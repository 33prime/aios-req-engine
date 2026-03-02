import { apiRequest } from './core'
import type { CallRecording, CallDetails } from '@/types/call-intelligence'

// List recordings for a project
export const listCallRecordings = (projectId: string, status?: string) =>
  apiRequest<CallRecording[]>(
    `/call-intelligence/recordings?project_id=${projectId}${status ? `&status=${status}` : ''}`
  )

// Get single recording
export const getCallRecording = (recordingId: string) =>
  apiRequest<CallRecording>(`/call-intelligence/recordings/${recordingId}`)

// Get full details (transcript + analysis + children)
export const getCallDetails = (recordingId: string) =>
  apiRequest<CallDetails>(`/call-intelligence/recordings/${recordingId}/details`)

// Trigger re-analysis
export const analyzeRecording = (recordingId: string, packs?: string) =>
  apiRequest<{ status: string; recording_id: string }>(
    `/call-intelligence/recordings/${recordingId}/analyze`,
    {
      method: 'POST',
      body: JSON.stringify({ dimension_packs: packs ?? null }),
    }
  )

// Schedule recording from a meeting
export const scheduleCallRecording = (meetingId: string, projectId: string) =>
  apiRequest<{ recording_id: string; recall_bot_id: string }>(
    `/call-intelligence/meetings/${meetingId}/record?project_id=${projectId}`,
    { method: 'POST' }
  )
