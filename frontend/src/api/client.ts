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

// ── API functions ──────────────────────────────────────────

export const healthCheck = () => api.get("/health");

// Sync / Ingestion
export const getSyncStats = () => api.get("/api/sync/stats");
export const getRepositories = () => api.get("/api/sync/repositories");
export const getDevelopers = () => api.get("/api/sync/developers");
export const getCommits = (params?: { repo_id?: number; limit?: number }) =>
  api.get("/api/sync/commits", { params });
export const syncRepo = (data: {
  full_name: string;
  max_commit_pages?: number;
  max_pr_pages?: number;
  fetch_files?: boolean;
}) => api.post("/api/sync/repo", data);
