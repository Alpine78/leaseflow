# SES Bounce And Complaint Ingestion Plan

## Purpose

This document defines the future production path for ingesting Amazon SES
bounce and complaint events for LeaseFlow notification email.

This is a planning artifact only. It does not create AWS resources, Terraform
configuration, backend handlers, frontend behavior, DNS records, SES production
access, or email-sending changes.

## Current State

- Dev SES SMTP delivery exists as a disabled-by-default internal backend
  worker.
- Tenant-scoped `notification_email_deliveries` rows track send attempts,
  sanitized failure codes, and sent timestamps.
- The browser can manage notification contacts and read safe aggregate delivery
  status, but cannot trigger scans, delivery, retries, or provider event
  processing.
- Bounce and complaint event ingestion does not exist yet.
- SES accepting an SMTP message is not proof that the recipient accepted or
  retained the message.

## Event Destination Options

### EventBridge

EventBridge is the chosen default for future LeaseFlow bounce and complaint
ingestion.

SES event publishing supports configuration set event destinations. A future
SES configuration set should publish only the required `BOUNCE` and
`COMPLAINT` events to EventBridge. An EventBridge rule can then route matching
events to a future internal backend processor without exposing any browser
control path.

This fits the current LeaseFlow direction: internal jobs use AWS events, browser
routes remain tenant-scoped read/write flows, and production processing can be
expanded later with separate rules, retries, monitoring, or dead-letter design.

### SNS

SNS is an acceptable fallback because SES supports SNS event destinations and
SNS is a common bounce/complaint notification path.

It is not the default for LeaseFlow because backend state updates would still
need an additional subscription target and routing design. SNS may be revisited
if the implementation needs direct fan-out to multiple subscribers.

### CloudWatch And Firehose

CloudWatch and Firehose can be useful for aggregate metrics, dashboards,
alarms, or long-term analytics.

They are not the primary state-update path for tenant/contact suppression
because LeaseFlow needs controlled backend processing that updates tenant-owned
data without storing raw provider payloads by default.

## Target Architecture

Future implementation should use:

- SES configuration set with an EventBridge event destination.
- Matching event types limited to `BOUNCE` and `COMPLAINT`.
- EventBridge rule that targets an internal backend processor.
- Backend processor that maps provider events to sanitized categories and
  tenant/contact-scoped state changes.
- Delivery-row updates for the matching notification/contact relationship when
  that relationship can be safely resolved.
- Suppression/preference state updates for permanent bounces and complaints.

`DELIVERY_DELAY`, `REJECT`, or other SES event types should be added only by a
separate decision because they have different operational meaning and retry
behavior.

## Data Handling Rules

Persist only sanitized, application-owned state:

- event category such as bounce or complaint
- non-sensitive reason category or failure code
- aggregate-safe timestamps
- relationship to existing tenant-scoped notification/contact/delivery rows
- suppression or preference state when modeled

Do not store raw SES event payloads by default. If raw payload storage is ever
needed, it requires a separate privacy, retention, and access-control decision.

Do not log or commit recipient emails, tenant IDs, message bodies, MIME content,
SMTP transcripts, raw SES responses, credentials, SSM values, DB endpoints, or
provider-generated identifiers that are not necessary for safe debugging.

## Tenant And Browser Boundaries

- Tenant context must remain backend-derived from existing LeaseFlow data and
  validated internal processing context, not from browser request bodies.
- Browser users must not trigger delivery, retries, reminder scans, or
  bounce/complaint ingestion.
- Browser UI may later show safe aggregate delivery or suppression status, but
  not raw provider data or recipient-level provider details.
- Processing must not weaken existing application-layer tenant isolation.

## Follow-Up Tickets

### Add SES Configuration Set EventBridge Destination

Add Terraform for an SES configuration set and EventBridge event destination
for `BOUNCE` and `COMPLAINT` only. Include least-privilege EventBridge routing.
Out of scope: backend event processing.

### Implement SES Bounce And Complaint Processor

Add an internal backend event handler that parses SES events into sanitized
categories and updates tenant/contact-scoped state. Include unit and integration
tests for tenant isolation and no raw payload persistence.

### Add Notification Suppression State

Add tenant-scoped suppression/preference state for permanent bounces,
complaints, disabled contacts, and future unsubscribe decisions. Out of scope:
Cognito user enumeration and marketing email.

### Add Bounce Complaint Monitoring And Evidence

Add aggregate metrics, alarms, runbook steps, and sanitized evidence templates
for bounce/complaint ingestion validation.

## Security And Cost Boundaries

- No NAT Gateway is part of this plan.
- RDS must remain private.
- No browser-triggered scan, retry, delivery, or ingestion action is introduced.
- No raw SES payload storage is selected by default.
- No production readiness claim is made until implementation, monitoring, and
  sanitized evidence exist.
- Future AWS resources must be justified as production-delivery hardening and
  remain least-privilege.

## References

- [Amazon SES event publishing](https://docs.aws.amazon.com/ses/latest/dg/monitor-using-event-publishing.html)
- [Setting up Amazon SES event publishing](https://docs.aws.amazon.com/ses/latest/dg/monitor-sending-using-event-publishing-setup.html)
- [Amazon SES EventBridge event destination](https://docs.aws.amazon.com/ses/latest/dg/event-publishing-add-event-destination-eventbridge.html)
- [Amazon SES SNS event destination](https://docs.aws.amazon.com/ses/latest/dg/event-publishing-add-event-destination-sns.html)
- [Amazon SES event destination types](https://docs.aws.amazon.com/ses/latest/APIReference-V2/API_EventDestination.html)
