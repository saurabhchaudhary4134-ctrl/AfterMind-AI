# AfterMind AI

**Decision-intelligence platform** — model your decisions, run probabilistic simulations, compare scenarios, and track forecast accuracy before you act.

---

## What it does

A user describes a decision, defines assumptions and constraints as a structured **Decision DNA** (variables with probability distributions, deterministic formulas, objectives), builds **scenarios** with alternative assumptions, launches a **Monte Carlo simulation**, reviews **percentile summaries, sensitivity analysis, and risk metrics**, records **actual outcomes**, and revisits the project to evaluate forecast accuracy over time.

---

## Architecture

```
Browser → Next.js 14 (App Router)
           ↓ HTTPS /api/v1
         FastAPI (Python 3.12)
           ↓
  PostgreSQL  Redis  Celery workers
               ↓
           Simulation Engine (pure Python)
           Monte Carlo · Statistics · Sensitivity
```

Full architecture in `.kiro/steering/architecture.md`.

---

## Quick start (local dev)

### Requirements

- Python 3.12+
- Node.js 20+
- No Redis/Postgres required for dev — SQLite + sync simulation fallback

### Backend

```bash
cd services/api

# Install dependencies
pip install -e ".[dev]"

# Run database migrations
python -m alembic upgrade head

# Start the API (hot-reload)
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd apps/web

# Install dependencies
npm install

# Copy and edit environment
cp ../../.env.example .env.local
# Set NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1

# Start the dev server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## Running tests

```bash
# Backend — 167 tests
cd services/api
python -m pytest tests/ -q

# Backend with coverage
python -m pytest tests/ --cov=app --cov-report=term-missing

# Frontend type check + build
cd apps/web
npx tsc --noEmit
npm run build
```

---

## Production deployment

See `docs/deployment.md` for:
- Environment variable reference
- Alembic migration workflow
- Docker Compose setup
- Backup and restore procedures
- Rollback plan
- Monitoring hooks
- Pre-launch security checklist

---

## Feature overview

| Feature | Status |
|---------|--------|
| JWT auth (register, login, refresh) | ✅ |
| Workspace isolation + member roles | ✅ |
| Decision CRUD + version history | ✅ |
| Decision DNA (variables, distributions, formulas) | ✅ |
| Safe formula evaluator (no eval/exec) | ✅ |
| Monte Carlo simulation (up to 100k iterations) | ✅ |
| Sensitivity analysis / tornado charts | ✅ |
| Scenario builder with assumption overrides | ✅ |
| Background jobs (Celery + sync fallback) | ✅ |
| Persisted, immutable simulation results | ✅ |
| LLM extraction (OpenAI + mock provider) | ✅ |
| Grounded explanations (from computed stats only) | ✅ |
| Actual outcome recording + forecast evaluation | ✅ |
| Report export (JSON + CSV) | ✅ |
| Subscription tiers + quota enforcement | ✅ |
| Rate limiting (auth endpoints) | ✅ |
| Request ID middleware + structured logging | ✅ |
| Body size limits | ✅ |
| Premium dark SaaS frontend (Next.js 14) | ✅ |
| Landing page + onboarding flow | ✅ |
| Docker + docker-compose | ✅ |
| CI/CD pipeline (GitHub Actions) | ✅ |
| Deployment + ops docs | ✅ |

---

## Test summary

- **167 backend tests** — auth, workspace isolation, decisions, simulations, scenarios, outcomes, reports, LLM, quotas, **security (IDOR, injection, rate-limiting, cross-tenant)**
- **76 simulation engine tests** — reproducibility, statistical correctness, formula safety, sensitivity
- **Frontend** — TypeScript strict, zero type errors, production build passing

---

## Environment variables

See `.env.example` for all documented variables. Key ones:

```bash
DATABASE_URL=sqlite:///./aftermind_dev.db  # Use postgresql+psycopg2://... in prod
SECRET_KEY=<32-byte-random-hex>
SIMULATION_SYNC=true                       # false in prod (uses Celery)
CORS_ORIGINS=http://localhost:3000
LLM_PROVIDER=                              # set to "openai" or "mock"
LLM_API_KEY=                               # required for OpenAI
```

---

## License

Proprietary — AfterMind AI. All rights reserved.
