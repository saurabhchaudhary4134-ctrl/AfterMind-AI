/**
 * AfterMind AI — Shared API contracts.
 * These types mirror the backend Pydantic schemas and can be imported
 * by both the frontend and any other consumers.
 */

// ── Auth ──────────────────────────────────────────────────────

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

// ── Workspace ─────────────────────────────────────────────────

export type WorkspaceRole = "owner" | "admin" | "member" | "viewer";

export interface Workspace {
  id: string;
  name: string;
  slug: string;
  owner_id: string;
  my_role: string | null;
  created_at: string;
}

export interface WorkspaceMember {
  id: string;
  workspace_id: string;
  user_id: string;
  role: WorkspaceRole;
  created_at: string;
}

// ── Decision ──────────────────────────────────────────────────

export type DecisionStatus = "draft" | "active" | "archived";

export interface Decision {
  id: string;
  workspace_id: string;
  owner_id: string;
  title: string;
  description: string;
  objective: string;
  time_horizon_days: number;
  constraints: Record<string, unknown> | null;
  outcome_metrics: OutcomeMetric[] | null;
  status: DecisionStatus;
  current_version_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface OutcomeMetric {
  name: string;
  unit: string;
  description: string;
  target: number | null;
}

export interface DecisionVersion {
  id: string;
  decision_id: string;
  version_number: number;
  decision_dna: Record<string, unknown>;
  change_summary: string;
  created_by: string | null;
  created_at: string;
}

// ── Decision DNA ──────────────────────────────────────────────

export type DistributionType =
  | "normal"
  | "uniform"
  | "triangular"
  | "lognormal"
  | "beta"
  | "constant";

export interface Distribution {
  type: DistributionType;
  params: Record<string, number>;
}

export interface Variable {
  name: string;
  label: string;
  unit: string;
  distribution: Distribution;
}

export interface Formula {
  name: string;
  expression: string;
  description: string | null;
}

export interface DecisionModel {
  variables: Variable[];
  formulas: Formula[];
  objective: string;
  constraints: string[];
}

// ── Scenario ──────────────────────────────────────────────────

export interface Scenario {
  id: string;
  decision_id: string;
  workspace_id: string;
  name: string;
  description: string;
  assumption_overrides: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

// ── Simulation ────────────────────────────────────────────────

export type SimulationStatus =
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

export interface SimulationRun {
  id: string;
  scenario_id: string;
  decision_id: string;
  workspace_id: string;
  status: SimulationStatus;
  iterations: number;
  seed: number;
  engine_version: string;
  progress: number;
  error_message: string | null;
  requested_by: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface SimulationSummary {
  n: number;
  mean: number;
  std: number;
  variance: number;
  min: number;
  max: number;
  range: number;
  p5: number;
  p10: number;
  p25: number;
  p50: number;
  p75: number;
  p90: number;
  p95: number;
  cvar_5: number;
  cv: number;
  [key: string]: number;
}

export interface SimulationResult {
  run_id: string;
  status: string;
  objective: string;
  iterations: number;
  seed: number;
  summary: SimulationSummary;
  distribution_buckets: {
    bin_edges: number[];
    bin_centers: number[];
    counts: number[];
    bins: number;
  };
  sensitivity: {
    variables: SensitivityVariable[];
  };
  elapsed_seconds: number | null;
  config_snapshot: Record<string, unknown> | null;
  created_at: string | null;
}

export interface SensitivityVariable {
  name: string;
  label: string;
  unit: string;
  low_impact: number;
  base_impact: number;
  high_impact: number;
  sensitivity: number;
  direction: "positive" | "negative";
  variation_pct: number;
}

// ── Actual Outcomes ───────────────────────────────────────────

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
