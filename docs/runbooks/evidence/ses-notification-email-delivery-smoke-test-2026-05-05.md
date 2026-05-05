# SES Notification Email Delivery Smoke Test Evidence - 2026-05-05

## Summary

Result:

- SES sender identity prerequisite: `pass`
- SES sandbox recipient requirement: `pass`
- SMTP credential SSM parameter type check: `pass`
- SMTP credential login probe: `pass`
- Dev delivery enablement: `pass`
- Contact setup invocation: `pass`
- Reminder scan invocation: `pass`
- First delivery invocation: `pass`
- Second idempotency invocation: `pass`
- Cleanup: `pass`

Full SES SMTP delivery smoke passed. The first delivery run sent one persisted
due notification email, and the second delivery run did not resend the sent
delivery.

## Context

- Date: `2026-05-05`
- Branch: `154-execute-ses-delivery-smoke-validation-and-capture-sanitized-evidence`
- Related issue: `#154 Execute SES Delivery Smoke Validation`
- Region: `eu-north-1`
- Runbook: `docs/runbooks/ses-notification-email-delivery-smoke-test.md`

## Preconditions

```text
SES sender identity verified:                  pass
SES sandbox recipient requirement satisfied:   pass
SES SMTP credential parameters are SecureString: pass
SMTP login with current credential values:     pass
SES SMTP VPC endpoint enabled for smoke:       pass
Notification email delivery enabled for smoke: pass
Deployed DB migrations current:                pass
Enabled contact prerequisite confirmed:        pass
```

No SMTP username, SMTP password, SSM value, email address, tenant ID, token, DB
endpoint, or raw provider response is captured here.

## Seed Data And Contact Setup

Seed script aggregate output:

```text
seed_reminder_scan_status_code:       200
seed_candidate_count:                 1
seed_notification_created_count:      1
seed_notification_duplicate_count:    0
seed_property_created_count:          2
seed_lease_created_count:             2
```

Contact setup aggregate output:

```text
contact_setup_status_code: 200
contact_configured:        true
contact_created:           true
contact_updated:           false
contact_enabled:           true
```

## Reminder Scan Results

Explicit reminder scan aggregate output:

```text
reminder_scan_status_code: 200
candidate_count:           1
created_count:             0
duplicate_count:           1
```

## First Delivery Run

Sanitized aggregate output:

```text
delivery_status_code: 200
enabled:              true
candidate_count:      1
created_count:        1
duplicate_count:      0
attempted_count:      1
sent_count:           1
failed_count:         0
```

Expected pass condition was:

```text
enabled=true, attempted_count>=1, sent_count>=1, failed_count=0
```

The condition was met.

## Second Delivery Run

Sanitized aggregate output:

```text
delivery_status_code: 200
enabled:              true
candidate_count:      1
created_count:        0
duplicate_count:      1
attempted_count:      0
sent_count:           0
failed_count:         0
```

Expected idempotency condition was:

```text
enabled=true, attempted_count=0, sent_count=0, failed_count=0
```

The condition was met.

## Cleanup

```text
local smoke temp cleanup:                  pass
notification email delivery disabled:      pass
SES SMTP VPC endpoint disabled if unused:  pass
```

## Evidence Hygiene

This evidence intentionally does not include:

- Recipient email addresses
- Cognito emails
- Tenant IDs
- JWTs or authorization headers
- SMTP or SES credentials
- SSM values
- DB endpoints or connection strings
- Notification titles or message bodies
- Raw SES responses
- Raw SMTP transcripts
- Screenshots with sensitive values
