# Notification Subscription Preference Evaluation

## Purpose

This document evaluates whether to add a per-type subscription or preference
model for notification contacts now, or defer until a concrete optional
notification type is scoped. The evaluation covers three design options with a
recommendation.

This is a design decision document only. No implementation, schema migration, or
API change is part of this ticket.

Related planning document: `docs/notification-suppression-unsubscribe-model.md`

## Current State

The notification contact model has two independent layers:

- `notification_contacts.enabled` — tenant-managed binary on/off for a contact.
  A disabled contact is excluded from all delivery candidate selection.
- `notification_contact_suppressions` — system-managed bounce and complaint
  suppressions derived from provider feedback. Independent of the `enabled` flag.

The only notification type in the system is `rent_due_soon`. Due reminders are
classified as operational tenant notification mail, not optional, digest-style,
or marketing mail.

There is no current use case where a contact should receive some notification
types but not others, because only one type exists and it is not optional.

## Design Options Evaluated

### Option A — Defer Until A Concrete Optional Type Is Needed

No preference table, no type-scoped flags. The existing `enabled` flag covers
the full opt-out case. When a concrete optional notification type (e.g., monthly
summary, lease renewal alert) is scoped as a separate ticket, that ticket designs
the appropriate preference model for that type.

Dimensions:

- **Schema change**: none
- **Delivery eligibility query**: unchanged
- **API surface**: unchanged
- **Frontend work**: none
- **Operational risk**: low — no new state to reason about
- **Fit for current demand**: complete — there is no current demand for per-type
  preference management

### Option B — Contact-Level Type Flags

Add one boolean column to `notification_contacts` per notification type (e.g.,
`reminders_enabled BOOLEAN NOT NULL DEFAULT TRUE`). Delivery eligibility checks
the relevant column for the notification type being prepared.

Dimensions:

- **Schema change**: migration required per new type; column list grows with
  each new type
- **Delivery eligibility query**: adds a type-specific column condition per
  delivery preparation call
- **API surface**: update and read endpoints must expose type-level flags
- **Frontend work**: per-type toggle UI or at minimum API representation
- **Operational risk**: medium — the schema encodes the type list, requiring a
  migration for each new type
- **Fit for current demand**: low — a `reminders_enabled` flag with no other
  type to compare it to adds complexity without value

### Option C — Preference Table

Add a separate `notification_contact_preferences` table, for example:

```sql
CREATE TABLE notification_contact_preferences (
    preference_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       TEXT NOT NULL,
    contact_id      UUID NOT NULL,
    notification_type TEXT NOT NULL,
    unsubscribed_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, contact_id, notification_type),
    FOREIGN KEY (tenant_id, contact_id) REFERENCES notification_contacts (tenant_id, contact_id)
);
```

Delivery eligibility adds a NOT EXISTS subquery checking for an active
unsubscribed preference row for the notification type being prepared.

Dimensions:

- **Schema change**: new table, indexes, FK, migration; delivery eligibility
  query adds a subquery
- **Delivery eligibility query**: more complex; requires join or NOT EXISTS per
  notification type
- **API surface**: CRUD endpoints for preference rows; list contacts must include
  preference state
- **Frontend work**: preference management UI or at minimum read exposure
- **Operational risk**: medium-high — preference table adds state interactions
  with enabled/suppressed states that must be tested and documented
- **Fit for current demand**: low — a flexible per-type table provides no value
  when only one non-optional type exists

## Recommendation

**Option A — Defer.**

The case for a preference model rests on having at least one optional
notification type. That condition is not met:

- `rent_due_soon` is operational mail that all tenants receive. A contact that
  does not want due reminders should be disabled (or the tenant should not add
  it). There is no meaningful partial opt-out.
- The `enabled` flag already covers "no notifications from this contact." Option
  B or C would add complexity that duplicates what `enabled` already does for
  the only existing type.
- The right schema depends on what the optional type looks like. A "monthly
  portfolio summary" with a digest cadence requires different state and delivery
  semantics than a "lease renewal alert." Designing the schema before the use
  case exists risks building the wrong abstraction.
- When an optional type is eventually scoped, its implementation ticket can
  choose between Option B (simple flag for a small fixed set) and Option C
  (table for a dynamic or large type set) based on actual requirements at that
  time.

## Constraints That Must Apply When A Model Is Eventually Added

These constraints apply regardless of which option is chosen at that time:

- No raw SES unsubscribe event data, SES list IDs, SES topic ARNs, or
  provider-issued subscription identifiers in the LeaseFlow data model or API
  responses.
- No Cognito user enumeration. Preferences must be scoped to
  `notification_contacts`, not to Cognito user identities.
- Unsubscribed or type-preference state must not automatically remove
  provider-derived suppression. Bounce and complaint suppression are independent
  system-managed states; clearing them requires a separate explicit workflow.
- Browser UI may read and write preferences for managed contacts but must not
  trigger delivery, retries, reminder scans, or provider feedback ingestion.
- Each new notification type must be explicitly classified as transactional or
  optional before production delivery is enabled for that type. Optional types
  require unsubscribe behavior before broad sending.
- Preference state priority must be documented: a contact blocked by
  `enabled=false` or an active suppression must not receive mail regardless of
  preference state.

## Trigger Conditions For Revisiting This Decision

This decision should be revisited when any of the following conditions are met:

- A concrete optional or periodic notification type (e.g., monthly portfolio
  summary, lease renewal reminder distinct from due reminder) is scoped in a
  follow-up ticket.
- SES subscription management headers, RFC 8058 one-click unsubscribe, or
  list-management compliance is required for a future notification type.
- A tenant explicitly requests the ability to receive some notification types
  but not others, providing a concrete preference model requirement.

## References

- [Amazon SES subscription management](https://docs.aws.amazon.com/ses/latest/dg/sending-email-subscription-management.html)
- [Amazon SES contact list management](https://docs.aws.amazon.com/ses/latest/dg/sending-email-list-management.html)
- [RFC 8058 — one-click unsubscribe](https://datatracker.ietf.org/doc/html/rfc8058)
