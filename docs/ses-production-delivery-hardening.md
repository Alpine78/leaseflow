# SES Production Delivery Hardening Plan

## Purpose

This document defines the gap between the current dev SES SMTP notification
delivery MVP and a production-ready email delivery capability.

The current implementation proves that persisted due reminder notifications can
be delivered through an explicitly enabled dev SES SMTP path. It does not prove
production readiness, sender reputation readiness, compliance readiness, or
operational readiness.

No production access request, DNS change, AWS resource change, Terraform change,
backend code change, frontend change, or custom domain implementation is part of
this planning document.

## Current State

- Persisted due reminder notifications are stored in tenant-owned
  `notifications` rows.
- Tenant-owned `notification_contacts` rows define recipient contacts.
- Tenant-scoped `notification_email_deliveries` rows track delivery attempts,
  sanitized failure codes, and sent timestamps.
- The backend has an internal `deliver_notification_emails` event handler.
- Email delivery is disabled by default and cannot be triggered from the
  browser.
- The current private delivery path uses SES SMTP over an optional interface VPC
  endpoint.
- SMTP credentials are operator-created outside Terraform and referenced through
  SSM SecureString parameter names.
- The browser can view only safe aggregate delivery status through
  `GET /notifications`.
- Dev SES smoke validation evidence exists in
  `docs/runbooks/evidence/ses-notification-email-delivery-smoke-test-2026-05-05.md`.

## Production Readiness Requirements

### SES Account And Identity Readiness

Production delivery requires an explicit SES production access decision for the
target AWS Region. While an SES account is in sandbox mode, sending is limited
to verified recipients or the SES mailbox simulator, with low daily and
per-second quotas.

The production sender should use a verified domain identity rather than relying
only on one verified email address. Domain verification is the better long-term
fit because it supports sending from addresses under the domain without
verifying each address separately.

Required future decisions:

- The production sender identity direction is documented in
  `docs/ses-production-domain-identity-dns-authentication.md`.
- Whether LeaseFlow later adopts a custom MAIL FROM domain.
- Which AWS Region owns the production SES identity.
- Whether dev and production identities are isolated by account, region, or
  configuration.

### Email Authentication

Production sending needs DNS-based authentication before broad delivery:

- DKIM must be enabled for the sending domain.
- SPF alignment must be reviewed, especially if a custom MAIL FROM domain is
  used.
- DMARC must exist for the sending domain and start with a safe monitoring
  posture before any stricter policy is considered.

The first rollout should avoid claiming strong deliverability until DNS
authentication has been verified and monitored.

### Bounce, Complaint, And Suppression Handling

Production delivery cannot rely only on SMTP success. SES accepting a message is
not proof that the recipient received or accepted it.

Future production work must ingest bounce and complaint signals through SES
configuration sets. The planned default is an EventBridge event destination, as
documented in `docs/ses-bounce-complaint-ingestion.md`.

Handling requirements:

- Persist only sanitized event categories and aggregate-safe status fields.
- Do not store raw SES provider payloads unless a separate privacy and retention
  review justifies it.
- Do not log recipient emails, tenant IDs, SMTP transcripts, notification
  message bodies, or raw provider responses.
- Permanent bounces and complaints must suppress future sends to the affected
  contact.
- Suppression behavior must be tenant-scoped in the LeaseFlow data model even
  if SES also maintains account-level suppression.

### Unsubscribe And Message Classification

Due reminder emails are closer to transactional operational mail than marketing
mail, but production rollout still needs an explicit classification decision.

If any future notification type is promotional, digest-style, or optional, it
must include unsubscribe/list-management behavior before broad sending. The
LeaseFlow suppression and preference direction is documented in
`docs/notification-suppression-unsubscribe-model.md`.

Production requirements:

- Classify each email type before enabling production sending.
- Keep browser delivery controls read-only; users may manage contacts but must
  not trigger scans or delivery runs.
- Define how disabled contacts, suppressed contacts, and unsubscribed contacts
  interact.

### Retry And Idempotency

The current delivery table prevents duplicate sends after `sent_at` is
persisted. This remains required in production.

Future production retry behavior must add:

- Clear distinction between transient and permanent failures.
- Bounded retry attempts.
- Backoff or scheduled retry cadence.
- No automatic infinite retries.
- No retry of already sent delivery rows.
- Explicit documentation that exactly-once external SMTP delivery cannot be
  guaranteed if Lambda crashes after SES accepts a message but before the DB
  status update commits.

### Monitoring And Alarms

Production delivery needs CloudWatch-visible health signals before enabling
real recipients at scale.

Minimum monitoring topics:

- Delivery worker invocation success/failure.
- Candidate, attempted, sent, failed, and skipped counts.
- Bounce and complaint counts.
- Failure categories.
- Retry exhaustion.
- SES sending quota pressure.
- Unusual spikes in send volume.
- Optional SES SMTP VPC endpoint cost exposure when enabled.

