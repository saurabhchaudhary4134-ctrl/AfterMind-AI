# AfterMind AI — Deployment Guide

## Prerequisites

- Docker Engine 24+ and Docker Compose v2
- A PostgreSQL 16 instance (or use the `docker-compose.yml` Postgres service)
- A Redis 7 instance (or use the `docker-compose.yml` Redis service)
- A domain name with HTTPS/TLS termination (Nginx, Caddy, or a cloud load balancer)

---

## 1. Environment configuration

Copy `.env.example` to `.env` and fill in every value:

```bash
cp .env.example .env
```

Critical variables to set for production:

| Variable | Example | Notes |
|----------|---------|-------|
| `DATABASE_URL` | `postgresql+psycopg2://user:pw@host/db` | Must point to Postgres in prod |
| `SECRET_KEY` | 32-byte random hex | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `CORS_ORIGINS` | `https://yourdomain.com` | Never use `*` in production |
| `SIMULATION_SYNC` | `false` | Use Celery in production |
| `REDIS_URL` | `redis://redis:6379/0` | Must match CELERY_BROKER_URL host |
| `CELERY_BROKER_URL` | `redis://redis:6379/1` | Separate DB index for broker |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/2` | Separate DB index for results |

Never commit `.env` to version control.

---

## 2. Database migrations

Run Alembic migrations before starting the API for the first time, and after every deployment:

```bash
# Inside the API container or on the host with DATABASE_URL set
python -m alembic upgrade head

# Verify current revision
python -m alembic current

# Check for pending migrations (CI check)
python -m alembic check
```

### Creating a new migration

```bash
python -m alembic revision --autogenerate -m "describe your change"
# Review the generated file in alembic/versions/ before applying
python -m alembic upgrade head
```

### Rolling back

```bash
# Roll back the last migration
python -m alembic downgrade -1

# Roll back to a specific revision
python -m alembic downgrade <revision_id>
```

---

## 3. Running with Docker Compose (recommended for staging/production)

```bash
# Build all images
docker compose build

# Start all services (detached)
docker compose up -d

# Follow logs
docker compose logs -f api worker

# Stop all services
docker compose down
```

The compose file starts:
- `postgres` — PostgreSQL 16
- `redis` — Redis 7
- `api` — FastAPI + Uvicorn (runs migrations on startup)
- `worker` — Celery worker (4 concurrency)
- `web` — Next.js frontend

---

## 4. Health checks

| Service | URL | Expected |
|---------|-----|----------|
| API | `GET /api/v1/health` | `{"status":"ok"}` |
| Web | `GET /` | HTTP 200 |

All Docker services include HEALTHCHECK directives. The `api` service waits for `postgres` and `redis` to be healthy before starting.

---

## 5. Backup and restore

### PostgreSQL backup

```bash
# Manual backup
docker exec -t aftermind-postgres-1 \
  pg_dump -U aftermind aftermind | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Restore
gunzip -c backup_YYYYMMDD_HHMMSS.sql.gz | \
  docker exec -i aftermind-postgres-1 psql -U aftermind aftermind
```

### Automated backups

Configure a cron job or cloud-managed backup (e.g. RDS automated snapshots, Fly.io volumes) to run daily backups. Retain at least 7 daily and 4 weekly snapshots.

---

## 6. Rollback plan

1. **Application rollback**: Deploy the previous Docker image tag.
   ```bash
   docker compose down
   # Update image tag in docker-compose.yml (or override with .env)
   docker compose up -d
   ```

2. **Database rollback**: Run `alembic downgrade -1` before deploying the older image.
   ```bash
   python -m alembic downgrade -1
   ```

3. **Immutable simulation results**: Completed `simulation_results` rows are never overwritten. Rollback does not affect historical simulation data.

---

## 7. Monitoring hooks

The API emits structured logs with:
- `X-Request-ID` on every response header
- `request_id`, `method`, `path`, `status`, `elapsed_ms`, `client` in log records

Recommended stack:
- **Logs**: Ship to Datadog, Loki/Grafana, or AWS CloudWatch
- **Metrics**: Expose Prometheus metrics with `prometheus-fastapi-instrumentator` (add to `pyproject.toml`)
- **Alerts**: Alert on error rate > 1%, P99 latency > 2s, worker queue depth > 100

---

## 8. CI/CD pipeline

The `.github/workflows/ci.yml` runs on every push to `main` and `develop`:

1. **backend-lint** — ruff format + check
2. **backend-test** — pytest (SQLite) with coverage ≥ 60%
3. **backend-security** — pip-audit dependency scan
4. **migration-check** — alembic upgrade head + alembic check
5. **frontend-lint** — tsc --noEmit + next lint
6. **frontend-build** — next build (production)
7. **docker-api** — docker build + startup health check
8. **secret-scan** — grep for common secret patterns

Deployments are **not** triggered automatically from CI — always require explicit approval before pushing to production.

---

## 9. Security checklist (pre-launch)

- [ ] `SECRET_KEY` is a unique, randomly generated 32-byte value
- [ ] `CORS_ORIGINS` contains only your production domain(s)
- [ ] Database uses a dedicated low-privilege user (not superuser)
- [ ] `SIMULATION_SYNC=false` — simulations run in Celery workers
- [ ] HTTPS/TLS is enforced at the load balancer or reverse proxy
- [ ] Rate limiting is active (built-in: 10 auth attempts / 60s per IP)
- [ ] `.env` is excluded from version control (`.gitignore` confirms)
- [ ] LLM API key is set only if LLM features are enabled
- [ ] Stripe keys are set only if payments are activated
- [ ] `pip-audit` passes in CI (or known vulnerabilities are accepted)
- [ ] `npm audit` passes in CI
