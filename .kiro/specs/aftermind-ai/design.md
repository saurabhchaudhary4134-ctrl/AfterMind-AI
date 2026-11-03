# AfterMind AI — Design

## 1. System architecture

See `.kiro/steering/architecture.md` for the high-level diagram and repository layout.
This document covers the detailed design of each subsystem.

## 2. Database schema

### Entity overview

```
users (PK: id UUID)
  - email (unique, indexed)
  - hashed_password
  - full_name
  - is_active, is_superuser
  - created_at, updated_at

workspaces (PK: id UUID)
  - name, slug
  - owner_id FK users
  - created_at, updated_at

workspace_members (PK: id UUID)
  - workspace_id FK workspaces
  - user_id FK users
  - role (owner|admin|member|viewer)
  - UNIQUE(workspace_id, user_id)

decisions (PK: id UUID)
  - workspace_id FK workspaces (indexed)
  - owner_id FK users
  - title, description
  - objective, time_horizon_days
  - constraints (JSONB)
  - outcome_metrics (JSONB)
  - status (draft|active|archived)
  - current_version_id FK decision_versions (nullable)
  - created_at, updated_at

decision_versions (PK: id UUID)
  - decision_id FK decisions
  - version_number (int)
  - decision_dna (JSONB)  -- full snapshot of variables, assumptions, formulas, deps
  - change_summary
  - created_by FK users
  - created_at

scenarios (PK: id UUID)
  - decision_id FK decisions (indexed)
  - workspace_id FK workspaces (indexed, for isolation)
  - name, description
  - assumption_overrides (JSONB)
  - created_at, updated_at

simulation_runs (PK: id UUID)
  - scenario_id FK scenarios
  - decision_id FK decisions
  - workspace_id FK workspaces (indexed, for isolation)
  - status (queued|running|completed|failed|cancelled)
  - iterations (int)
  - seed (bigint)
  - engine_version (str)
  - model_version (str, nullable)
  - config_snapshot (JSONB)  -- immutable full config
  - progress (int 0-100)
  - error_message (nullable)
  - requested_by FK users
  - started_at, completed_at, created_at

simulation_results (PK: id UUID)
  - run_id FK simulation_runs (one-to-one)
  - summary (JSONB)  -- percentiles, mean, std, threshold probs, CVaR, downside
  - distribution_buckets (JSONB)  -- histogram data for charts
  - sensitivity (JSONB)  -- tornado data
  - raw_percentiles_cache (JSONB, nullable)
  - created_at
  - IMMUTABLE once created

actual_outcomes (PK: id UUID)
  - decision_id FK decisions
  - workspace_id FK workspaces (indexed, for isolation)
  - metric_name
  - actual_value (float)
  - recorded_by FK users
  - recorded_at, created_at

model_versions (PK: id UUID)
  - workspace_id FK workspaces (nullable, nullable for global)
  - name, version (str)
  - model_type (str)
  - description
  - is_active (bool)
  - metadata (JSONB)
  - created_at

audit_events (PK: id UUID)
  - workspace_id FK workspaces (indexed)
  - actor_id FK users
  - action (str)
  - resource_type, resource_id
  - metadata (JSONB)
  - created_at

subscriptions (PK: id UUID)
  - workspace_id FK workspaces (unique)
  - tier (free|pro|team|business)
  - status (active|trialing|canceled)
  - stripe_customer_id (nullable)
  - stripe_subscription_id (nullable)
  - current_period_end (nullable)
  - created_at, updated_at
```

### Conventions
- All PKs are UUID (server-side default via `gen_random_uuid()` in Postgres, `uuid4`
  in SQLite fallback).
- All tables have `created_at`; mutable tables have `updated_at`.
- Tenant-scoped tables have `workspace_id` with an index.
- Foreign keys have `ON DELETE` policies (CASCADE for children of decisions, SET NULL
  for optional references).
- JSONB is used only for flexible configuration/snapshot data, not for fields that
  should be queryable columns.

## 3. API design

