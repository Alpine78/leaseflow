# Notification Suppression And Unsubscribe Model Plan

## Purpose

This document defines the future tenant/contact-level suppression and
preference model for LeaseFlow notification email.

This is a planning artifact only. It does not add database migrations, backend
code, frontend UI, Terraform resources, SES integration changes, production
access, or marketing email behavior.

## Current State

- `notification_contacts.enabled` is the current tenant-managed recipient
  on/off state.
- Disabled contacts remain stored and are excluded from delivery candidate
  selection.
- `notification_email_deliveries` tracks delivery attempts, sanitized failure
  codes, and sent timestamps.
- Bounce and complaint ingestion is planned separately in
  `docs/ses-bounce-complaint-ingestion.md`.
- No LeaseFlow-owned suppression or unsubscribe/preference state exists yet.
- The browser can manage contacts but cannot trigger reminder scans, delivery,
  retries, or provider feedback processing.

## Message Classification

Due reminder email is classified as operational tenant notification mail for
the first production-ready delivery path.

Due reminder delivery should be controlled by the LeaseFlow tenant-owned contact
model:

- tenant users can enable or disable a contact.
- provider feedback can suppress a contact after permanent bounce or complaint.
- optional unsubscribe/list-topic behavior is not required for the first due
  reminder path.

Marketing mail, digest mail, optional newsletters, and broad promotional
messages are out of scope. If those message types are added later, they need an
explicit preference/unsubscribe design before delivery is enabled.

## Future Contact State Model

The future model should distinguish these states:

- `enabled`: tenant-managed contact is eligible if no suppression/preference
  block applies.
- `disabled`: tenant-managed contact opt-out; delivery must not select the
  contact.
- `suppressed_bounce`: system-managed block after permanent bounce or
  provider suppression bounce.
- `suppressed_complaint`: system-managed block after complaint feedback.
- future `unsubscribed`: reserved for optional, digest, or marketing-like
  notification types; not required for the first due reminder path.

Delivery eligibility requires both:

- the contact is enabled.
- no suppression or preference state blocks the message type.

Suppression must be tenant-scoped in LeaseFlow even if SES account-level
suppression is also enabled later. SES account-level suppression can protect
sender reputation, but it is not a replacement for application-owned
tenant/contact state.

## State Priority

When multiple states apply, delivery must choose the safest outcome:

- `disabled`, `suppressed_bounce`, `suppressed_complaint`, or future
  `unsubscribed` blocks delivery.
- Re-enabling a contact should not automatically remove provider-derived
  suppression.
- Removing provider-derived suppression must be an explicit future operator or
  tenant-safe workflow with auditability.
- Complaint suppression should be treated as stronger than ordinary disabled
  state because it represents recipient/provider feedback.

## SES Subscription Management

Amazon SES subscription management is not the first source of truth for
LeaseFlow due reminder delivery.

The first source of truth remains the LeaseFlow-owned tenant contact model
because:

- current delivery uses the SES SMTP path.
- due reminders are operational tenant notifications.
- tenant isolation and browser visibility must remain LeaseFlow-controlled.
- optional/digest/marketing message types do not exist yet.

SES contact list/topic subscription management may be evaluated later for
optional email types. That evaluation must be a separate ticket and must decide
how SES-managed preferences sync with LeaseFlow tenant/contact state.

## Browser And Tenant Boundaries

- Browser users may manage notification contacts.
- Browser users must not trigger delivery, retries, reminder scans, or
  provider feedback ingestion.
- Browser UI may later show safe contact status such as enabled, disabled, or
  suppressed.
- Browser UI must not show raw SES payloads, raw provider identifiers, SMTP
  transcripts, notification message bodies, tenant IDs, or recipient-level
  provider diagnostics.
- Tenant context must remain backend-derived from validated Cognito JWT claims
  or internal processing context, never browser request bodies.

## Follow-Up Tickets

### Add Notification Suppression State

Add DB and data-access support for tenant-scoped suppression/preference state.
Out of scope: SES event ingestion and browser UI.

### Apply Suppression To Email Delivery Eligibility

Update delivery preparation and sending selection so disabled or suppressed
contacts are excluded before delivery rows are created or sent.

### Add Suppression Visibility In Notifications UI

Expose safe contact status in the existing notifications/contact UI. Do not
show provider payloads, raw event data, tenant IDs, or recipient-level provider
diagnostics.

### Evaluate SES Subscription Management For Optional Email Types

Evaluate SES contact list/topic subscription management only if LeaseFlow adds
optional, digest, or marketing-like message types.

## Security And Cost Boundaries

- No Cognito user enumeration.
- No NAT Gateway is part of this plan.
- RDS must remain private.
- No browser-triggered delivery, scan, retry, or provider event processing.
- No production readiness claim is made.
- No raw SES event payloads, real email addresses, tenant IDs, message bodies,
  SMTP credentials, SES credentials, SSM values, DB endpoints, or provider
  responses should be stored in docs, logs, evidence, or audit metadata.

## References

- [Amazon SES subscription management](https://docs.aws.amazon.com/ses/latest/dg/sending-email-subscription-management.html)
- [Amazon SES global suppression list](https://docs.aws.amazon.com/ses/latest/dg/sending-email-global-suppression-list.html)
- [Amazon SES account-level suppression list](https://docs.aws.amazon.com/ses/latest/DeveloperGuide/sending-email-suppression-list.html)
- [Amazon SES event publishing](https://docs.aws.amazon.com/ses/latest/dg/monitor-using-event-publishing.html)
