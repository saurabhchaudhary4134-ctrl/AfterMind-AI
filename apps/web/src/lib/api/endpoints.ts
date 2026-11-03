/**
 * API endpoint functions — one per backend endpoint group.
 */

import { apiFetch, buildQuery, setTokens, clearTokens } from "./client";
import type {
  Decision,
  DecisionCreate,
  DecisionVersion,
  PaginatedResponse,
  Scenario,
  ScenarioCreate,
  SimulationCreate,
  SimulationResult,
  SimulationRun,
  TokenResponse,
  User,
  UserLogin,
  UserRegister,
  Workspace,
  WorkspaceMember,
} from "./types";

// ── Auth ──────────────────────────────────────────────────────

export const authApi = {
  register: async (data: UserRegister): Promise<TokenResponse> => {
    const result = await apiFetch<TokenResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    });
    setTokens(result.access_token, result.refresh_token);
    return result;
  },

  login: async (data: UserLogin): Promise<TokenResponse> => {
    const result = await apiFetch<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    });
    setTokens(result.access_token, result.refresh_token);
    return result;
  },

  logout: () => clearTokens(),

  getMe: () => apiFetch<User>("/me"),

  updateMe: (data: { full_name?: string }) =>
    apiFetch<User>("/me", { method: "PUT", body: JSON.stringify(data) }),
};

// ── Workspaces ────────────────────────────────────────────────

