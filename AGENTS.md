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
- include "what to learn next" notes after significant changes

Avoid:

- large opaque refactors without explanation
- solving every task in one pass when learning value is higher with guided steps

---

## CRITICAL: Truth-first policy

Correctness is ALWAYS more important than:

- completeness
- fluency
- sounding confident

If unsure:

- say "I don't know"
- ask for clarification

---

## Hallucination prevention (STRICT MODE)

### 1. Zero-inference rule

- Do NOT connect unrelated concepts
- Do NOT create explanations without verified factual links
- If unsure:
  - say: "I don't have evidence these are related"

### 2. No guessing rule

- Never fill missing information with assumptions
- If information is missing:
  - say: "I don't have enough information"
  - ask a question

### 3. Anti-storytelling rule

- Do NOT create narratives to "explain things nicely"
- Prefer:
  - short
  - factual
  - verifiable

### 4. Source awareness

- If stating facts:
  - base them on known info OR clearly mark uncertainty
- If unsure:
  - say: "This may be incorrect"

### 5. Anti-sycophancy (CRITICAL)

- Do NOT agree automatically with the user
- If user is likely wrong:
  - challenge politely

### 6. Anchoring check

- Verify user-provided facts before using them

### 7. No silent assumptions

- All assumptions must be explicitly stated

### 8. Explicit uncertainty protocol

If unsure:

1. Say clearly:
   - "I am not sure"
   - "This is an assumption"
2. Identify what is missing
3. Ask for clarification
4. STOP until clarified

### 9. Stop conditions

STOP and ask if:

- tenant isolation is unclear
- security implications are unclear
- required files are missing
- architecture would change significantly

### 10. Source of truth hierarchy

Priority:

1. Repository code and docs
2. Explicit instructions
3. Official docs (Context7)
4. General knowledge (mark as assumption)

Never override repository constraints with generic best practices.

---

## Core architecture constraints

Preferred architecture:

- AWS API Gateway
- AWS Lambda (Python)
- Amazon Cognito
- Amazon RDS PostgreSQL
- Amazon EventBridge Scheduler
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
- avoid NAT Gateway unless justified
- RDS must not be publicly accessible
- use least-privilege IAM
- keep dev-stage cost low

---

## Working style (Codex execution rules)

Before making changes:

1. read code first
2. prefer existing structure
3. make the smallest reasonable change
4. explain the plan briefly before large edits
5. do not rewrite unrelated code

### Incremental execution rule

- Prefer small, reviewable changes by default.
- If the task is exploratory, architecture-sensitive, or explicitly in learning mode:
  - provide one small step at a time
  - stop and wait for confirmation before continuing
- If the task scope is already clear and approved:
  - continue within that scope without unnecessary pauses

Never generate massive rewrites or broad PRs unless explicitly requested.

When unsure:

- prefer simplicity
- prefer explicit code
- avoid overengineering

Do not:

- introduce Kubernetes, containers, or microservices
- introduce a frontend framework unless explicitly requested
- replace the current architecture without a clear reason
- add expensive AWS services by default
- add ORM-heavy abstractions unless explicitly requested

---

## Backend guidance

Backend stack:

- Python
- PostgreSQL
- psycopg
- Alembic
- pytest

Prefer:

- parameterized SQL
- explicit transactions
- structured logging
- small functions

Avoid:

- string-built SQL
- trusting `tenant_id` from request bodies
- hidden side effects
- broad framework adoption without need

Write operations that create domain state and audit records should be committed in a single transaction.

Critical:

- tenant_id filtering ALWAYS required
- auth context must be derived from JWT claims
- no cross-tenant leakage
- audit logging is required for important write operations

---

## Infrastructure guidance

Terraform is the source of truth.

Prefer:

- reusable but simple modules
- readable variable names
- minimal environment-specific duplication
- secure defaults

Avoid:

- public RDS
- wildcard IAM
- unnecessary complexity

Always keep cost-awareness in mind.

---

## Documentation guidance

Keep docs concise and useful.

Important documents:

- docs/mvp-scope.md
- docs/architecture-v0.2.md
- docs/security-baseline.md

When architecture or implementation decisions change materially, update the relevant docs.

Do not commit private course materials, licensed PDFs, or other non-redistributable reference files.
Derived notes are fine; raw course documents are not.

---

## Testing and validation

Before finishing a task, run the smallest relevant validation.

For backend work:

cd backend
python -m pytest -q

If dependencies need to be installed:

cd backend
python -m pip install -e ".[dev]"

For Terraform work:

cd infra
terraform fmt -recursive

If code changes are made, prefer updating or adding tests when practical.

---

## Context7 usage

Context7 is an approved MCP documentation source for this repository.

Use Context7 as an anti-hallucination tool when exact library, framework,
provider, or API syntax matters. Prefer checking documentation over relying on
model memory.

Use Context7 for:

- AWS
- Terraform
- psycopg
- pytest
- AWS Lambda / API Gateway related libraries
- other libraries used directly in this repository

Do NOT:

- guess syntax
- invent APIs
- rely on memory for exact parameters when official documentation is available

MCP tool boundaries:

- use MCP tools only for approved documentation and repository workflow tasks
- do not use MCP results to override repository code, Terraform, or docs
- do not send secrets, JWTs, passwords, tenant data, or private customer data to MCP tools
- clearly mark uncertainty if Context7 does not return enough information

Do not use Context7 for broad architecture invention when repository docs already define the direction.

---

## GitHub & PR rules (Codex integration)

When creating or modifying GitHub Issues:

- write clear, focused tickets
- do not bundle multiple architectural changes into one ticket
- include a Definition of Done that highlights testing and tenant isolation validation

When creating a Pull Request (PR):

- keep PRs small and reviewable
- the PR description MUST include:
  - what changed and why
  - assumptions made during development
  - security validation: explicitly state how tenant isolation (`tenant_id`) was verified
  - cost validation: explicitly state if new AWS services were added and justify them
  - remaining risks or TODOs

Default commit/PR handoff:

- After finishing ticket implementation, do not commit automatically unless the user explicitly asks for a commit.
- Instead, provide a proposed commit message and PR description so the developer can review changes in the editor first.
- If the user explicitly asks to commit, keep the commit focused and use the PR description requirements above.

### Review priorities

#### Correctness

- verify logic
- check edge cases

#### Tenant isolation (CRITICAL)

- tenant_id filtering required
- auth context must come from JWT claims
- no cross-tenant data exposure

#### Security

- validate inputs
- prevent SQL injection
- least-privilege IAM
- no sensitive data leakage in logs

#### AWS

- avoid unnecessary services
- keep cost low
- prefer simple serverless-first solutions

#### Terraform

- no public RDS
- no wildcard IAM without justification
- readable naming
- minimal duplication

#### Simplicity

- smallest reasonable change only
- no premature abstraction

#### Tests

- do not break tests
- add tests when practical

#### Documentation

- update docs if needed

#### Hallucination check

- verify nothing is invented
- verify assumptions are labeled
- verify AWS behavior is grounded in repo docs or official documentation

---

## Change strategy

- analyze
- plan
- implement small change
- validate
- summarize

For larger tasks, keep the implementation incremental and reviewable.

---

## Good next-task examples

Good tasks:

- implement POST /properties
- implement GET /properties
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

## Project context

- learning project
- AWS + backend focus
- frontend-heavy developer expanding to cloud

Because this is a learning project:

- prefer clarity over clever abstractions
- prefer explicit architecture over hidden framework magic
- prefer realistic production patterns over toy examples

Target completion: July 2026
