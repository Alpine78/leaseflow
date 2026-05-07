# SES Delivery Monitoring, Alarms, And Cost Controls Plan

## Purpose

This document defines the future monitoring, alarm, and cost-control direction
for LeaseFlow SES notification delivery.

This is a planning document only. It does not add Terraform alarms, CloudWatch
dashboards, backend metrics, AWS Budgets, SES production readiness, or cost
automation.

## Current State

- Baseline CloudWatch alarms already cover backend Lambda errors and throttles,
  API Gateway 5xx responses, and reminder scheduler target errors.
- The SES SMTP delivery worker exists, is internal-only, and remains disabled
  by default.
- Dev SES SMTP delivery has sanitized smoke evidence, but this does not prove
  production monitoring or production email readiness.
- SES bounce/complaint ingestion is planned in
  `docs/ses-bounce-complaint-ingestion.md`, not implemented.
- Notification suppression and unsubscribe/preference handling is planned in
  `docs/notification-suppression-unsubscribe-model.md`, not implemented.
- Production rollout hardening is planned in
  `docs/ses-production-delivery-hardening.md`.
- No SES delivery-specific custom metrics, delivery alarms, delivery dashboard,
  or AWS Budgets resources exist yet.

## Future Application Metrics

LeaseFlow-specific delivery visibility should use CloudWatch custom metrics
emitted from backend logs in an Embedded Metric Format style. These metrics
should be aggregate operational counters, not recipient- or tenant-identifying
records.

Allowed low-cardinality dimensions:

- environment
- service or component
- operation
- sanitized result category

Forbidden metric dimensions:

- recipient email
- tenant ID
- contact ID
- notification ID
- lease ID or property ID
- message body or notification content
- request ID or other high-cardinality per-run identifiers

The delivery worker should eventually emit these aggregate counters:

- `candidate_count`
- `created_delivery_count`
- `attempted_count`
- `sent_count`
- `failed_count`
- `skipped_count`
- `retry_exhausted_count`

The future bounce/complaint processor should emit these aggregate counters:

- `bounce_count`
- `complaint_count`
- `suppressed_contact_count`

Send-volume metrics should track total attempted and sent counts per worker run
and per alarm period. They must not expose tenant or recipient values.

SES native CloudWatch and reputation metrics should supplement these
application metrics once production access and a production sending identity are
ready. SES native metrics are useful for account or identity reputation signals,
but they do not replace LeaseFlow worker-specific counters.

## Future Alarm Boundaries

Alarm thresholds below are planning targets, not implemented resources.

Delivery health alarms:

- delivery worker invocation or processing error count greater than zero
- sustained `failed_count` greater than zero
- `retry_exhausted_count` greater than zero
- sudden drop to zero sends when candidates and enabled contacts exist

Provider feedback review alarms:

- `bounce_count` greater than zero in production
- `complaint_count` greater than zero in production
- SES native reputation, bounce-rate, or complaint-rate signal enters warning
  territory after production sender identity is enabled

Volume and safety alarms:

- attempted or sent volume exceeds the expected dev envelope
- attempted or sent volume exceeds the expected production envelope
- send volume changes sharply compared with a recent baseline

Alarms must use aggregate counts and sanitized categories only. Alarm names,
descriptions, dimensions, and notifications must not contain recipient data,
tenant IDs, contact IDs, notification IDs, message bodies, raw provider
responses, SMTP credentials, or SSM values.

## Cost Controls

Delivery must remain disabled by default until the operator intentionally
enables it for a controlled environment.

The SES SMTP interface VPC endpoint should remain disabled by default in dev.
When enabled for smoke testing or long-lived environments, the cost owner must
track:

- whether the endpoint is still required
- provisioned endpoint hours
- `BytesProcessed`
- `NewConnections`
- `ActiveConnections`

Future paid or long-lived environments should use AWS Budgets or an equivalent
cost alert path for:

- total account or environment spend
- unexpected SES sending volume
- long-lived interface endpoint cost exposure
- unusually high CloudWatch Logs or custom metric usage

Do not add NAT Gateway by default for email delivery. Any future proposal to
use NAT for SES access must justify cost, security, and operational tradeoffs
against the existing private SES SMTP endpoint direction.

## Follow-Up Tickets

### Emit SES Delivery CloudWatch Custom Metrics

Add backend aggregate EMF-style metrics for the delivery worker and future
bounce/complaint processor. Out of scope: recipient-level dimensions, tenant
dimensions, Terraform alarms, or dashboard resources.

### Add SES Delivery CloudWatch Alarms

Add Terraform alarms for delivery failures, retry exhaustion, bounce/complaint
signals, and send-volume anomaly boundaries. Out of scope: browser controls,
recipient-level alarm data, or production-readiness claims.

### Add SES Delivery Dashboard

Add a CloudWatch dashboard for aggregate delivery health. The dashboard must not
include recipient, tenant, contact, notification, or message-content details.

### Add SES And PrivateLink Cost Controls

Add AWS Budgets or equivalent cost-alert resources and an endpoint-cost review
path for paid or long-lived environments. Out of scope: automatic destructive
cost actions.

### Capture SES Monitoring Sanitized Evidence

Add a runbook and evidence template proving metrics and alarms without
recipient details, tenant IDs, raw provider payloads, or sensitive operational
values.

## Security And Evidence Boundaries

- Browser UI must not trigger scan, delivery, retry, or provider feedback
  processing.
- Tenant context remains backend-derived from validated Cognito JWT claims.
- Monitoring must not make RDS public.
- Monitoring must not introduce NAT Gateway by default.
- Logs, metrics, alarms, dashboards, and evidence must not contain real
  recipient emails, tenant IDs, JWTs, authorization headers, SMTP credentials,
  SES credentials, SSM values, DB endpoints, message bodies, raw SES responses,
  or raw SMTP transcripts.

## References

- [CloudWatch Embedded Metric Format](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Embedded_Metric_Format.html)
- [CloudWatch Embedded Metric Format specification](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Embedded_Metric_Format_Specification.html)
- [Amazon SES event publishing](https://docs.aws.amazon.com/ses/latest/dg/monitor-using-event-publishing.html)
- [Amazon SES sender reputation monitoring](https://docs.aws.amazon.com/ses/latest/DeveloperGuide/monitor-sender-reputation.html)
- [AWS PrivateLink CloudWatch metrics](https://docs.aws.amazon.com/vpc/latest/privatelink/privatelink-cloudwatch-metrics.html)
- [AWS Budgets](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html)
