# AGENTS.md

## Project overview

This repository may be used as a portfolio project when applying for cloud or software engineering roles.

LeaseFlow is a cloud-native, multi-tenant rental management system built as an AWS architecture and backend portfolio project.

Primary goals:
- demonstrate AWS architecture thinking
- use Terraform as Infrastructure as Code
- build a production-relevant Python backend
- apply security-by-design
- keep the MVP realistic and cost-aware

This is not a feature-heavy SaaS product. Avoid unnecessary scope expansion.

---

## Learning mode

This is a learning project. Do not do everything end-to-end by default.

Prefer:
- explain reasoning briefly before changes
- propose small, reviewable steps
- leave suitable implementation tasks for the developer when requested
- include “what to learn next” notes after significant changes

Avoid:
- large opaque refactors without explanation
- solving every task in one pass when learning value is higher with guided steps

---

## Core architecture constraints

Preferred architecture:
- AWS API Gateway
- AWS Lambda (Python)
- Amazon Cognito
- Amazon RDS PostgreSQL
- EventBridge / Scheduler
- CloudWatch
- Terraform

Important constraints:
- PostgreSQL is used instead of DynamoDB
- multi-tenant isolation is mandatory
- `tenant_id` must exist in all relevant domain tables
- `tenant_id` must come from JWT claims, not trusted client input
- one backend Lambda is acceptable for MVP
- notifications are stored in the database first; email can come later
- app-level tenant isolation is enough for MVP; PostgreSQL RLS is a possible future improvement
- avoid NAT Gateway unless there is a strong reason
- RDS must not be publicly accessible
- use least-privilege IAM
- keep dev-stage cost low

---

## Working style

Before making changes:
1. read the relevant code first
2. prefer existing project structure over inventing new layers
3. make the smallest reasonable change
4. explain the plan briefly before large edits
5. do not rewrite unrelated code

When unsure:
- prefer simplicity over cleverness
- prefer explicit code over heavy abstraction
- prefer realistic MVP trade-offs over idealized enterprise patterns

Do not:
- introduce Kubernetes, containers, or microservices
- introduce a frontend framework unless explicitly requested
- replace the current architecture without a clear reason
- add expensive AWS services by default
- add ORM-heavy abstractions unless explicitly requested

---

## Truthfulness and uncertainty

Do not hallucinate or invent facts, APIs, AWS behavior, project requirements, or implementation details.

If you do not know:
- say clearly that you are not sure
- do not guess or fill gaps with plausible-sounding answers
- ask the developer for the missing context, documentation, or decision input
- prefer quoting or referencing repository docs over inventing architecture

If the repository or prompt does not provide enough information to make a safe decision:
- stop and ask for the relevant file, documentation, or requirement
- explain briefly what is missing and why it matters
- wait for clarification before making architecture-shaping assumptions

When making a recommendation:
- separate confirmed facts from assumptions
- label assumptions explicitly
- keep uncertain guidance provisional until verified

---

## Architectural priorities

When making design decisions, prioritize in this order:

1. tenant isolation and security
2. operational simplicity
3. cost awareness
4. clear and understandable architecture
5. developer productivity

Avoid adding complexity unless it clearly improves one of the above.

---
## Repository structure

- `backend/` = Python application code, migrations, tests
- `infra/` = Terraform infrastructure
- `docs/` = architecture, MVP scope, security, and related documentation

Treat this as a monorepo with clearly separated responsibilities.

---

## Backend guidance

Backend stack:
- Python
- PostgreSQL
- psycopg
- Alembic
- pytest

Prefer:
- parameterized SQL queries only
- explicit transaction handling
- clear auth and tenant isolation logic
- structured logging
- small, testable functions

Avoid:
- string-built SQL
- trusting `tenant_id` from request bodies
- hidden side effects
- broad framework adoption without need

Write operations that create domain state and audit records should be committed in a single transaction.

Critical rules:
- every tenant-scoped query must explicitly filter by `tenant_id`
- auth context must be derived from JWT claims
- audit logging is required for important write operations
- never return data across tenants, even accidentally

### AWS Lambda considerations

The backend runs in AWS Lambda.

Prefer:
- stateless request handling
- simple dependency structure
- minimal cold start overhead

Avoid:
- long-lived in-memory state
- heavy framework initialization
- unnecessary global objects

---

## Infrastructure guidance

Terraform is the source of truth for infrastructure.

Prefer:
- reusable but simple modules
- readable variable names
- minimal environment-specific duplication
- secure defaults

Avoid:
- public RDS
- unnecessary networking complexity
- wildcard IAM policies unless clearly justified
- adding services that are not required for the MVP

Always keep cost-awareness in mind.

---

## Documentation guidance

Keep docs concise and useful.

Important documents:
- `docs/mvp-scope.md`
- `docs/architecture-v0.2.md`
- `docs/security-baseline.md`

When architecture or implementation decisions change materially, update the relevant docs.

Do not commit private course materials, licensed PDFs, or other non-redistributable reference files.
Derived notes are fine; raw course documents are not.

---

## Testing and validation

Before finishing a task, run the smallest relevant validation.

For backend work, prefer these commands:

```bash
cd backend
pytest
```

If dependencies need to be installed:

```bash
cd backend
pip install -e ".[dev]"
```

For Terraform work, at minimum run formatting if Terraform is available:

```bash
cd infra
terraform fmt -recursive
```

If you change code, prefer updating or adding tests when practical.

---

## Context7 usage

If Context7 is available, prefer it for current official documentation on:
- psycopg
- pytest
- Terraform AWS provider
- AWS Lambda / API Gateway related libraries
- other libraries used directly in this repository

Use Context7 to verify current syntax and best practices before making library-specific changes.

Do not use Context7 for broad architecture invention when the repository docs already define the direction.

---

## Change strategy

Prefer this sequence:
- analyze existing code
- propose a minimal plan
- implement one focused change
- run relevant tests
- summarize changed files and remaining work

For larger tasks, keep the implementation incremental and reviewable.

---

## Good next-task examples

Good tasks:
- implement `POST /properties`
- implement `GET /properties`
- add migration for a new table
- add tests for tenant isolation
- refine Terraform module inputs/outputs
- improve audit logging for a write flow

Bad tasks:
- "rewrite the backend"
- "finish the whole MVP"
- "add all missing infrastructure"
- "replace current structure with a better pattern"

---

## Review expectations

When reviewing or generating changes, optimize for:
- correctness
- security
- tenant isolation
- cost-aware AWS usage
- operational simplicity
- maintainability

Call out architectural risks early if you notice them.

---

## Project context

This project is developed during an academy program.

Primary purpose:
- learn AWS architecture and cloud-native backend development
- practice Infrastructure as Code with Terraform
- practice event-driven backend design
- build a realistic portfolio project

The developer has a strong frontend background and is expanding into backend and cloud architecture.

Because this is a learning project:
- prefer clarity over clever abstractions
- prefer explicit architecture over hidden framework magic
- prefer realistic production patterns over toy examples

Target completion timeline: July 2026.