### Base path: `/api/v1`

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| GET | /health | 200 | Health check (no auth) |
| GET | /docs | 200 | OpenAPI Swagger UI (dev) |
| POST | /auth/register | 201 | Register |
| POST | /auth/login | 200 | Login → access + refresh tokens |
| POST | /auth/refresh | 200 | Refresh token → new access token |
| GET | /me | 200 | Current user |
| PUT | /me | 200 | Update profile |
| GET | /workspaces | 200 | List my workspaces |
| POST | /workspaces | 201 | Create workspace |
| GET | /workspaces/{id} | 200 | Get workspace |
| GET | /workspaces/{id}/members | 200 | List members |
| POST | /workspaces/{id}/members | 201 | Add member |
| PATCH | /workspaces/{id}/members/{uid} | 200 | Update role |
| DELETE | /workspaces/{id}/members/{uid} | 204 | Remove member |
| GET | /decisions | 200 | List decisions (paginated, scoped) |
| POST | /decisions | 201 | Create decision |
| GET | /decisions/{id} | 200 | Get decision |
| PUT | /decisions/{id} | 200 | Update decision (creates new version) |
| DELETE | /decisions/{id} | 204 | Delete decision |
| GET | /decisions/{id}/versions | 200 | List versions |
| GET | /decisions/{id}/versions/{ver} | 200 | Get specific version |
| PUT | /decisions/{id}/dna | 200 | Update Decision DNA (creates version) |
| POST | /decisions/{id}/extract | 202 | LLM extraction (async or sync) |
| GET | /scenarios | 200 | List scenarios for a decision |
| POST | /scenarios | 201 | Create scenario |
| GET | /scenarios/{id} | 200 | Get scenario |
| PUT | /scenarios/{id} | 200 | Update scenario |
| DELETE | /scenarios/{id} | 204 | Delete scenario |
| POST | /scenarios/{id}/duplicate | 201 | Duplicate scenario |
| POST | /simulations | 202 | Create simulation job |
| GET | /simulations/{id} | 200 | Get job status |
| GET | /simulations/{id}/results | 200 | Get results (if completed) |
| POST | /simulations/{id}/cancel | 200 | Cancel queued/running job |
| GET | /simulations | 200 | List simulations (paginated, scoped) |
| POST | /decisions/{id}/outcomes | 201 | Record actual outcome |
| GET | /decisions/{id}/outcomes | 200 | List actual outcomes |
| GET | /decisions/{id}/forecast-eval | 200 | Forecast evaluation |
| GET | /reports/{run_id} | 200 | Get report data |
| GET | /reports/{run_id}/export | 200 | Export (json/csv) |
| GET | /workspaces/{id}/subscription | 200 | Get subscription |
| GET | /workspaces/{id}/usage | 200 | Get quota usage |

### Error response shape

```json
{ "detail": "Human-readable message", "code": "error_code" }
```

### Pagination

`?page=1&page_size=20` → `{ "items": [...], "total": 100, "page": 1, "page_size": 20 }`

### Idempotency

`POST /simulations` supports an `Idempotency-Key` header to prevent duplicate jobs.

## 4. Simulation engine design

### Decision DNA model (Pydantic / typed)

```python
class DistributionType(str, Enum):
    NORMAL = "normal"
    UNIFORM = "uniform"
    TRIANGULAR = "triangular"
    LOGNORMAL = "lognormal"
    BETA = "beta"
    CONSTANT = "constant"

class Distribution(BaseModel):
    type: DistributionType
    params: dict[str, float]  # validated per type

class Variable(BaseModel):
    name: str            # identifier-safe
    label: str
    unit: str
    distribution: Distribution

class Formula(BaseModel):
    name: str            # output variable identifier
    expression: str      # restricted expression, e.g. "revenue * margin - costs"
    description: str | None

class DecisionModel(BaseModel):
    variables: list[Variable]
    formulas: list[Formula]
    objective: str       # which formula/variable to optimize
    constraints: list[str]  # restricted expressions that must be >= 0
```

### Safe formula evaluator

- Parse expressions with a restricted parser (e.g. `simpleeval` or a custom
  recursive-descent parser supporting `+ - * / ** ()` and named variables).
- No attribute access, no function calls, no imports, no builtins.
- Variables resolved from the model's variable/formula namespace.
- Circular dependency detection via topological sort before evaluation.

### Monte Carlo

1. Resolve evaluation order (topological sort of variables/formulas).
2. For each iteration:
   a. Sample each input variable from its distribution using the seeded RNG.
   b. Evaluate formulas in dependency order.
   c. Collect objective value(s).
3. After all iterations, compute summary statistics.

### Statistics

- Percentiles: P5, P10, P25, P50, P75, P90, P95
- Mean, standard deviation, variance
- Threshold probability: P(outcome >= threshold) and P(outcome <= threshold)
- CVaR (conditional value at risk) at the 5th percentile
- Downside risk: probability and magnitude of loss below a threshold
- Distribution histogram buckets for visualization

### Sensitivity analysis

- One-at-a-time: vary each input variable ±20% (or by its std dev), recompute the
  objective, measure the delta. Produce tornado chart data.
