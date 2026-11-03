# AfterMind AI — Security Steering

## Authentication & sessions

- Use a maintained authentication solution (JWT-based with refresh tokens, or an
  external provider). Never roll your own crypto.
- Access tokens are short-lived. Refresh tokens are stored securely (httpOnly,
  SameSite cookies where applicable) and rotated on use.
- Passwords are hashed with bcrypt or argon2 — never stored or logged in plaintext.

## Authorization & tenant isolation

- Every protected endpoint verifies the caller's identity and workspace membership.
- Every tenant-scoped DB query filters by `workspace_id`. No cross-workspace reads or
  writes are possible regardless of what ID is passed.
- Role checks happen server-side. The frontend only hides/shows UI; it never
  authorizes.
- Prevent IDOR: resource IDs are validated against the caller's workspace before any
  action.

## Input validation & injection prevention

- All API input is validated with Pydantic schemas. Reject early, reject clearly.
- SQL injection: use ORM parameterized queries only. No string-interpolated SQL.
- Formula injection: the simulation formula evaluator uses a restricted, safe parser.
  No `eval`, no `exec`, no `compile` of user input, no access to builtins.
- Prompt injection: LLM output is treated as untrusted data. It is validated with
  Pydantic and never executed, stored as-is into critical fields, or given DB/code
  access. LLM suggestions require human confirmation before simulation.
- Input size limits on all endpoints. File uploads (if any) are size-restricted and
  type-checked.

## Secrets & configuration

- Secrets come from environment variables only. Never hardcode secrets in code.
- `.env.example` documents variables with placeholder values. Real `.env` is gitignored.
- Never commit real credentials, API keys, or tokens.

## Rate limiting & quotas

- API endpoints are rate-limited (per-user and per-IP) to prevent abuse.
- Simulation job quotas are enforced per subscription tier.
- LLM extraction has its own token and request budgets.

## Data protection

- Redact sensitive data (tokens, passwords, PII) from logs.
- Provide data export and deletion workflows.
- Define retention policies for simulation results and audit logs.
- Do not expose private information between workspaces.

## Dependency & supply chain

- Pin dependency versions. Prefer well-known, actively maintained packages.
- Scan dependencies for known vulnerabilities (pip-audit / npm audit).
- Scan container images in CI.
- Flag unusual package names (possible typosquatting).

## CORS & transport

- CORS is restricted to known origins. Never use `*` in production.
- All transport is HTTPS in production. Secure cookies where applicable.

## Webhook security (when payment integration is active)

- Verify webhook signatures. Reject unsigned or replayed events.
- Handle duplicate webhook events idempotently.

## What the LLM may never do

- Authorize database access.
- Execute code.
- Invent evidence or fabricate simulation results.
- Bypass human confirmation for extracted assumptions.
- Write directly to the database without validation.

## Verification

- Security tests: unauthorized access attempts, IDOR attempts, injection attempts,
  formula injection attempts, oversized payloads, and cross-tenant reads.
- Report what was verified and what requires external services to fully validate.
