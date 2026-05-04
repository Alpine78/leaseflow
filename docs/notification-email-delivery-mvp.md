# Notification Email Delivery MVP

## Purpose

This document defines the next notification phase after the current persisted
notification UI. The goal is to add production-like email delivery later without
weakening tenant isolation, exposing internal jobs to the browser, or adding
uncontrolled AWS cost.

This is a planning document only. Email delivery is not implemented in the
current MVP.

## Current State

- The internal due reminder scan creates tenant-owned `notifications` rows.
- Notification creation is idempotent through the existing
  `tenant_id`, `lease_id`, `type`, and `due_date` uniqueness constraint.
- The browser frontend can list notifications and mark them read.
- The browser cannot create notifications, run the reminder scan, or trigger
  external delivery.
- A tenant-scoped notification contact model exists as the future recipient
  source.
- There is no email delivery status, SES infrastructure, or email-sending code
  yet.

## Chosen Direction

- Amazon SES is the preferred future email delivery service for LeaseFlow.
- Persisted `notifications` remain the source of delivery work; the delivery
  job must not recalculate reminder candidates independently.
- Recipient addresses will come from a LeaseFlow-owned tenant-scoped contact
  model, not from Cognito user enumeration.
- Email delivery remains a backend/internal workflow. No browser route should
  trigger scan or delivery execution.
- The first MVP should support due reminder notification email only. Marketing
  mail, billing mail, digest preferences, unsubscribe management, and external
  notification providers are out of scope for the first delivery slice.

## Future Data Model

The first implementation added a tenant-scoped notification contact model with:

- `tenant_id`
- contact identifier
- email address
- enabled/disabled state
- creation timestamp

Disabled contacts remain stored but must be excluded from delivery candidate
selection.

Future work should add delivery tracking for notification email attempts. This
can be a dedicated delivery table or explicit delivery columns, but it must
support:

- notification relationship
- tenant scope
- recipient relationship
- delivery status
- attempt count
- last attempt timestamp
- sent timestamp
- non-sensitive failure category or code

Do not store SES raw responses, SMTP transcripts, message bodies, or secrets in
delivery rows.

## Delivery Flow

The target flow for the later implementation is:

1. EventBridge Scheduler invokes the internal due reminder scan.
2. The scan creates missing persisted due reminder `notifications` rows.
3. A backend-only delivery worker selects unsent eligible notification/contact
   pairs.
4. The worker sends email through SES.
5. The worker records delivery success or a sanitized failure category.

Delivery must be idempotent and retry-safe:

- rerunning scan must not duplicate notification rows.
- rerunning delivery must not send duplicate email for the same
  notification/contact pair after success.
- failed attempts may be retried with a bounded attempt limit.
- read acknowledgement in the browser must not be treated as proof that email
  was delivered.

## Infrastructure And Cost Boundaries

- Do not add a NAT Gateway by default.
- The current backend Lambda runs in private subnets. SES delivery therefore
  needs an explicit private connectivity design before implementation.
- The preferred private path to evaluate first is an SES SMTP interface VPC
  endpoint with credentials stored outside the repository.
- If a future implementation chooses a different SES access path, the PR must
  justify the network, security, and cost tradeoff explicitly.
- SES requires verified sending identities. In the SES sandbox, recipient
  restrictions also apply unless using supported simulator addresses.
- Sending limits, sandbox removal, bounce/complaint handling, and domain
  verification are rollout concerns, not browser features.

## Security And Tenant Isolation

- Tenant context must remain backend-derived. Browser request bodies must never
  define delivery tenant context.
- Contact rows and delivery rows must be tenant-scoped.
- Cross-tenant reads or delivery updates must be rejected by tests.
- Do not log email addresses, notification message contents, tenant IDs,
  tokens, SMTP credentials, SES credentials, SSM values, DB endpoints, or raw
  provider responses.
- Logs should use request/job IDs, aggregate counts, sanitized status values,
  and non-sensitive failure categories.
- SES credentials or SMTP credentials must be stored in AWS-managed secret
  storage and accessed with least-privilege IAM.

## Follow-Up Implementation Tickets

The implementation should be split into separate reviewable tickets:

- Add notification recipient contact model.
- Add SES dev infrastructure foundation.
- Implement idempotent notification email delivery.
- Add SES delivery smoke runbook and sanitized evidence.

## References

- [Amazon SES verified identities](https://docs.aws.amazon.com/ses/latest/dg/verify-addresses-and-domains.html)
- [Amazon SES production access](https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html)
- [Amazon SES VPC endpoints](https://docs.aws.amazon.com/ses/latest/dg/send-email-set-up-vpc-endpoints.html)