export const workspaceApi = {
  list: () => apiFetch<Workspace[]>("/workspaces"),

  create: (data: { name: string; slug?: string }) =>
    apiFetch<Workspace>("/workspaces", { method: "POST", body: JSON.stringify(data) }),

  get: (id: string) => apiFetch<Workspace>(`/workspaces/${id}`),

  listMembers: (id: string) =>
    apiFetch<WorkspaceMember[]>(`/workspaces/${id}/members`),

  addMember: (id: string, data: { user_id: string; role: string }) =>
    apiFetch<WorkspaceMember>(`/workspaces/${id}/members`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateMemberRole: (id: string, userId: string, role: string) =>
    apiFetch<WorkspaceMember>(`/workspaces/${id}/members/${userId}`, {
      method: "PATCH",
      body: JSON.stringify({ role }),
    }),

  removeMember: (id: string, userId: string) =>
    apiFetch<void>(`/workspaces/${id}/members/${userId}`, { method: "DELETE" }),
};

// ── Decisions ──────────────────────────────────────────────────

export const decisionApi = {
  list: (workspaceId: string, page = 1, pageSize = 20) =>
    apiFetch<PaginatedResponse<Decision>>(
      `/decisions${buildQuery({ workspace_id: workspaceId, page, page_size: pageSize })}`,
    ),

  create: (workspaceId: string, data: DecisionCreate) =>
    apiFetch<Decision>(
      `/decisions${buildQuery({ workspace_id: workspaceId })}`,
      { method: "POST", body: JSON.stringify(data) },
    ),

  get: (id: string, workspaceId: string) =>
    apiFetch<Decision>(`/decisions/${id}${buildQuery({ workspace_id: workspaceId })}`),

  update: (id: string, workspaceId: string, data: Partial<DecisionCreate>) =>
    apiFetch<Decision>(
      `/decisions/${id}${buildQuery({ workspace_id: workspaceId })}`,
      { method: "PUT", body: JSON.stringify(data) },
    ),

  delete: (id: string, workspaceId: string) =>
    apiFetch<void>(`/decisions/${id}${buildQuery({ workspace_id: workspaceId })}`, { method: "DELETE" }),

  listVersions: (id: string, workspaceId: string) =>
    apiFetch<DecisionVersion[]>(`/decisions/${id}/versions${buildQuery({ workspace_id: workspaceId })}`),

  getVersion: (id: string, version: number, workspaceId: string) =>
    apiFetch<DecisionVersion>(
      `/decisions/${id}/versions/${version}${buildQuery({ workspace_id: workspaceId })}`,
    ),

  updateDna: (id: string, workspaceId: string, dna: Record<string, unknown>, changeSummary: string) =>
    apiFetch<DecisionVersion>(
      `/decisions/${id}/dna${buildQuery({ workspace_id: workspaceId })}`,
      { method: "PUT", body: JSON.stringify({ decision_dna: dna, change_summary: changeSummary }) },
    ),
};

// ── Scenarios ─────────────────────────────────────────────────

export const scenarioApi = {
  list: (decisionId: string, workspaceId: string) =>
    apiFetch<Scenario[]>(`/scenarios${buildQuery({ decision_id: decisionId, workspace_id: workspaceId })}`),

  create: (workspaceId: string, data: ScenarioCreate) =>
    apiFetch<Scenario>(
      `/scenarios${buildQuery({ workspace_id: workspaceId })}`,
      { method: "POST", body: JSON.stringify(data) },
    ),

  get: (id: string, workspaceId: string) =>
    apiFetch<Scenario>(`/scenarios/${id}${buildQuery({ workspace_id: workspaceId })}`),

  update: (id: string, workspaceId: string, data: Partial<ScenarioCreate>) =>
    apiFetch<Scenario>(`/scenarios/${id}${buildQuery({ workspace_id: workspaceId })}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  delete: (id: string, workspaceId: string) =>
    apiFetch<void>(`/scenarios/${id}${buildQuery({ workspace_id: workspaceId })}`, { method: "DELETE" }),

  duplicate: (id: string, workspaceId: string) =>
    apiFetch<Scenario>(`/scenarios/${id}/duplicate${buildQuery({ workspace_id: workspaceId })}`, {
      method: "POST",
    }),

  compare: (decisionId: string, workspaceId: string) =>
    apiFetch<{ scenarios: unknown[] }>(
      `/scenarios/compare${buildQuery({ decision_id: decisionId, workspace_id: workspaceId })}`,
    ),
};

// ── Simulations ───────────────────────────────────────────────

export const simulationApi = {
  create: (workspaceId: string, data: SimulationCreate) =>
    apiFetch<SimulationRun>(
      `/simulations${buildQuery({ workspace_id: workspaceId })}`,
      { method: "POST", body: JSON.stringify(data) },
    ),

  get: (id: string, workspaceId: string) =>
    apiFetch<SimulationRun>(`/simulations/${id}${buildQuery({ workspace_id: workspaceId })}`),

  getResults: (id: string, workspaceId: string) =>
    apiFetch<SimulationResult>(`/simulations/${id}/results${buildQuery({ workspace_id: workspaceId })}`),

  cancel: (id: string, workspaceId: string) =>
    apiFetch<SimulationRun>(`/simulations/${id}/cancel${buildQuery({ workspace_id: workspaceId })}`, {
      method: "POST",
    }),

  list: (decisionId: string, workspaceId: string, page = 1, pageSize = 20) =>
    apiFetch<PaginatedResponse<SimulationRun>>(
      `/simulations${buildQuery({ decision_id: decisionId, workspace_id: workspaceId, page, page_size: pageSize })}`,
    ),
};

// ── Outcomes & Reports ────────────────────────────────────────

export interface ActualOutcome {
  id: string;
  decision_id: string;
  workspace_id: string;
  metric_name: string;
  actual_value: number;
  notes: string;
  recorded_by: string | null;
  created_at: string;
}

export interface ForecastEvaluation {
  decision_id: string;
  n_outcomes: number;
  metrics: Array<{
    metric_name: string;
    actual_value: number;
    simulated_p50: number | null;
    simulated_mean: number | null;
    absolute_error: number | null;
    pct_error: number | null;
    note: string;
  }>;
  limitation_note: string;
}

export const outcomeApi = {
  record: (decisionId: string, workspaceId: string, data: { metric_name: string; actual_value: number; notes?: string }) =>
    apiFetch<ActualOutcome>(
      `/decisions/${decisionId}/outcomes${buildQuery({ workspace_id: workspaceId })}`,
      { method: "POST", body: JSON.stringify(data) },
    ),

  list: (decisionId: string, workspaceId: string) =>
    apiFetch<ActualOutcome[]>(`/decisions/${decisionId}/outcomes${buildQuery({ workspace_id: workspaceId })}`),

  forecastEval: (decisionId: string, workspaceId: string) =>
    apiFetch<ForecastEvaluation>(`/decisions/${decisionId}/forecast-eval${buildQuery({ workspace_id: workspaceId })}`),
};

export const reportApi = {
  get: (runId: string, workspaceId: string) =>
    apiFetch<Record<string, unknown>>(`/reports/${runId}${buildQuery({ workspace_id: workspaceId })}`),

  exportUrl: (runId: string, workspaceId: string, format: "json" | "csv") =>
    `/reports/${runId}/export${buildQuery({ workspace_id: workspaceId, format })}`,
};
