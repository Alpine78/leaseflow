# LeaseFlow Security Baseline

## Purpose

This document defines the minimum security baseline for LeaseFlow. Its purpose is to show practical security-by-design decisions for a low-cost AWS MVP without adding controls that are disproportionate to the project scope.

## Security Principles

- **Security by Design**: Security requirements are part of the architecture, data model, API design, and Terraform definitions from the start.
- **Least Privilege**: Users, Lambda functions, and infrastructure roles receive only the permissions required for their specific actions.
- **Multi-Tenant Isolation**: Tenant boundaries are enforced in authentication, authorization, database access, and audit logging.
- **Defense in Depth**: LeaseFlow combines identity controls, application validation, database restrictions, network controls, and logging rather than relying on a single safeguard.
- **Cost-Aware Security**: The baseline favors built-in AWS capabilities and simple engineering controls that materially reduce risk without creating unnecessary cost or operational burden.

## System Context

LeaseFlow is an AWS-based, multi-tenant rental management system built with:

- Amazon API Gateway for HTTPS API exposure
- AWS Lambda (Python) for backend application logic
- Amazon Cognito for authentication and token issuance
- Amazon RDS for PostgreSQL as the primary relational datastore
- Amazon EventBridge and Scheduler for background and timed workflows
- Amazon CloudWatch for logs, metrics, and operational visibility
- Terraform for infrastructure provisioning and change control

Sensitive data handled by the system may include:

- User identity data and tenant membership information
- Rental, lease, payment-related, and property management records
- Audit events and operational logs
- Secrets and connection details used by the runtime

## Security Principles Applied to the MVP

- Use Cognito-issued JWTs as the source of authenticated identity.
- Enforce authorization in application code for every tenant-scoped operation.
- Keep the database private and reachable only by approved application paths.
- Avoid storing or logging more sensitive data than the MVP needs.
- Detect common failure modes early through CI checks, structured logs, and audit trails.

## Top Threats

### Spoofing

Risk:
Attackers may try to impersonate users or services through stolen credentials, forged tokens, or weak identity checks.

Mitigations:

- Use Amazon Cognito for authentication instead of custom password handling.
- Validate JWT signature, issuer, audience, expiry, and required claims on every protected request.
- Derive user identity and tenant context from validated token claims, not from client-supplied fields.
- For tenant-scoped HTTP API calls, use the Cognito ID token so the backend receives `custom:tenant_id`.
- Require strong password policy and support MFA in Cognito as the account base matures.
- Use short-lived tokens and avoid long-lived static credentials for workloads.

### Tampering

Risk:
Attackers may try to modify tenant data, API requests, infrastructure definitions, or background event flows.

Mitigations:

- Use parameterized SQL for all database access.
- Validate input shape, type, and allowed values at the API boundary.
- Enforce authorization checks before every write operation.
- Store infrastructure in Terraform and review changes through version control.
- Restrict Lambda IAM permissions so functions cannot modify unrelated resources.

### Repudiation

Risk:
Users or operators may deny having performed a sensitive action if events are not traceable.

Mitigations:

- Write structured application logs to CloudWatch with request ID, user ID, tenant ID, action, and result.
- Maintain an audit log table in PostgreSQL for security-relevant business actions.
- Record who performed an action, when it happened, which tenant was affected, and the target entity.
- Avoid mutable or ambiguous audit records.

### Information Disclosure

Risk:
The highest MVP risk is cross-tenant data leakage, followed by secret exposure, overly broad logs, and public cloud misconfiguration.

Mitigations:

- Enforce tenant-scoped queries for every read and write.
- Never trust `tenant_id` from the client when determining access scope.
- Keep RDS non-public and limit access through restrictive security groups.
- Store secrets outside the repository in AWS Systems Manager Parameter Store `SecureString`.
- Encrypt data at rest and require TLS in transit.
- Redact or avoid sensitive values in logs, errors, and debug output.

### Denial of Service

Risk:
API abuse, malformed traffic, or noisy tenant behavior may degrade service availability or create avoidable cost.

Mitigations:

- Enable API Gateway throttling and request validation.
- Apply application-level input validation to reject obviously invalid or abusive requests early.
- Use CloudWatch metrics and alarms for backend Lambda errors, Lambda throttles, HTTP API 5xx responses, scheduler target failures, and unusual invocation spikes.
- Publish baseline alarm-state changes to the environment SNS alarm topic for AWS-native notification fan-out.
- Keep scheduled and event-driven tasks idempotent to reduce cascading retries.
- Size the MVP conservatively and prefer simple protective limits over complex resilience features.

### Elevation of Privilege

Risk:
A user or compromised function may gain broader access than intended through weak authorization, broad IAM permissions, or admin/user boundary mistakes.

Mitigations:

- Enforce role-based and tenant-aware authorization in the backend.
- Separate normal user actions from administrative actions in both code and IAM design.
- Apply least-privilege IAM policies to Lambda execution roles.
- Avoid shared admin credentials and avoid default or hardcoded credentials entirely.
- Review Terraform for excessive permissions and public exposure before deployment.

