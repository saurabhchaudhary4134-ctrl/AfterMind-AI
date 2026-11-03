# AfterMind AI — Tasks

## Phase 1: Foundation & Specs

### Task 1.1 — Steering files and spec
- [x] Create `.kiro/steering/product.md`, `architecture.md`, `coding-standards.md`, `security.md`
- [x] Create `.kiro/specs/aftermind-ai/requirements.md`, `design.md`, `tasks.md`
- [x] Create `.env.example`, `.gitignore`
- **Acceptance**: All files exist and are consistent with each other.

## Phase 2: Backend, Database, Auth, Workspace Isolation

### Task 2.1 — Backend project scaffold
- [x] Create `services/api/` with `pyproject.toml` (pinned deps), `app/` package
- [x] `app/core/config.py` (Pydantic Settings, env vars)
- [x] `app/main.py` (FastAPI app, CORS, routers, health endpoint)
- [x] Verify: `uvicorn` starts, `/api/v1/health` returns 200
- **Acceptance**: Server starts, health endpoint works.

### Task 2.2 — Database layer
- [x] `app/db/base.py` (declarative base, TimestampMixin)
- [x] `app/db/session.py` (engine, session factory, get_db dependency)
- [x] `app/models/` — all ORM models (users, workspaces, members, decisions, versions, scenarios, runs, results, outcomes, model_versions, audit, subscriptions)
- [x] Alembic setup with `env.py` + initial migration
- **Acceptance**: `alembic upgrade head` succeeds (SQLite dev); tables exist.

### Task 2.3 — Auth: register, login, refresh
- [x] `app/core/security.py` (password hashing, JWT create/verify)
- [x] `app/core/deps.py` (get_current_user, require_workspace_member)
- [x] `app/schemas/auth.py`, `app/services/auth_service.py`
- [x] `app/repositories/user_repo.py`
- [x] Endpoints: `/auth/register`, `/auth/login`, `/auth/refresh`, `/me`
- [x] Tests: register, login, refresh, protected route, invalid token
- **Acceptance**: Auth flow works; tests pass.

