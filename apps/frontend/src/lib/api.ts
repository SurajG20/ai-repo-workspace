const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

const TOKEN_KEY = "repograph_token";

export function getToken(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(TOKEN_KEY) || "";
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  token: string | null = null
): Promise<T> {
  const headers: Record<string, string> = {};
  const effectiveToken = token ?? getToken();
  if (effectiveToken) headers.Authorization = `Bearer ${effectiveToken}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail || data.message || JSON.stringify(data);
    } catch {
      /* keep statusText */
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  get: <T>(path: string, token?: string) => request<T>("GET", path, undefined, token),
  post: <T>(path: string, body?: unknown, token?: string) =>
    request<T>("POST", path, body, token),
  del: <T>(path: string, token?: string) => request<T>("DELETE", path, undefined, token),
};

export interface Repository {
  id: string;
  full_name: string;
  provider: string;
  status: string;
  language: string | null;
  description: string | null;
  is_private: boolean;
  default_branch: string;
  size_bytes: number;
  last_synced_at: string | null;
  last_synced_sha: string | null;
  created_at: string;
}

export interface OverviewStats {
  repositories_total: number;
  repositories_active: number;
  repositories_by_status: Record<string, number>;
  languages: Record<string, number>;
  files_total: number;
  snapshots_total: number;
  symbols_total: number;
  symbols_by_kind: Record<string, number>;
  jobs: { queued: number; running: number; completed: number; failed: number };
}

export interface SearchHit {
  symbol_id: string;
  name: string;
  kind: string;
  file_path: string;
  signature: string | null;
  start_line: number;
  end_line: number;
  parent_name: string | null;
  language: string;
  score: number;
  sources: string[];
}

export interface SearchResult {
  query: string;
  repository_id: string;
  total: number;
  hits: SearchHit[];
  trace: {
    searchers: {
      source: string;
      hits: number;
      error: string | null;
      duration_ms: number;
    }[];
    fused_count: number;
    total_candidates: number;
  };
}

export interface CallEdge {
  source_id: string;
  source_name: string;
  source_file: string;
  target_id: string;
  target_name: string;
  target_file: string;
  distance: number;
}

export interface DeadCodeCandidate {
  symbol_id: string;
  name: string;
  kind: string;
  file_path: string;
  signature: string | null;
  start_line: number;
  end_line: number;
  parent_name: string | null;
  language: string;
  outbound_links: number;
  entry_point: boolean;
}

export interface DeadCodeResult {
  repository_id: string;
  count: number;
  candidates: DeadCodeCandidate[];
  ai_triage: unknown | null;
}

export interface AskResult {
  answer: {
    question: string;
    answer: string;
    context_blocks: {
      index: number;
      kind: string;
      name: string;
      file_path: string;
      start_line: number;
      end_line: number;
      signature: string | null;
      score: number;
      sources: string[];
    }[];
    model: string;
    provider: string;
  };
  retrieval: {
    hits: SearchHit[];
    trace: unknown;
    llm: { model: string; provider: string; duration_ms: number; error: string | null };
  };
}

export interface SymbolRecord {
  symbol_id: string;
  name: string;
  kind: string;
  file_path: string;
  signature: string | null;
  start_line: number;
  end_line: number;
  parent_name: string | null;
  language: string;
}

export interface GraphStats {
  symbols: number;
  relationships: number;
  by_type: Record<string, number>;
}

export interface RepositoryItem {
  id: string;
  full_name: string;
  provider: string;
  status: string;
  language: string | null;
  description: string | null;
  is_private: boolean;
  default_branch: string;
  size_bytes: number;
  last_synced_at: string | null;
  last_synced_sha: string | null;
  created_at: string;
}
