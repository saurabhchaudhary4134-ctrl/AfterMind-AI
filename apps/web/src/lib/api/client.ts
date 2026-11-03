/**
 * Typed API client for the AfterMind AI backend.
 * Reads the base URL from NEXT_PUBLIC_API_URL.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

/** Standard error response shape from the backend. */
export interface ApiError {
  detail: string;
  code?: string;
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("refresh_token");
}

function setTokens(access: string, refresh: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem("access_token", access);
  localStorage.setItem("refresh_token", refresh);
}

function clearTokens(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

async function refreshIfNeeded(): Promise<boolean> {
  const access = getToken();
  if (!access) return false;

  // Try to decode and check expiry (without verification)
  try {
    const payload = JSON.parse(atob(access.split(".")[1]));
    const exp = payload.exp * 1000;
    if (Date.now() < exp - 30000) return true; // Still valid for 30s+
  } catch {
    return false;
  }

  // Token is about to expire — try refresh
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  try {
    const resp = await fetch(`${API_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!resp.ok) return false;
    const data = await resp.json();
    setTokens(data.access_token, data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  // Ensure token is fresh
  const valid = await refreshIfNeeded();
  const token = getToken();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  };

  if (token && valid) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const resp = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });

  if (resp.status === 401) {
    // Try one more refresh
    const refreshed = await refreshIfNeeded();
    if (refreshed) {
      headers["Authorization"] = `Bearer ${getToken()}`;
      const retryResp = await fetch(`${API_URL}${path}`, { ...options, headers });
      if (!retryResp.ok) {
        const error = await retryResp.json().catch(() => ({ detail: "Request failed" }));
        throw new ApiErrorImpl(error.detail, error.code);
      }
      return retryResp.json() as Promise<T>;
    }
    clearTokens();
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw new ApiErrorImpl("Authentication required", "auth_required");
  }

  if (!resp.ok) {
    const error = await resp.json().catch(() => ({ detail: "Request failed" }));
    throw new ApiErrorImpl(error.detail || `HTTP ${resp.status}`, error.code);
  }

  if (resp.status === 204) {
    return undefined as T;
  }

  return resp.json() as Promise<T>;
}

/** Upload with query params helper. */
export function buildQuery(params: Record<string, string | number | boolean | undefined>): string {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined);
  if (entries.length === 0) return "";
  return "?" + entries.map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`).join("&");
}

export class ApiErrorImpl extends Error {
  code?: string;
  constructor(detail: string, code?: string) {
    super(detail);
    this.name = "ApiError";
    this.code = code;
  }
}

export { setTokens, clearTokens, getToken, API_URL };
