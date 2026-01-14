/**
 * API client for the client portal.
 * Handles authentication and requests to the backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/v1';

interface ApiOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  body?: unknown;
  headers?: Record<string, string>;
}

class ApiClient {
  private accessToken: string | null = null;

  setAccessToken(token: string | null) {
    this.accessToken = token;
  }

  async request<T>(endpoint: string, options: ApiOptions = {}): Promise<T> {
    const { method = 'GET', body, headers = {} } = options;

    const requestHeaders: Record<string, string> = {
      'Content-Type': 'application/json',
      ...headers,
    };

    if (this.accessToken) {
      requestHeaders['Authorization'] = `Bearer ${this.accessToken}`;
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      method,
      headers: requestHeaders,
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Auth endpoints
  async sendMagicLink(email: string, redirectUrl?: string) {
    return this.request('/auth/magic-link', {
      method: 'POST',
      body: { email, redirect_url: redirectUrl },
    });
  }

  async verifyToken(token: string, tokenHash?: string) {
    return this.request('/auth/verify', {
      method: 'POST',
      body: { token, token_hash: tokenHash },
    });
  }

  async getCurrentUser() {
    return this.request('/auth/me');
  }

  async updateUser(data: { first_name?: string; last_name?: string; company_name?: string }) {
    return this.request('/auth/me', { method: 'PATCH', body: data });
  }

  async markWelcomeSeen() {
    return this.request('/auth/me/welcome-seen', { method: 'POST' });
  }

  // Portal endpoints
  async getProjects() {
    return this.request('/portal/projects');
  }

  async getProject(projectId: string) {
    return this.request(`/portal/projects/${projectId}`);
  }

  async getDashboard(projectId: string) {
    return this.request(`/portal/projects/${projectId}/dashboard`);
  }

  async getInfoRequests(projectId: string, phase?: 'pre_call' | 'post_call') {
    const params = phase ? `?phase=${phase}` : '';
    return this.request(`/portal/projects/${projectId}/info-requests${params}`);
  }

  async answerInfoRequest(requestId: string, answerData: Record<string, unknown>, status = 'complete') {
    return this.request(`/portal/info-requests/${requestId}`, {
      method: 'PATCH',
      body: { answer_data: answerData, status },
    });
  }

  async updateInfoRequestStatus(requestId: string, status: string) {
    return this.request(`/portal/info-requests/${requestId}/status?status=${status}`, {
      method: 'PATCH',
    });
  }

  // Context endpoints
  async getContext(projectId: string) {
    return this.request(`/portal/projects/${projectId}/context`);
  }

  async updateContextSection(projectId: string, section: string, data: Record<string, unknown>) {
    return this.request(`/portal/projects/${projectId}/context/${section}`, {
      method: 'PATCH',
      body: data,
    });
  }

  async lockContextSection(projectId: string, section: string, field?: string) {
    const params = field ? `?field=${field}` : '';
    return this.request(`/portal/projects/${projectId}/context/lock?section=${section}${params}`, {
      method: 'POST',
    });
  }

  // File endpoints
  async getFiles(projectId: string, category?: 'client_uploaded' | 'consultant_shared') {
    const params = category ? `?category=${category}` : '';
    return this.request(`/portal/projects/${projectId}/files${params}`);
  }

  async uploadFile(projectId: string, file: File, description?: string, infoRequestId?: string) {
    const formData = new FormData();
    formData.append('file', file);
    if (description) formData.append('description', description);
    if (infoRequestId) formData.append('info_request_id', infoRequestId);

    const response = await fetch(`${API_BASE}/portal/projects/${projectId}/files`, {
      method: 'POST',
      headers: this.accessToken ? { Authorization: `Bearer ${this.accessToken}` } : {},
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  async deleteFile(documentId: string) {
    return this.request(`/portal/files/${documentId}`, { method: 'DELETE' });
  }

  // Chat endpoint (streaming)
  async clientChat(
    projectId: string,
    params: {
      message: string;
      conversation_id?: string;
      conversation_history?: Array<{ role: string; content: string }>;
    }
  ): Promise<Response> {
    const requestHeaders: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (this.accessToken) {
      requestHeaders['Authorization'] = `Bearer ${this.accessToken}`;
    }

    const response = await fetch(`${API_BASE}/portal/projects/${projectId}/chat`, {
      method: 'POST',
      headers: requestHeaders,
      body: JSON.stringify(params),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Chat request failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response;
  }

  // Chat history
  async getChatHistory(projectId: string, conversationId: string) {
    return this.request(`/portal/projects/${projectId}/chat/history?conversation_id=${conversationId}`);
  }
}

export const api = new ApiClient();
export default api;
