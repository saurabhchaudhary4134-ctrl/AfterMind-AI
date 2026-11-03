# AfterMind AI — Product Steering

## What we are building

AfterMind AI is a decision-intelligence platform that helps users understand the
possible consequences of decisions **before** taking action. A user describes a
decision, defines assumptions and constraints, explores alternative scenarios,
runs probabilistic simulations, analyzes risk, compares outcomes, and later
evaluates predictions against actual results.

The product is a working application, not a UI mockup. Every button and form on a
production flow must perform a real action. Hardcoded fake results are forbidden in
production code paths.

## Guiding principles

1. **Decisions before predictions.** The core value is structured decision modeling
   and Monte Carlo simulation. LLM features augment this; they never replace it.
2. **Honesty about uncertainty.** Never present user assumptions as validated facts.
   Clearly separate facts, user assumptions, model estimates, and unknowns.
3. **Reproducibility.** Every simulation stores its seed, engine version, model
   version, and configuration snapshot so results can be reproduced and audited.
4. **Tenant isolation.** No data leaks between workspaces. Every protected resource
   checks ownership server-side.
5. **Graceful degradation.** The simulation engine works without an LLM provider.
   LLM failures degrade to manual entry, never to fabricated data.
6. **Safety first.** No `eval`, no arbitrary code execution, no trusting LLM output
   without validation, no secrets in the repo.

## Target users

- Individual analysts and founders evaluating strategic decisions.
- Teams that need to compare scenarios and track forecast accuracy over time.
- Organizations that require audit trails, role-based access, and exportable reports.

## Subscription tiers

| Tier     | Purpose                                   |
|----------|-------------------------------------------|
| Free     | Explore the product with limited quotas   |
| Pro      | Individual professional use               |
| Team     | Collaborative workspaces with members     |
| Business | Advanced quotas, SSO-ready, audit exports |

Pricing is not invented. Quotas are enforced on the backend. Payment integration is
optional and only activated after explicit configuration and authorization.

## Definition of done (project level)

A user can authenticate, create and save a decision, review structured assumptions,
define scenarios, launch a real simulation, track the background job, view persisted
results and uncertainty metrics, compare scenarios, inspect explanations, record
actual outcomes, and revisit the project later. Access controls prevent
cross-workspace data leakage. Tests and deployment instructions are present.
