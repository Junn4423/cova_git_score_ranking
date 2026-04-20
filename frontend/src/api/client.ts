import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error("API Error:", error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export default api;

// ── Sync / Ingestion ──────────────────────────────────────

export const healthCheck = () => api.get("/health");

export const getSyncStats = () => api.get("/api/sync/stats");

export const syncRepo = (data: {
  full_name: string;
  max_commit_pages?: number;
  max_pr_pages?: number;
  fetch_files?: boolean;
}) => api.post("/api/sync/repo", data);

// ── Dashboard ─────────────────────────────────────────────

export const getDashboardOverview = (params?: { days?: number; repo_id?: number }) =>
  api.get("/api/dashboard/overview", { params });

export const getCommitActivity = (params?: { days?: number; repo_id?: number }) =>
  api.get("/api/dashboard/commit-activity", { params });

// ── Developers ────────────────────────────────────────────

export const getDevelopers = (params?: { search?: string }) =>
  api.get("/api/developers", { params });

export const getDeveloper = (id: number) =>
  api.get(`/api/developers/${id}`);

export const getDeveloperCommits = (id: number, params?: { repo_id?: number; limit?: number }) =>
  api.get(`/api/developers/${id}/commits`, { params });

export const getDeveloperActivity = (id: number, params?: { days?: number }) =>
  api.get(`/api/developers/${id}/activity`, { params });

export const getDeveloperAliases = (id: number) =>
  api.get(`/api/developers/${id}/aliases`);

export const addDeveloperAlias = (id: number, data: { alias_type: string; alias_value: string }) =>
  api.post(`/api/developers/${id}/aliases`, data);

export const mergeDevelopers = (data: { keep_id: number; merge_id: number }) =>
  api.post("/api/developers/merge", data);

// ── Repositories ──────────────────────────────────────────

export const getRepositories = () =>
  api.get("/api/repositories");

export const getRepository = (id: number) =>
  api.get(`/api/repositories/${id}`);

// ── Pull Requests ─────────────────────────────────────────

export const getPullRequests = (params?: {
  repo_id?: number;
  author_id?: number;
  state?: string;
  limit?: number;
}) => api.get("/api/pull-requests", { params });

// ── Commits (legacy sync endpoint) ───────────────────────

export const getCommits = (params?: { repo_id?: number; limit?: number }) =>
  api.get("/api/sync/commits", { params });
