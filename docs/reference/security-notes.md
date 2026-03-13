# LeaseFlow Security Notes (from `docs/reference/raw`)

This note distills only the security ideas that are directly useful for LeaseFlow's first backend vertical slice.

## Multi-tenant security

- Treat multi-tenant separation as a primary security boundary, not only a data-model detail.
- Prevent cross-tenant access caused by logic flaws, shared-component mistakes, or misconfigured IAM.
- Enforce tenant scoping in every data path (`tenant_id` required in reads/writes), and deny by default.
- Add layered isolation: API authorization checks + database-level controls (prepare for row-level security later).

## Authentication and authorization

- Build around strong identity signals and continuous verification (Zero Trust mindset).
- Require strong authentication at the edge, then enforce authorization in backend logic for each operation.
- Use least privilege for both users and service identities; scope access to exact actions and resources.
- Prefer short-lived credentials/tokens and avoid long-lived secrets in code, logs, or CI artifacts.

## Secure database access

- Use parameterized SQL/ORM patterns everywhere to reduce injection risk.
- Encrypt data in transit and protect credentials with a dedicated secret manager (not plaintext config).
- Restrict DB network exposure and access paths; private networking + tightly scoped security groups.
- Include vulnerability and dependency checks in the development lifecycle, since DB risk often comes through application flaws.

## Audit logging

- Keep tamper-resistant, structured audit trails for critical domain events (who did what, when, and in which tenant).
- Separate operational logs from security/audit events, but correlate them via request/user/tenant identifiers.
- Redact sensitive values in logs and define retention plus review practices.
- Monitor privileged access changes and security-relevant actions as part of regular audits.

## Cloud security controls

- Follow shared-responsibility thinking: cloud provider secures the platform, LeaseFlow secures workload configuration and code.
- Apply least-privilege IAM, segmentation, and deny-by-default policies for services and infrastructure.
- Use defense in depth: network controls, identity controls, encryption, monitoring, and incident response runbooks.
- Shift security left in CI/CD: SAST, dependency scanning, secret scanning, IaC scanning, and policy checks before deploy.
- Plan resilience controls early: backups, restore testing, alerting thresholds, and incident reporting workflows.

## Practical implications for LeaseFlow now

- Keep tenant isolation explicit in `POST /properties` and `GET /properties` tests (including negative cross-tenant cases).
- Validate that audit logging records actor, tenant, action, entity, and timestamp for property events.
- Keep DB credentials in managed secrets, rotate regularly, and ensure app/infra roles cannot overreach.
- Add CI security gates incrementally so security checks are routine, not a separate late-phase task.
