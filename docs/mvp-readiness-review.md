# LeaseFlow Backend and Infra MVP Readiness Review

## Review Context

Date: 2026-04-20

Reviewed state:

- Branch: `main`
- Commit: `3552ad5 docs: add MVP demo flow and refresh architecture diagram (#74)`
- Latest `main` CI result: passed
- CI run: `https://github.com/Alpine78/leaseflow/actions/runs/24566811654`
- Related ticket: `#75 Backend + Infra MVP readiness review`

Purpose:

- capture the current backend and infrastructure MVP state
- make portfolio review easier
- separate MVP readiness from production readiness

This is not a production certification.

## Implemented MVP

Backend capabilities:

- Public health route: `GET /health`
- Tenant-scoped property flow: `GET /properties`, `POST /properties`, `PATCH /properties/{property_id}`
- Tenant-scoped lease flow: `GET /leases`, `POST /leases`, `PATCH /leases/{lease_id}`
- Reminder candidate query: `GET /lease-reminders/due-soon`
- Notification flow: `GET /notifications`, `PATCH /notifications/{notification_id}/read`
- Internal Lambda events for deployed DB migrations and due reminder scans
- Audit logging for important property and lease write operations

Tenant isolation:

- `tenant_id` comes from validated Cognito JWT claims.
- Client-supplied `tenant_id` is not trusted as tenant context.
- Tenant-scoped reads and writes filter by `tenant_id`.

Infrastructure capabilities:

- Terraform-managed AWS dev environment
- S3 remote state bootstrap path with native Terraform S3 lockfile locking
- API Gateway HTTP API with JWT authorization
- CloudFront + private S3 frontend hosting path
- Python Lambda backend
- Cognito user pool and app client
- Private RDS PostgreSQL
- SSM SecureString for runtime DB password retrieval
- VPC interface endpoints for private SSM and KMS access
- EventBridge Scheduler for the daily reminder scan
- CloudWatch Logs and baseline CloudWatch alarms
- SNS topic as the baseline alarm action target
- Optional dev email subscription for the SNS topic when configured and confirmed

## Validation Evidence

Automated validation:

- Latest `main` CI passed for backend checks, Terraform formatting, dev environment validation, and Terraform module tests.
- CI is credential-free and does not run `terraform plan` or `terraform apply`.

Deployed validation:

- `docs/runbooks/evidence/deployed-dev-smoke-test-2026-04-16.md`
- The smoke test validated API Gateway, Cognito, Lambda, private RDS, migrations, protected API calls, tenant override handling, reminder scan, notifications, read acknowledgement, Cognito cleanup, and stack destroy.

Documentation-backed API review:

- `docs/runbooks/evidence/context7-api-usage-review-2026-04-15.md`
- The review checked selected Terraform AWS provider usage, psycopg usage, and boto3 SSM password resolution.
- Result: no code or Terraform changes were required.

Restore validation:

- `docs/runbooks/evidence/dev-rds-restore-validation-2026-04-14.md`
- The restore validation evidence supports the dev backup and restore story, but it does not make the workload production-grade DR.

Architecture documentation:

- `docs/architecture-v0.2.md` reflects the current backend and infrastructure shape.
- `docs/diagrams/leaseflow-architecture.d2` and the generated SVG include API Gateway, Cognito, Lambda, private RDS tables, EventBridge Scheduler, CloudWatch alarms, SNS alarm topic, and private secret access.

## Not Production-Ready

The current state is a validated dev MVP, not a production workload.

Known limitations:

- Terraform state now has a dev S3 remote-state path, but this is still not a
  complete production environment strategy.
- Dev RDS is single-instance and cost-controlled, not a highly available production database design.
- RDS deletion behavior is dev-oriented; destroy removes dev data.
- The repo now has a first browser frontend slice and Terraform-managed hosted
  frontend path, but later screens remain outside this backend+infra review.
- SNS alarm actions exist, but an SNS topic alone is not human notification delivery.
- Optional email delivery requires a configured address and confirmed subscription.
- There is no full incident workflow, escalation policy, dashboard suite, or on-call process.
- There is no production DR automation, cross-region recovery, load testing, or performance baseline.
- Tenant isolation is application-level; PostgreSQL Row Level Security remains a future defense-in-depth option.
- The deployed smoke test was executed once as evidence, not as a continuously scheduled production synthetic check.

## Current Risks and Assumptions

Assumptions:

- Dev stack cost is controlled by destroying the stack after validation when it is not needed.
- Current CI is enough for repository-level regression checks, but it does not prove live AWS behavior.
- Deployed smoke evidence is historical evidence from 2026-04-16 and should be rerun after meaningful backend, migration, or Terraform changes.

Risks:

- Terraform state access remains sensitive because state can contain generated
  password material and other infrastructure details.
- Remote state improves collaboration and recovery, but it still requires
  disciplined IAM access and operator workflow.
- Sparse CloudWatch metrics and missing-data treatment can make alarm timing non-obvious.
- Optional email alarm delivery can fail operationally if the SNS subscription is not confirmed.
- The backend has no delete/archive flows, so API-created synthetic domain data is normally cleaned up through dev stack destroy.

## Recommended Next Phase

Recommended default:

- Continue the browser frontend after the auth, CORS, and hosting foundation.

Why:

- Backend and infra are now mostly validated for MVP use.
- The next natural step is completing user-facing frontend flows on top of the
  validated backend and infra MVP.
- The frontend direction is now documented separately in
  `docs/frontend-mvp-strategy.md`.

Other valid next phases:

- Production-readiness hardening: remote Terraform state, stronger operational alerting, production-like DR design, and stricter runtime controls.
- AWS SAA-C03 study extraction: turn the project decisions into exam-focused notes about serverless, private networking, RDS, IAM, monitoring, and operational tradeoffs.
- Frontend MVP: continue hosted validation after auth, dashboard, properties,
  leases, reminders, and notifications.

Production-readiness hardening is scoped in
`docs/production-readiness-hardening.md`.

## Final Assessment

Backend MVP: mostly ready for portfolio review.

Infrastructure MVP: mostly ready for dev-stage portfolio review.

Production readiness: not claimed.

The strongest current story is:

```text
LeaseFlow demonstrates a tenant-aware AWS backend MVP with Terraform-managed dev infrastructure,
remote-state bootstrap support, local and CI validation, deployed smoke evidence, operational runbooks, baseline alarms,
and explicit documentation of the remaining production-readiness gaps.
```
