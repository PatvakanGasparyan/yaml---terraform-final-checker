import { API_URL } from './utils';

export function getApiBaseUrl(): string {
  if (typeof window !== 'undefined') {
    return `${window.location.origin}/api/v1`;
  }
  return `${API_URL}/api/v1`;
}

export function formatApiError(detail: unknown): string {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) =>
        typeof item === 'object' && item && 'msg' in item ? String(item.msg) : String(item)
      )
      .join(', ');
  }
  if (detail && typeof detail === 'object' && 'message' in detail) {
    return String((detail as { message: string }).message);
  }
  return 'Request failed';
}

interface RequestOptions extends RequestInit {}

class ApiClient {
  private resolveBaseUrl(): string {
    return getApiBaseUrl();
  }

  private getHeaders(): HeadersInit {
    return { 'Content-Type': 'application/json', Accept: 'application/json' };
  }

  async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    let response: Response;
    try {
      response = await fetch(`${this.resolveBaseUrl()}${endpoint}`, {
        ...options,
        headers: { ...this.getHeaders(), ...options.headers },
      });
    } catch {
      throw new Error(
        'Cannot reach the API server. Ensure Docker is running: docker compose up -d'
      );
    }

    if (!response.ok) {
      const text = await response.text();
      let detail: unknown = `HTTP ${response.status}`;
      try {
        const parsed = JSON.parse(text) as { detail?: unknown; message?: string };
        detail = parsed.detail ?? parsed.message ?? text.slice(0, 300);
      } catch {
        detail = text.slice(0, 300) || `HTTP ${response.status}`;
      }
      throw new Error(formatApiError(detail));
    }

    if (response.status === 204) return undefined as T;
    const text = await response.text();
    if (!text) return undefined as T;
    return JSON.parse(text) as T;
  }

  async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  async post<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }
}

export const api = new ApiClient();

export interface DashboardData {
  stats: {
    total_scans: number;
    failed_validations: number;
    successful_validations: number;
    security_findings: number;
    terraform_projects: number;
    yaml_projects: number;
    ai_recommendations: number;
  };
  charts: {
    validation_trends: { date: string; value: number }[];
    security_trends: { date: string; value: number }[];
    repository_stats: { date: string; value: number }[];
    scan_performance: { date: string; value: number }[];
  };
  recent_activity: {
    id: number;
    activity_type: string;
    title: string;
    description?: string;
    user_name: string;
    created_at: string;
  }[];
  ai_recommendations: string[];
}

export interface ValidationFinding {
  file_path: string;
  line_number?: number;
  severity: string;
  category: string;
  message: string;
  original_code?: string;
  corrected_code?: string;
  correction_reason?: string;
  impact?: string;
}

export interface SecurityFinding {
  scanner: string;
  rule_id: string;
  severity: string;
  title: string;
  description?: string;
  file_path: string;
  line_number?: number;
  remediation?: string;
}

export interface LineExplanation {
  line_number: number;
  code: string;
  explanation: string;
  risk_level: string;
  recommendation?: string;
}

export interface ValidationResult {
  validation_id: number;
  status: string;
  validation_type: string;
  duration_ms: number;
  error_count: number;
  warning_count: number;
  security_findings_count: number;
  findings: ValidationFinding[];
  security_findings?: SecurityFinding[];
  ai_explanations?: LineExplanation[];
  corrected_content?: string;
  summary?: string;
}

export interface ValidationHistoryItem {
  id: number;
  validation_type: string;
  status: string;
  branch?: string;
  commit_sha?: string;
  error_count: number;
  warning_count: number;
  security_findings_count: number;
  duration_ms?: number;
  summary?: string;
  created_at: string;
}

export interface PaginatedHistory {
  items: ValidationHistoryItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