Alarms must use aggregate counts and sanitized categories. They must not include
recipient addresses, tenant IDs, message bodies, raw SES responses, SMTP
credentials, or SSM values.

The focused monitoring, alarm, and cost-control direction is documented in
`docs/ses-delivery-monitoring-alarms-cost-controls.md`. Backend metric
emission, Terraform alarms, dashboards, and budget resources remain future work.

### Cost Controls

Delivery must stay disabled by default until production readiness is explicit.

Production hardening should include:

- Environment-level enablement flag.
- Batch size limits.
- Max attempt limits.
- Optional per-tenant or per-run send caps.
- Explicit review before enabling a billable interface endpoint for long-lived
  environments.
- CloudWatch alarms for unexpected send volume and endpoint cost exposure.

## Integration Path Decision

The near-term default remains SES SMTP over PrivateLink because the backend
Lambda runs in private subnets and the project avoids NAT Gateway by default.
This is consistent with the current cost-aware private networking direction.

SES API integration may be evaluated later, but it must be a separate ticket
with an explicit network, security, cost, and operational tradeoff. Do not add a
NAT Gateway only to reach SES APIs unless the PR proves that the cost and
security tradeoff is justified.

## Follow-Up Tickets

### Add SES Production Domain Identity And DNS Authentication Plan

Completed as a focused planning document in
`docs/ses-production-domain-identity-dns-authentication.md`. Implementation,
DNS changes, sending code, and production access submission remain out of
scope.

### Add SES Bounce And Complaint Ingestion

Planned in `docs/ses-bounce-complaint-ingestion.md` with EventBridge as the
default future event path. Terraform resources, backend processing, browser
triggering, and raw provider payload storage remain out of scope.

### Add Notification Suppression And Unsubscribe Model

Planned in `docs/notification-suppression-unsubscribe-model.md`. Database
state, delivery eligibility changes, browser visibility, SES subscription
automation, marketing mail, and Cognito user enumeration remain out of scope.

### Add SES Delivery Monitoring, Alarms, And Cost Controls

Planned in `docs/ses-delivery-monitoring-alarms-cost-controls.md`. Backend
metric emission, Terraform alarms, CloudWatch dashboards, budget resources, and
sanitized monitoring evidence remain out of scope.

### Add Production SES Rollout Runbook And Sanitized Evidence Template

Document the controlled production-readiness validation path with safe evidence
rules. Out of scope: actual production access request or real customer data.

### Evaluate SES API Integration Path For Production Delivery

Compare the current SMTP PrivateLink path with SES API options. The decision
must cover private networking, IAM, idempotency, error mapping, cost, and
operational complexity. Out of scope: changing the implementation inside the
planning ticket.

## Security Boundaries

- Tenant context remains backend-derived from validated Cognito JWT claims.
- Browser request bodies and query parameters must never define delivery tenant
  context.
- Browser UI may manage contacts and read safe aggregate status, but must not
  trigger scan, retry, or delivery jobs.
- Production hardening must not make RDS public.
- Production hardening must not introduce NAT Gateway by default.
- Production hardening must not log or commit real emails, tenant IDs, JWTs,
  SMTP credentials, SES credentials, SSM values, DB endpoints, notification
  bodies, raw SES responses, or raw SMTP transcripts.

## References

- [Amazon SES verified identities](https://docs.aws.amazon.com/ses/latest/dg/verify-addresses-and-domains.html)
- [Amazon SES production access](https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html)
- [Amazon SES VPC endpoints](https://docs.aws.amazon.com/ses/latest/dg/send-email-set-up-vpc-endpoints.html)
- [Amazon SES event publishing](https://docs.aws.amazon.com/ses/latest/dg/monitor-using-event-publishing.html)
- [Amazon SES configuration sets](https://docs.aws.amazon.com/ses/latest/dg/using-configuration-sets.html)
- [Amazon SES subscription management](https://docs.aws.amazon.com/ses/latest/dg/sending-email-subscription-management.html)
- [Amazon SES global suppression list](https://docs.aws.amazon.com/ses/latest/dg/sending-email-global-suppression-list.html)
- [Amazon SES Easy DKIM](https://docs.aws.amazon.com/ses/latest/dg/send-email-authentication-dkim-easy.html)
- [Amazon SES SPF authentication](https://docs.aws.amazon.com/ses/latest/dg/send-email-authentication-spf.html)
- [Amazon SES custom MAIL FROM](https://docs.aws.amazon.com/ses/latest/dg/mail-from.html)
- [Amazon SES DMARC](https://docs.aws.amazon.com/ses/latest/dg/send-email-authentication-dmarc.html)
- [CloudWatch Embedded Metric Format](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Embedded_Metric_Format.html)
- [AWS PrivateLink CloudWatch metrics](https://docs.aws.amazon.com/vpc/latest/privatelink/privatelink-cloudwatch-metrics.html)
- [AWS Budgets](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html)
