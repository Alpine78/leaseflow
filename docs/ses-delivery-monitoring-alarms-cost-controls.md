# SES Delivery Monitoring, Alarms, And Cost Controls Plan

## Purpose

This document defines the future monitoring, alarm, and cost-control direction
for LeaseFlow SES notification delivery.

This document records the current monitoring implementation and remaining
planning boundaries. It does not add SES production readiness or automatic cost
actions.

## Current State

- Baseline CloudWatch alarms already cover backend Lambda errors and throttles,
  API Gateway 5xx responses, and reminder scheduler target errors.
- The SES SMTP delivery worker exists, is internal-only, and remains disabled
  by default.
- Dev SES SMTP delivery has sanitized smoke evidence, but this does not prove
  production monitoring or production email readiness.
- SES bounce/complaint ingestion exists as a disabled-by-default internal
  backend processor and opt-in EventBridge routing.
- Notification suppression and unsubscribe/preference handling is planned in
  `docs/notification-suppression-unsubscribe-model.md`, not implemented.
- Production rollout hardening is planned in
  `docs/ses-production-delivery-hardening.md`.
- SES delivery worker custom metrics now exist for normal internal delivery
  runs.
- Terraform-managed dev alarms now cover delivery failures, retry exhaustion,
  and a conservative attempted-send volume boundary.
- A Terraform-managed dev CloudWatch dashboard now shows aggregate delivery
  worker health, send-volume, failure, and future feedback/suppression metric
  panels. Dashboard widgets can show no data until delivery is enabled and the
  relevant metrics are emitted.
- An optional Terraform-managed AWS monthly cost budget is available for paid
  or long-lived dev environments. It is disabled by default.

## Future Application Metrics

LeaseFlow-specific delivery visibility should use CloudWatch custom metrics
emitted from backend logs in an Embedded Metric Format style. These metrics
should be aggregate operational counters, not recipient- or tenant-identifying
records.

Implemented delivery worker metrics use the namespace
`LeaseFlow/NotificationEmailDelivery` and the dimension set `environment`,
`service`, `operation`, and `result`.

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

The delivery worker emits these aggregate counters:

- `candidate_count`
- `created_delivery_count`
- `attempted_count`
- `sent_count`
- `failed_count`
- `skipped_count`
- `retry_exhausted_count`

The bounce/complaint processor emits these aggregate counters:

- `bounce_count`
- `complaint_count`
- `suppressed_contact_count`

Send-volume metrics should track total attempted and sent counts per worker run
and per alarm period. They must not expose tenant or recipient values.

SES native CloudWatch and reputation metrics should supplement these
application metrics once production access and a production sending identity are
ready. SES native metrics are useful for account or identity reputation signals,
but they do not replace LeaseFlow worker-specific counters.

## Alarm Boundaries

Implemented dev delivery alarms use the `LeaseFlow/NotificationEmailDelivery`
namespace with the dimensions `environment`, `service`, `operation`, and
`result`.

Implemented delivery health alarms:

- `failed_count` greater than or equal to `1` for
  `result=completed_with_failures` over a five-minute period.
- `retry_exhausted_count` greater than or equal to `1` for
  `result=completed_with_failures` over a five-minute period.
- `attempted_count` greater than `100` by default for `result=completed` over a
  one-hour period as a dev send-volume boundary.

Remaining alarm thresholds below are planning targets, not implemented
resources.

Delivery health alarms:

- delivery worker invocation or processing error count greater than zero
- sudden drop to zero sends when candidates and enabled contacts exist

Provider feedback review alarms:

- `bounce_count` greater than or equal to `1` for
  `operation=process_ses_provider_feedback, result=processed` over a
  five-minute period. Implemented for dev.
- `complaint_count` greater than or equal to `1` for
  `operation=process_ses_provider_feedback, result=processed` over a
  five-minute period. Implemented for dev.
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

## Dashboard

The dev CloudWatch dashboard uses the same
`LeaseFlow/NotificationEmailDelivery` namespace and the low-cardinality
dimensions `environment`, `service`, `operation`, and `result`.

Implemented dashboard panels show:

- delivery run volume for candidates, created deliveries, attempted sends, sent
  sends, and skipped candidates
- failure health for failed sends and retry exhaustion
- worker result categories for completed, completed-with-failures, and disabled
  runs
- future feedback and suppression counts for bounces, complaints, and
  suppressed contacts

Future feedback and suppression widgets are intentionally present before those
metrics are emitted. They can render as no-data until EventBridge routing is
enabled and real SES feedback events are processed.

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

Paid or long-lived environments can enable the optional AWS monthly cost budget
to alert operators when actual account spend reaches the configured percentage
of the configured monthly USD amount.

The budget is intentionally coarse-grained. It tracks AWS account cost for the
environment account rather than tenant, recipient, contact, notification, or
provider-payload data.

The optional budget supports:

- disabled-by-default cost alerting for short-lived learning stacks
- a configurable monthly USD limit
- a configurable actual-spend percentage threshold
- operator email subscribers configured only in local ignored Terraform inputs

Future paid or long-lived environments should also use AWS Budgets or an
equivalent cost alert path for:

- total account or environment spend
- unexpected SES sending volume
- long-lived interface endpoint cost exposure
- unusually high CloudWatch Logs or custom metric usage

The dev CloudWatch dashboard adds the normal CloudWatch dashboard monthly cost
exposure for one dashboard. Keep dashboard count small and aggregate-only; do
not create tenant-, recipient-, contact-, notification-, or request-specific
dashboards.

The optional SES SMTP interface VPC endpoint remains the primary email-specific
cost exposure. If enabled, operators must review whether the endpoint is still
needed after each smoke or long-lived validation window.

Do not add NAT Gateway by default for email delivery. Any future proposal to
use NAT for SES access must justify cost, security, and operational tradeoffs
against the existing private SES SMTP endpoint direction.

## Follow-Up Tickets

### Emit SES Delivery CloudWatch Custom Metrics

Completed for the internal delivery worker. Bounce/complaint processor
metrics are also implemented as aggregate EMF-style counters. Recipient-level
dimensions, tenant dimensions, Terraform alarms, and dashboard resources remain
out of scope for metric emission.

### Add SES Delivery CloudWatch Alarms

Completed for dev delivery failures, retry exhaustion, and the attempted-send
volume boundary. Future work remains for bounce/complaint signals, production
reputation alarms, and any production-specific volume thresholds. Out of scope:
browser controls, recipient-level alarm data, or production-readiness claims.

### Add SES Delivery Dashboard

Completed for aggregate dev delivery health. Future dashboard expansion for
production reputation or bounce/complaint processor-specific views must remain
aggregate-only and avoid recipient, tenant, contact, notification, or
message-content details.

### Add SES And PrivateLink Cost Controls

Completed for an optional dev monthly AWS cost budget and documented SES SMTP
PrivateLink endpoint-cost review expectations. Future work can add more
specific budgets or reporting for paid/long-lived environments. Out of scope:
automatic destructive cost actions.

### Capture SES Monitoring Sanitized Evidence

Completed for delivery worker monitoring and bounce/complaint processor
monitoring. A delivery smoke-test runbook, a processor validation runbook, and
sanitized evidence files exist for both. Live AWS runtime validation remains
pending until the dev stack is available with a configured AWS CLI profile.

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
