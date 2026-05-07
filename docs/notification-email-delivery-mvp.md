# Notification Email Delivery MVP

## Purpose

This document defines the notification email delivery direction after the
persisted notification UI. The goal is to add production-like email delivery
without weakening tenant isolation, exposing internal jobs to the browser, or
adding uncontrolled AWS cost.

Email delivery now exists as a disabled-by-default internal backend worker. It
is not a browser feature, automatic schedule, production mail setup, or proof of
SES deliverability.

## Current State

- The internal due reminder scan creates tenant-owned `notifications` rows.
- Notification creation is idempotent through the existing
  `tenant_id`, `lease_id`, `type`, and `due_date` uniqueness constraint.
- The browser frontend can list notifications, mark them read, and view safe
  aggregate email delivery status per notification.
- The browser frontend can manage tenant-owned notification contacts.
- The browser cannot create notifications, run the reminder scan, or trigger
  external delivery.
- Tenant-scoped notification contacts are the recipient source.
- A dev SES infrastructure foundation exists with an optional sender identity
  and opt-in SES SMTP VPC endpoint.
- A tenant-scoped `notification_email_deliveries` table tracks delivery status,
  attempts, sanitized failure codes, and sent timestamps.
- `GET /notifications` includes delivery summary counts and sanitized status
  fields, but never recipient addresses, contact IDs, tenant IDs, or raw
  provider responses.
- The backend has an internal `deliver_notification_emails` event handler that
  can send due reminder notifications through SES SMTP when explicitly enabled.
- SMTP credentials are operator-created outside Terraform and referenced by SSM
  SecureString parameter names. Terraform does not create or output SMTP
  credential values.
- Dev smoke validation is documented in
  `docs/runbooks/ses-notification-email-delivery-smoke-test.md`, with sanitized
  successful evidence in
  `docs/runbooks/evidence/ses-notification-email-delivery-smoke-test-2026-05-05.md`.
  This validates the dev SMTP path only; it is not production email readiness.

## Chosen Direction

- Amazon SES is the preferred email delivery service for LeaseFlow.
- Production delivery hardening is planned separately in
  `docs/ses-production-delivery-hardening.md`.
- Production sender identity and DNS authentication planning is documented in
  `docs/ses-production-domain-identity-dns-authentication.md`; production
  sending remains unavailable.
- Persisted `notifications` remain the source of delivery work; the delivery
  job must not recalculate reminder candidates independently.
- Recipient addresses come from a LeaseFlow-owned tenant-scoped contact
  model, not from Cognito user enumeration.
- Email delivery remains a backend/internal workflow. No browser route should
  trigger scan or delivery execution.
- The first MVP should support due reminder notification email only. Marketing
  mail, billing mail, digest preferences, unsubscribe management, and external
  notification providers are out of scope for the first delivery slice.

## Data Model

The recipient model is `notification_contacts`:

- `tenant_id`
- contact identifier
- email address
- enabled/disabled state
- creation timestamp

Disabled contacts remain stored but must be excluded from delivery candidate
selection.

Delivery tracking is stored in `notification_email_deliveries` and supports:

- notification relationship
- tenant scope
- recipient relationship
- delivery status
- attempt count
- last attempt timestamp
- sent timestamp
- non-sensitive failure category or code

Do not store SES raw responses, SMTP transcripts, recipient email addresses,
message bodies, or secrets in delivery rows.

## Delivery Flow

The implemented backend flow is:

1. EventBridge Scheduler invokes the internal due reminder scan.
2. The scan creates missing persisted due reminder `notifications` rows.
3. An operator or future internal automation invokes the backend-only
   `deliver_notification_emails` event.
4. The delivery worker creates missing delivery rows for enabled contacts.
5. The worker selects unsent eligible notification/contact pairs.
6. The worker sends email through SES SMTP when delivery is enabled.
7. The worker records delivery success or a sanitized failure category.

Delivery must be idempotent and retry-safe:

- rerunning scan must not duplicate notification rows.
- rerunning delivery must not send duplicate email for the same
  notification/contact pair after success.
- failed attempts may be retried with a bounded attempt limit.
- read acknowledgement in the browser must not be treated as proof that email
  was delivered.
- browser-visible delivery status is read-only and must not trigger retries,
  scans, or delivery execution.
- exactly-once external SMTP delivery cannot be guaranteed if Lambda crashes
  after SES accepts a message but before `sent_at` is persisted.

## Infrastructure And Cost Boundaries

- Do not add a NAT Gateway by default.
- The current backend Lambda runs in private subnets. SES delivery therefore
  needs an explicit private connectivity design before implementation.
- The preferred private path is an SES SMTP interface VPC endpoint. Terraform
  includes this endpoint as disabled-by-default dev infrastructure so it does
  not create idle endpoint cost before delivery code exists.
- If a future implementation chooses a different SES access path, the PR must
  justify the network, security, and cost tradeoff explicitly.
- SES requires verified sending identities. In the SES sandbox, recipient
  restrictions also apply unless using supported simulator addresses.
- Sending limits, sandbox removal, bounce/complaint handling, and domain
  verification are rollout concerns, not browser features.
- SMTP credentials are operator-provided through SSM SecureString parameter
  names. Terraform grants Lambda read/decrypt access only to the configured
  parameter ARNs.
- Delivery remains disabled by default until SES identity, sandbox restrictions,
  SMTP credentials, endpoint connectivity, and smoke validation are ready.

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

- Add notification recipient contact model. Completed.
- Add tenant notification contact management API/UI. Completed.
- Add SES dev infrastructure foundation. Completed as disabled-by-default
  Terraform foundation.
- Implement idempotent notification email delivery. Completed as a
  disabled-by-default internal backend worker.
- Expose safe notification email delivery status. Completed as read-only
  aggregate status on persisted notifications.
- Add SES delivery smoke runbook and sanitized evidence. Runbook added;
- Add production-ready SES delivery hardening. Planned separately in
  `docs/ses-production-delivery-hardening.md`.

## References

- [Amazon SES verified identities](https://docs.aws.amazon.com/ses/latest/dg/verify-addresses-and-domains.html)
- [Amazon SES production access](https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html)
- [Amazon SES VPC endpoints](https://docs.aws.amazon.com/ses/latest/dg/send-email-set-up-vpc-endpoints.html)
