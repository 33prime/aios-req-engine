import { apiRequest } from './core'
import type { CallRecording, CallDetails, CallStrategyBrief } from '@/types/call-intelligence'

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

// Get the recording linked to a meeting
export const getRecordingForMeeting = (meetingId: string) =>
  apiRequest<CallRecording>(`/call-intelligence/meetings/${meetingId}/recording`)

// Seed a recording from a public audio URL
export const seedRecording = (projectId: string, audioUrl: string, title?: string, meetingId?: string) =>
  apiRequest<{ recording_id: string; status: string }>(
    `/call-intelligence/recordings/seed?project_id=${projectId}&audio_url=${encodeURIComponent(audioUrl)}${title ? `&title=${encodeURIComponent(title)}` : ''}${meetingId ? `&meeting_id=${meetingId}` : ''}`,
    { method: 'POST' }
  )

// Generate a pre-call strategy brief
export const generateStrategyBrief = (projectId: string, meetingId?: string) =>
  apiRequest<{ status: string; project_id: string }>(
    '/call-intelligence/strategy-brief/generate',
    {
      method: 'POST',
      body: JSON.stringify({ project_id: projectId, meeting_id: meetingId ?? null }),
    }
  )

// Get a strategy brief by ID
export const getStrategyBrief = (briefId: string) =>
  apiRequest<CallStrategyBrief>(`/call-intelligence/strategy-brief/${briefId}`)

// Get strategy brief linked to a meeting
export const getBriefForMeeting = (meetingId: string) =>
  apiRequest<CallStrategyBrief>(`/call-intelligence/strategy-brief/meeting/${meetingId}`)

// Get strategy brief linked to a recording
export const getBriefForRecording = (recordingId: string) =>
  apiRequest<CallStrategyBrief>(`/call-intelligence/strategy-brief/recording/${recordingId}`)

// List strategy briefs for a project
export const listStrategyBriefs = (projectId: string, limit = 20) =>
  apiRequest<CallStrategyBrief[]>(
    `/call-intelligence/strategy-briefs?project_id=${projectId}&limit=${limit}`
  )
