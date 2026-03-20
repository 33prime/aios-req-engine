import { apiRequest } from './core'
import type {
  IntelLayerAgent,
  IntelLayerResponse,
  AgentChatMessage,
  AgentExecutionResult,
} from '@/types/workspace'

const prefix = (projectId: string) =>
  `/projects/${projectId}/workspace/intelligence-layer`

// ── Generate ──

export const generateIntelligenceLayer = (projectId: string) =>
  apiRequest<IntelLayerResponse>(`${prefix(projectId)}/generate`, {
    method: 'POST',
  })

// ── Agent CRUD ──

export const getIntelligenceAgents = (projectId: string) =>
  apiRequest<IntelLayerResponse>(`${prefix(projectId)}/agents`)

export const getIntelligenceAgent = (projectId: string, agentId: string) =>
  apiRequest<IntelLayerAgent>(`${prefix(projectId)}/agents/${agentId}`)

export const updateIntelligenceAgent = (
  projectId: string,
  agentId: string,
  data: Partial<IntelLayerAgent>,
) =>
  apiRequest<IntelLayerAgent>(`${prefix(projectId)}/agents/${agentId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })

export const deleteIntelligenceAgent = (projectId: string, agentId: string) =>
  apiRequest<{ ok: boolean }>(`${prefix(projectId)}/agents/${agentId}`, {
    method: 'DELETE',
  })

// ── Tools ──

export const updateAgentTool = (
  projectId: string,
  agentId: string,
  toolId: string,
  data: Record<string, unknown>,
) =>
  apiRequest<Record<string, unknown>>(
    `${prefix(projectId)}/agents/${agentId}/tools/${toolId}`,
    { method: 'PATCH', body: JSON.stringify(data) },
  )

// ── Chat ──

export const getAgentChatHistory = (projectId: string, agentId: string) =>
  apiRequest<{ messages: AgentChatMessage[] }>(
    `${prefix(projectId)}/agents/${agentId}/chat`,
  )

export const sendAgentChatMessage = (
  projectId: string,
  agentId: string,
  message: string,
) =>
  apiRequest<{ response: string; message_id: string }>(
    `${prefix(projectId)}/agents/${agentId}/chat`,
    { method: 'POST', body: JSON.stringify({ message }) },
  )

// ── Execution ──

export const executeAgent = (
  projectId: string,
  agentId: string,
  inputText: string,
) =>
  apiRequest<AgentExecutionResult>(
    `${prefix(projectId)}/agents/${agentId}/execute`,
    { method: 'POST', body: JSON.stringify({ input_text: inputText }) },
  )

// ── Validation ──

export const validateAgent = (
  projectId: string,
  agentId: string,
  executionId: string,
  verdict: 'confirmed' | 'adjusted',
  notes?: string,
) =>
  apiRequest<{ ok: boolean; validation_status: string }>(
    `${prefix(projectId)}/agents/${agentId}/validate`,
    {
      method: 'POST',
      body: JSON.stringify({
        execution_id: executionId,
        verdict,
        notes: notes || null,
      }),
    },
  )
