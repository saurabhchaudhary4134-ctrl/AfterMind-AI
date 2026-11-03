# AfterMind AI — Coding Standards

## General

- Match existing patterns in the codebase. Do not introduce new libraries or
  paradigms when an existing one suffices.
- Keep changes focused. A bug fix does not require surrounding cleanup. A feature
  gets the code it needs, not speculative abstractions.
- Never leave dead code, commented-out blocks, or `TODO` without a linked issue.

## Python (services/api)

- Python 3.12+ compatible syntax. Type hints required on all function signatures.
- Line length: 100 characters.
- Use `uv` or `pip` with a pinned `requirements.txt` / `pyproject.toml`.
- Formatting: `ruff format`. Linting: `ruff check`.
- Imports: stdlib → third-party → local, separated by blank lines.
- Pydantic v2 for all request/response schemas. Use `model_config = ConfigDict(...)`.
- SQLAlchemy 2.x style (typed mapped columns, `Mapped`, `mapped_column`).
- Every async DB function uses the session from `app/db/session.py`.
- Repository methods always filter by `workspace_id` on tenant-scoped tables.
- No raw SQL with string interpolation. Use parameterized queries or ORM methods.
- Tests: `pytest`. Name files `test_*.py`. Each test asserts something specific.
- The simulation engine (`app/simulation/`) must have **zero** imports from FastAPI,
  SQLAlchemy, Celery, or any HTTP/DB code.

## TypeScript (apps/web)

- TypeScript strict mode. No `any` unless explicitly justified with a comment.
- Next.js App Router conventions: `app/` for routes, `components/` for UI.
- Tailwind CSS utility classes. shadcn/ui for primitives.
- API calls go through a typed client in `lib/api/` that reads from `NEXT_PUBLIC_API_URL`.
- Forms: controlled inputs, `react-hook-form` + `zod` validation.
- Loading: skeleton components, not spinners alone.
- Errors: inline validation messages + toast for unexpected failures.
- Charts: Recharts. Responsive containers.
- Accessibility: semantic HTML, `aria-*` where needed, keyboard navigable, visible
  focus states. Color contrast ≥ 4.5:1 for text.
- Tests: Vitest for units, Playwright for E2E.

## Naming

- Python: `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_SNAKE`
  for constants.
- TypeScript: `camelCase` for variables/functions, `PascalCase` for types/components.
- Database tables: `snake_case` plural. Columns: `snake_case`.
- API paths: `kebab-case` or `snake_case` resource names under `/api/v1`.

## Error handling

- API errors use a consistent JSON shape: `{ "detail": "...", "code": "..." }`.
- HTTP status codes: 200, 201, 202, 204, 400, 401, 403, 404, 409, 422, 429, 500.
- Never expose stack traces or internal error details to clients in production.
- Log the full error server-side with a request ID.

## Commits (when git is available)

- Conventional commits: `feat:`, `fix:`, `test:`, `docs:`, `chore:`, `refactor:`.
- Keep commits atomic and reviewable.

## Verification

- Run linters and type checks before claiming a task is done.
- Run relevant tests. If a test fails, fix the code, do not delete the test.
- Report exact commands and their output.
