/**
 * TypeScript types for the client portal.
 */

export type PortalPhase = 'pre_call' | 'post_call' | 'building' | 'testing';
export type InfoRequestPhase = 'pre_call' | 'post_call';
export type InfoRequestType = 'question' | 'document' | 'tribal_knowledge';
export type InfoRequestInputType = 'text' | 'file' | 'multi_text' | 'text_and_file';
export type InfoRequestPriority = 'high' | 'medium' | 'low' | 'none';
export type InfoRequestStatus = 'not_started' | 'in_progress' | 'complete' | 'skipped';
export type ContextSource = 'call' | 'dashboard' | 'chat' | 'manual';
export type DocumentCategory = 'client_uploaded' | 'consultant_shared';

export interface User {
  id: string;
  email: string;
  user_type: 'consultant' | 'client';
  first_name?: string;
  last_name?: string;
  company_name?: string;
  avatar_url?: string;
  has_seen_welcome: boolean;
  created_at: string;
  updated_at: string;
}

export interface PortalProject {
  id: string;
  name: string;
  client_display_name?: string;
  portal_phase: PortalPhase;
  discovery_call_date?: string;
  call_completed_at?: string;
  prototype_expected_date?: string;
  created_at: string;
}

export interface InfoRequest {
  id: string;
  project_id: string;
  phase: InfoRequestPhase;
  created_by: 'ai' | 'consultant';
  display_order: number;
  title: string;
  description?: string;
  context_from_call?: string;
  request_type: InfoRequestType;
  input_type: InfoRequestInputType;
  priority: InfoRequestPriority;
  best_answered_by?: string;
  can_delegate: boolean;
  status: InfoRequestStatus;
  answer_data?: Record<string, unknown>;
  completed_at?: string;
  completed_by?: string;
  auto_populates_to: string[];
  why_asking?: string;
  example_answer?: string;
  example_formats?: string[];  // Example file formats for document requests
  pro_tip?: string;
  created_at: string;
  updated_at: string;
}

export interface DashboardProgress {
  total_items: number;
  completed_items: number;
  percentage: number;
  status_breakdown: Record<string, number>;
}

export interface DashboardCallInfo {
  consultant_name: string;
  scheduled_date?: string;
  completed_date?: string;
  duration_minutes: number;
  description?: string;
}

export interface DashboardResponse {
  project_id: string;
  project_name: string;
  phase: PortalPhase;
  call_info?: DashboardCallInfo;
  progress: DashboardProgress;
  info_requests: InfoRequest[];
  due_date?: string;
}

export interface MetricItem {
  metric: string;
  current?: string;
  goal?: string;
  source?: ContextSource;
  locked: boolean;
}

export interface KeyUser {
  name: string;
  role?: string;
  frustrations: string[];
  helps: string[];
  source?: ContextSource;
  locked: boolean;
}

export interface DesignInspiration {
  name: string;
  url?: string;
  what_like?: string;
  source?: ContextSource;
}

export interface Competitor {
  name: string;
  worked?: string;
  didnt_work?: string;
  why_left?: string;
  source?: ContextSource;
  locked: boolean;
}

export interface CompletionScores {
  problem: number;
  success: number;
  users: number;
  design: number;
  competitors: number;
  tribal: number;
  files: number;
  overall: number;
}

export interface ProjectContext {
  id: string;
  project_id: string;

  // Problem section
  problem_main?: string;
  problem_main_source?: ContextSource;
  problem_main_locked: boolean;
  problem_why_now?: string;
  problem_why_now_source?: ContextSource;
  problem_why_now_locked: boolean;
  metrics: MetricItem[];

  // Success section
  success_future?: string;
  success_future_source?: ContextSource;
  success_future_locked: boolean;
  success_wow?: string;
  success_wow_source?: ContextSource;
  success_wow_locked: boolean;

  // Users
  key_users: KeyUser[];

  // Design
  design_love: DesignInspiration[];
  design_avoid?: string;
  design_avoid_source?: ContextSource;
  design_avoid_locked: boolean;

  // Competitors
  competitors: Competitor[];

  // Tribal knowledge
  tribal_knowledge: string[];
  tribal_source?: ContextSource;
  tribal_locked: boolean;

  // Scores
  completion_scores: CompletionScores;
  overall_completion: number;

  created_at: string;
  updated_at: string;
}

export interface ClientDocument {
  id: string;
  project_id: string;
  file_name: string;
  file_path: string;
  file_size: number;
  file_type: string;
  mime_type?: string;
  uploaded_by: string;
  category: DocumentCategory;
  extracted_text?: string;
  signal_id?: string;
  info_request_id?: string;
  description?: string;
  uploaded_at: string;
}