### Task 2.4 — Workspace CRUD + isolation
- [x] `app/services/workspace_service.py`, `app/repositories/workspace_repo.py`
- [x] Auto-create personal workspace on registration
- [x] Endpoints: workspaces list/create/get, members add/update/remove
- [x] Tests: cross-workspace isolation (user A cannot read user B's workspace)
- **Acceptance**: Isolation test proves no cross-tenant access.

### Task 2.5 — Decision CRUD + version history
- [x] `app/schemas/decision.py`, `app/services/decision_service.py`
- [x] `app/repositories/decision_repo.py` (all scoped by workspace_id)
- [x] Endpoints: decision CRUD, versions list/get, DNA update (creates version)
- [x] Tests: CRUD, version increment, IDOR prevention
- **Acceptance**: Decision CRUD + versioning works; IDOR blocked.

## Phase 3: Simulation Engine

### Task 3.1 — Decision DNA schema + validation
- [x] `app/simulation/schema.py` (Distribution, Variable, Formula, DecisionModel)
- [x] Distribution parameter validation per type
- [x] Variable name validation (identifier-safe, unique)
- [x] **Acceptance**: Invalid models are rejected with clear errors.

### Task 3.2 — Safe formula evaluator
- [x] `app/simulation/evaluator.py` — restricted expression parser
- [x] Support: `+ - * / ** ()` and named variables; no builtins, no calls, no attrs
- [x] Topological sort for dependency order + circular dependency detection
- [x] **Acceptance**: Malicious inputs (`__import__`, `eval`, `os.system`) rejected.

### Task 3.3 — Monte Carlo engine
- [x] `app/simulation/engine.py` — seeded sampling, formula eval, iteration loop
- [x] `app/simulation/statistics.py` — percentiles, mean, std, threshold prob, CVaR
- [x] `app/simulation/sensitivity.py` — tornado / one-at-a-time
- [x] `app/simulation/__init__.py` — public API + ENGINE_VERSION
- [x] **Acceptance**: 10k iterations run; results deterministic for same seed.

### Task 3.4 — Simulation engine tests
- [x] `tests/simulation/test_engine.py` — reproducibility, stats correctness
- [x] `tests/simulation/test_evaluator.py` — safety, circular deps, boundaries
- [x] `tests/simulation/test_sensitivity.py` — tornado data shape
- [x] Statistical tests: mean within expected range for known distributions
- [x] **Acceptance**: All sim tests pass; no web/DB imports in simulation package.

## Phase 4: Workers, Scenarios, Simulation API

### Task 4.1 — Scenario CRUD + comparison
- [x] `app/schemas/scenario.py`, `app/services/scenario_service.py`
- [x] `app/repositories/scenario_repo.py` (workspace-scoped)
- [x] Endpoints: scenario CRUD, duplicate
- [x] Tests: CRUD, duplicate, isolation
- **Acceptance**: Scenarios work; comparison endpoint returns side-by-side stats.

### Task 4.2 — Simulation run + worker
- [x] `app/schemas/simulation.py`, `app/services/simulation_service.py`
- [x] `app/repositories/simulation_repo.py`
- [x] `app/workers/tasks.py` — Celery task `run_simulation`
- [x] Sync fallback: if `SIMULATION_SYNC=true`, run inline in the request
- [x] Endpoints: POST /simulations (202), GET status, GET results, POST cancel
- [x] Tests: create run, sync execution, result persistence, immutability
- **Acceptance**: Simulation runs, persists results; results immutable.

## Phase 5: Frontend

### Task 5.1 — Next.js scaffold + design system
- [x] `apps/web/` with Next.js App Router, TypeScript, Tailwind, shadcn/ui
- [x] Theme: dark navy, cyan/violet accents, base components
- [x] `packages/contracts/` — shared TypeScript API types
- [x] Verify: `npm run build` succeeds
- **Acceptance**: Build passes; design tokens applied.

### Task 5.2 — Auth pages + API client
- [x] `lib/api/` typed client, auth context, login/register pages
- [x] Protected route layout, session refresh
- **Acceptance**: Can register + login from the UI.

### Task 5.3 — Dashboard + decision list/creation
- [x] Overview dashboard, decision list, create/edit decision
- [x] Empty states, loading skeletons, toasts
- **Acceptance**: Create decision from UI → appears in list.

### Task 5.4 — Decision DNA editor + scenario builder
- [x] Assumption editor (variables, distributions, formulas)
- [x] Scenario builder with overrides, duplicate, comparison
- **Acceptance**: Edit DNA → version saved; create scenarios.

### Task 5.5 — Simulation lab + results dashboard
- [x] Launch simulation, track job status, view results + charts
- [x] Sensitivity tornado chart, what-if explorer
- **Acceptance**: Launch sim → see real persisted results.

### Task 5.6 — Reports, reality tracker, settings
- [x] Report view + export, reality tracker (record outcomes), settings
- **Acceptance**: Record outcome → forecast eval shows errors.

### Task 5.7 — Landing page + onboarding
- [x] Landing page, onboarding flow with sample decision
- **Acceptance**: Landing page renders; onboarding creates sample decision.

## Phase 6: LLM Integration

### Task 6.1 — LLM provider abstraction + extraction
- [x] `app/services/llm/` — provider abstraction, mock provider, OpenAI provider
- [x] `POST /decisions/{id}/extract` → validated draft, human confirmation
- [x] Tests: extraction with mock provider, LLM unavailable fallback
- **Acceptance**: Extraction returns validated draft; 503 when no provider.

### Task 6.2 — Grounded explanations
- [x] Generate explanation from computed results only
- [x] Display in results dashboard
- **Acceptance**: Explanation references real metrics; no fabricated data.

## Phase 7: Reality Feedback, Reports, Usage

### Task 7.1 — Actual outcomes + forecast evaluation
- [x] `POST/GET /decisions/{id}/outcomes`
- [x] `GET /decisions/{id}/forecast-eval` — MAE, MAPE, bias, calibration
- [x] Display sample size and limitations
- **Acceptance**: Record outcome → eval shows errors; n displayed.

### Task 7.2 — Report generation + export
- [x] `GET /reports/{run_id}` and `/export` (json/csv)
- [x] Audit events on state changes
- **Acceptance**: Export produces valid JSON/CSV.

### Task 7.3 — Usage quotas
- [x] Quota check before simulation + LLM calls
- [x] `GET /workspaces/{id}/usage`
- **Acceptance**: Over-quota returns 429; usage endpoint shows counts.

## Phase 8: Subscriptions, Monitoring, CI/CD, Deployment

### Task 8.1 — Subscription tiers
- [x] Subscription model + tier configs (free/pro/team/business)
- [x] Tier determines quotas; no invented prices
- **Acceptance**: Tier changes update available quotas.

### Task 8.2 — Docker + docker-compose
- [x] `infra/docker/api.Dockerfile`, `web.Dockerfile`
- [x] `docker-compose.yml` (api, web, postgres, redis, worker)
- **Acceptance**: Dockerfiles are valid (build verification if Docker available).

### Task 8.3 — CI/CD pipeline
- [x] GitHub Actions: lint, type-check, test, build, scan
- [x] Migration instructions, backup/restore docs, rollback plan
- **Acceptance**: CI config is complete and documented.

### Task 8.4 — Monitoring + security hardening
- [x] Request ID middleware, structured logging, health checks
- [x] Rate limiting, input size limits, CORS hardening
- [x] Dependency scan (pip-audit / npm audit) in CI
- **Acceptance**: Security tests pass; rate limiting active.

## Status legend
- [ ] not started
- [~] in progress
- [x] complete
