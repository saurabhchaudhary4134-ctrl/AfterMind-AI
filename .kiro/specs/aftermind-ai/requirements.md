# AfterMind AI — Requirements

## 1. Overview

AfterMind AI is a decision-intelligence platform. Users describe decisions, structure
assumptions into a "Decision DNA" model, build scenarios, run Monte Carlo
simulations, analyze risk and sensitivity, compare scenarios, receive explainable
reports, and later record actual outcomes to evaluate forecast accuracy.

## 2. User stories

### Authentication & workspaces
- US-1: As a visitor, I can register and sign in securely.
- US-2: As a user, I can view and edit my profile.
- US-3: As a user, I am assigned a personal workspace on registration.
- US-4: As a workspace owner, I can invite members and assign roles.
- US-5: As a member, I can only access resources in my workspace.

### Decisions
- US-6: As a user, I can create a decision with a title, description, objective, time
  horizon, and constraints.
- US-7: As a user, I can edit, archive, and delete decisions I own.
- US-8: As a user, I can view version history of a decision.
- US-9: As a user, I can define measurable outcome metrics for a decision.

### Decision DNA
- US-10: As a user, I can define variables with units, ranges, and distributions.
- US-11: As a user, I can define assumptions with values and confidence levels.
- US-12: As a user, I can define formulas linking variables to outcomes.
- US-13: As a user, I can define dependencies between variables.
- US-14: The system validates the Decision DNA for circular dependencies, invalid
  formulas, and missing fields before simulation.

### LLM extraction
- US-15: As a user, I can describe a decision in natural language and receive a
  structured draft (variables, assumptions, objectives).
- US-16: The system highlights missing assumptions for my review.
- US-17: I must confirm extracted assumptions before they are used in simulation.
- US-18: The simulation engine works fully without the LLM provider.

### Scenarios
- US-19: As a user, I can create named scenarios with assumption overrides.
- US-20: As a user, I can duplicate and edit scenarios.
- US-21: As a user, I can compare scenarios side-by-side.

### Simulation
- US-22: As a user, I can launch a simulation with configurable iterations and a
  reproducible random seed.
- US-23: The system queues the simulation and I can track its status.
- US-24: As a user, I can view percentile summaries, threshold probabilities, and
  downside-risk metrics.
- US-25: As a user, I can reproduce a past simulation from its stored configuration.

### Sensitivity & risk
- US-26: As a user, I can view a tornado chart of variable sensitivities.
- US-27: As a user, I can explore what-if scenarios interactively.
- US-28: The system explains model limitations transparently.

### Results & reports
- US-29: As a user, I can view persisted simulation results.
- US-30: As a user, I can export a report (JSON, CSV summary).
- US-31: Completed simulation results are immutable.

### Reality feedback loop
- US-32: As a user, I can record actual outcomes for a decision.
- US-33: The system computes forecast errors and calibration where sample size allows.
- US-34: The system displays sample sizes and limitations; it never claims statistical
  significance without adequate data.

### Platform
- US-35: As a user, I see useful empty states and an interactive sample decision.
- US-36: As a user, I can manage my subscription tier and view quota usage.
- US-37: As a user, I can access help and settings.

## 3. Functional requirements

| ID    | Requirement |
|-------|-------------|
| FR-1  | JWT auth with access + refresh tokens; password hashing with bcrypt/argon2 |
| FR-2  | Workspace CRUD; workspace_members with roles (owner, admin, member, viewer) |
| FR-3  | Decision CRUD with version history (decision_versions) |
| FR-4  | Decision DNA schema: variables (name, unit, distribution, params), assumptions, formulas, dependencies, objectives |
| FR-5  | Safe formula evaluator (restricted AST, no eval/exec) |
| FR-6  | LLM extraction endpoint returning validated Pydantic schemas; human confirmation required |
| FR-7  | Scenario CRUD with assumption overrides; duplication; comparison |
| FR-8  | Monte Carlo engine: seeded sampling, explicit distributions, deterministic formulas |
| FR-9  | Statistics: percentiles (P10, P25, P50, P75, P90), mean, std dev, threshold probability, CVaR, downside risk |
| FR-10 | Sensitivity analysis: tornado chart data, one-at-a-time variation |
| FR-11 | Simulation job lifecycle: queued, running, completed, failed, cancelled |
| FR-12 | Worker: retries (configurable), timeout, progress reporting, result persistence |
| FR-13 | Quota enforcement per subscription tier (simulations/month, LLM calls/month) |
| FR-14 | Actual outcome recording; forecast error (MAE, MAPE, bias); calibration (where n sufficient) |
| FR-15 | Audit events: who, what, when, resource_id, workspace_id |
| FR-16 | Report export: JSON, CSV |
| FR-17 | Health check, current user, OpenAPI docs endpoints |

## 4. Non-functional requirements

| ID    | Requirement |
|-------|-------------|
| NFR-1 | API responses < 500ms for non-simulation endpoints under normal load |
| NFR-2 | Simulation engine handles up to 100k iterations in < 30s for typical models |
| NFR-3 | Frontend Lighthouse accessibility score ≥ 90 |
| NFR-4 | All API input validated; no unhandled 500s in production paths |
| NFR-5 | Test coverage ≥ 70% for simulation engine and services |
| NFR-6 | No secrets in repository; .env.example documents all variables |
| NFR-7 | Docker builds succeed; docker-compose starts the stack |
| NFR-8 | Migrations are forward-only and tested |

## 5. Constraints

- The simulation engine is pure Python with zero web/DB/framework imports.
- No `eval`, `exec`, or `compile` of user-supplied input.
- LLM provider is pluggable and optional; core sim works without it.
- Completed simulation results cannot be silently overwritten.
- Payment integration requires explicit configuration and authorization.
- No hardcoded fake results in production code paths.

## 6. Out of scope (initial release)

- Real-time collaborative editing.
- Mobile native apps (responsive web only).
- Custom predictive model training UI (models added programmatically with data).
- SSO/SAML (business tier placeholder only).
