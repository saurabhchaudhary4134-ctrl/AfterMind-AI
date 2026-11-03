# AfterMind AI — Architecture Steering

## High-level architecture

AfterMind AI is a **modular monolith** with a clear separation between the web API,
the simulation engine, background workers, and the frontend.

```
                 ┌─────────────┐
   Browser  ───► │  Next.js    │  (apps/web)
                 │  App Router │
                 └──────┬──────┘
                        │ HTTPS /api/v1
                 ┌──────▼──────┐
                 │   FastAPI   │  (services/api)
                 │  REST API   │
                 └──────┬──────┘
                        │
          ┌─────────────┼─────────────┐
          │             │             │
   ┌──────▼──────┐ ┌────▼─────┐ ┌─────▼──────┐
   │ PostgreSQL  │ │  Redis   │ │  Celery    │
   │  (SQLAlchemy│ │  broker  │ │  workers   │
   │   Alembic)  │ │          │ └─────┬──────┘
   └─────────────┘ └──────────┘       │
                                        │
                                 ┌──────▼──────┐
                                 │ Simulation  │
                                 │   Engine    │  (pure Python)
                                 │ + ML models  │
                                 └─────────────┘
```

## Repository layout (monorepo)

```
.kiro/steering/          Kiro steering files
.kiro/specs/             Kiro specifications (requirements/design/tasks)
apps/web/                Next.js frontend (TypeScript, Tailwind, shadcn/ui)
services/api/            Python FastAPI backend
  app/api/v1/endpoints/  Versioned REST endpoints
  app/core/              Config, security, deps
  app/db/                Engine, session, base
  app/models/           SQLAlchemy ORM models
  app/schemas/          Pydantic request/response schemas
  app/repositories/     Data-access layer (ownership checks)
  app/services/         Business logic (auth, decisions, sim orchestration)
  app/simulation/       Pure mathematical engine (no HTTP, no DB)
  app/ml/               Forecasting models (added later with data)
  app/workers/          Celery tasks
  alembic/              Database migrations
  tests/                pytest suites
packages/contracts/     Shared API contracts (TypeScript types)
infra/docker/           Dockerfiles
infra/deployment/       Deployment manifests / instructions
scripts/                Utility scripts
docs/                   Architecture & ops documentation
.env.example            Documented environment variables
docker-compose.yml      Local development stack
```

## Layering rules

- **Endpoints** (`endpoints/`) only parse/validate input and call services. No DB
  access or business logic directly in endpoints.
- **Services** (`services/`) orchestrate business logic and call repositories.
- **Repositories** (`repositories/`) own all DB access and enforce ownership /
  tenant isolation on every query.
- **Simulation engine** (`simulation/`) is pure Python with no framework, no DB, no
  HTTP. It takes a typed model and returns typed results. This makes it fast to test
  and safe to reason about.
- **ML** (`ml/`) is separate from the simulation engine and only loaded when data
  exists. Predictive models are never auto-promoted from unverified data.

## Data isolation

Every multi-tenant table carries a `workspace_id` foreign key. Repository methods
accept a `workspace_id` and filter by it in every query. Ownership is verified before
any read or write. There are no "list everything" queries that cross workspaces.

## Reproducibility

Every `simulation_run` stores: the engine version, the model version, the random seed,
the full scenario configuration snapshot (JSONB), iteration count, and status. Once a
run reaches `completed`, its results are immutable. Re-running creates a new row.

## Background jobs

Long-running simulations are submitted via HTTP 202 and processed by Celery workers.
Job states: `queued → running → completed | failed | cancelled`. Workers report
progress and persist results on completion. Retries and timeouts are configurable.

## API versioning

All endpoints live under `/api/v1`. Breaking changes require a new version. The
OpenAPI schema is auto-generated from FastAPI + Pydantic and served at `/api/v1/docs`.

## Environment-based configuration

All configuration comes from environment variables (see `.env.example`). No secrets in
code. The app supports a local SQLite fallback for development so the core works
without external services, while production uses PostgreSQL.