## Multi-Tenant Isolation

- Every tenant-owned table must include `tenant_id`.
- Tenant context must be extracted from validated JWT claims.
- `custom:tenant_id` should come from a Cognito custom user attribute that is readable but not client-writable.
- All queries that access tenant data must be explicitly tenant-scoped.
- `tenant_id` provided by the client must never be trusted as the authorization source.
- Service logic must verify that the authenticated user is allowed to act within the resolved tenant.
- Cross-tenant administrative access is not part of the normal MVP request path and must be tightly controlled if introduced.
- PostgreSQL Row Level Security is a useful future hardening step, but it is not required for the MVP baseline if strict application-layer tenant enforcement is consistently applied.

## Secrets Management

- No secrets are stored in the Git repository, Terraform variables files committed to source control, or Lambda source code.
- Runtime secrets are stored in AWS Systems Manager Parameter Store as `SecureString` values.
- Lambda retrieves required secrets at runtime using IAM-scoped access.
- When Lambda runs in private subnets without NAT, secret resolution must use private AWS service connectivity such as interface VPC endpoints for SSM and KMS.
- Secrets must not be printed to logs, returned in API responses, or embedded in error messages.
- Rotate secrets when exposure is suspected or when credentials change.

## Secure Coding Practices

- Use parameterized SQL queries only.
- Validate and normalize request input at the API boundary.
- Use deny-by-default authorization logic for protected operations.
- Avoid sensitive logging, especially tokens, passwords, connection strings, and personal data.
- Handle errors without exposing stack traces or internal implementation details to clients.
- Keep dependencies pinned and updated to reduce exposure to known vulnerabilities.

## Logging and Audit

- Application logs must be structured and written to CloudWatch.
- Logs should include timestamp, severity, request ID, user ID when available, tenant ID when relevant, action name, and outcome.
- Audit events should be stored in PostgreSQL for business and security traceability.
- Baseline CloudWatch alarms should exist for backend Lambda errors, backend Lambda throttles, HTTP API 5xx responses, and reminder scheduler target failures.
- Baseline alarms publish to an environment SNS topic; optional dev email delivery starts only after the recipient confirms the SNS subscription email.

Examples of auditable events:

- User sign-in and sign-in failure patterns
- Tenant membership or role changes
- Lease creation, update, or deletion
- Payment status changes
- Manual overrides and administrative actions
- Security-relevant configuration changes

## Infrastructure Security

- Amazon RDS PostgreSQL must not be publicly accessible.
- Security groups must allow only required traffic paths between components.
- Private runtimes that call AWS control-plane services must have an explicit private network path when no NAT Gateway is present.
- IAM policies must follow least privilege for Lambda, Terraform execution, and any automation roles.
- API access must be exposed only through HTTPS endpoints.
- Infrastructure must be managed through Terraform to reduce drift and make security-relevant changes reviewable.
- Cloud misconfiguration is treated as a primary risk area for this project.

## CI/CD Security Checks

- Use `pre-commit` to run baseline checks before code is committed.
- Run secret scanning to prevent accidental credential leakage.
- Run `bandit` for Python security linting.
- Run dependency scanning to detect known vulnerable packages.
- Run `checkov` or `tfsec` against Terraform before deployment.
- Fail the pipeline on high-confidence secret leaks or critical IaC misconfigurations.

## Data Protection

- Enable encryption at rest for RDS and for managed secret storage.
- Use TLS for service-to-service and client-to-service communication where supported.
- Expose the API only over HTTPS through API Gateway.
- Minimize stored sensitive data to what the MVP actually needs.
- Avoid copying production data into unsecured local or test environments.

## Incident Handling (MVP)

If a security issue is suspected:

1. Contain the issue by disabling affected access paths, credentials, or workflows.
2. Review CloudWatch logs, audit records, and recent infrastructure or application changes.
3. Rotate potentially exposed secrets or tokens.
4. Fix the root cause and deploy through the normal reviewed workflow.
5. Document the incident briefly, including impact, timeline, and follow-up actions.

The MVP does not require a full incident management platform, but it does require a repeatable response process.

## Future Improvements

- PostgreSQL Row Level Security for defense-in-depth tenant enforcement
- Cognito MFA rollout for higher-risk roles
- Backup and restore validation for RDS
- Lightweight alerting for suspicious login or API abuse patterns
- Periodic dependency and IAM permission review

## Security Responsibility

Security in LeaseFlow is shared across three layers:

- **Application**: authentication, authorization, tenant isolation, secure coding, and audit events
- **Infrastructure**: private networking, encryption, IAM boundaries, and Terraform-managed configuration
- **Workflow**: code review, CI security checks, dependency maintenance, and secret handling discipline

This shared-responsibility approach is intentionally lightweight, but it is sufficient to demonstrate serious security thinking for an MVP architecture portfolio project.