- Report which variables have the largest impact and the direction.

### Reproducibility

- Seed stored per run. `numpy.random.default_rng(seed)`.
- Engine version string baked into results.

## 5. Worker design

- Celery task `run_simulation(run_id)`:
  1. Load run + config_snapshot from DB.
  2. Set status to `running`.
  3. Execute simulation engine (pure function).
  4. Persist results.
  5. Set status to `completed` (or `failed` with error_message).
- Progress reporting: update `progress` column periodically.
- Timeout: `soft_time_limit` on the Celery task.
- Retry: `max_retries=2`, exponential backoff.
- Idempotency: check run status before starting; skip if already completed.
- In dev without Redis/Celery: a synchronous fallback runs the simulation inline
  (behind a config flag `SIMULATION_SYNC=true`) so the full flow works locally.

## 6. LLM integration design

```
LLMProvider (abstract)
  ├── OpenAIProvider
  ├── AnthropicProvider  (future)
  └── MockProvider       (for tests / offline dev)
```

- `extract_decision(text) → ExtractionDraft` — returns structured draft validated
  with Pydantic. Missing fields are flagged. No DB writes.
- `generate_explanation(run_results) → Explanation` — text generated only from
  computed statistics, never fabricated data.
- Timeouts, retry limits, token budgets configured via env.
- If no provider configured, extraction endpoint returns 503 and the UI falls back
  to manual entry.

## 7. Frontend design

### Pages

| Route | Page |
|-------|------|
| `/` | Landing page |
| `/login` | Sign in |
| `/register` | Sign up |
| `/onboarding` | First-time setup + sample decision |
| `/app` | Dashboard / overview |
| `/app/decisions` | Decision list |
| `/app/decisions/[id]` | Decision workspace (tabs: overview, assumptions, scenarios, simulations, results, reality) |
| `/app/decisions/[id]/assumptions` | Decision DNA editor |
| `/app/decisions/[id]/scenarios` | Scenario builder |
| `/app/decisions/[id]/simulations` | Simulation lab |
| `/app/decisions/[id]/results/[runId]` | Results dashboard |
| `/app/decisions/[id]/what-if` | What-if explorer |
| `/app/decisions/[id]/reports` | Reports |
| `/app/decisions/[id]/reality` | Reality tracker |
| `/app/settings` | User settings |
| `/app/workspaces/[id]/settings` | Workspace settings |
| `/app/subscription` | Subscription management |

### Design system

- Dark navy surfaces (`#0a0e1a`, `#111729`, `#1a2235`).
- Cyan accent (`#22d3ee`) and violet accent (`#a78bfa`).
- Inter font. 14px base, 8px spacing grid.
- Cards with subtle borders (`#1e293b`) and soft shadows.
- Charts: Recharts with themed colors.
- Responsive: mobile stack, tablet 2-col, desktop sidebar.
- Loading skeletons, empty states with CTAs, toast notifications.

### State management

- Server state: TanStack Query (React Query) for API data.
- Local UI state: React useState/context.
- Auth: client-side auth context backed by httpOnly cookie tokens.

## 8. Security design

- JWT access (15 min) + refresh (7 day) tokens.
- Password hashing: passlib[argon2] or bcrypt.
- Rate limiting: slowapi or custom middleware (per-IP + per-user).
- CORS: configurable allowlist.
- Input limits: max body size, max iterations (100k), max variables (50), max
  formulas (50).
- Formula safety: restricted parser, no builtins.
- Tenant isolation: every repository method filters by workspace_id.
- Audit logging on all state-changing operations.

## 9. Testing strategy

| Layer | Framework | What |
|-------|-----------|------|
| Simulation engine | pytest | Statistical correctness, reproducibility, boundary, injection, circular deps |
| API services | pytest + httpx | CRUD, auth, isolation, validation |
| API endpoints | pytest + httpx (TestClient) | Status codes, error shapes, auth |
| Migrations | pytest + Alembic | Forward + backward, schema integrity |
| Frontend units | Vitest | Component rendering, utilities |
| E2E | Playwright | Auth → decision → sim → results → outcome |

## 10. Environment variables

Documented in `.env.example`. Key categories:
- Database: `DATABASE_URL`
- Redis: `REDIS_URL`
- Auth: `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`
- LLM: `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_TIMEOUT`
- CORS: `CORS_ORIGINS`
- Simulation: `SIMULATION_SYNC` (dev fallback), `MAX_ITERATIONS`
- Worker: `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
- Payments: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` (optional)
