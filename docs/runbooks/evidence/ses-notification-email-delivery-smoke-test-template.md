# SES Notification Email Delivery Smoke Test Evidence - YYYY-MM-DD

## Summary

This template is for sanitized evidence after manually running
`docs/runbooks/ses-notification-email-delivery-smoke-test.md`.

Result:

- SES sender identity prerequisite: `not run`
- SES sandbox recipient requirement: `not run`
- SMTP credential SSM parameter check: `not run`
- Dev delivery enablement: `not run`
- Reminder scan invocation: `not run`
- First delivery invocation: `not run`
- Second idempotency invocation: `not run`
- Cleanup: `not run`

Do not use this template itself as proof that smoke validation passed. Copy it
to a dated evidence file only after the operator-run smoke test is completed.

## Context

- Date: `YYYY-MM-DD`
- Branch: `146-add-ses-delivery-smoke-runbook-and-sanitized-evidence`
- Related issue: `#146 Add SES delivery smoke runbook and sanitized evidence`
- Region: `eu-north-1`
- Runbook: `docs/runbooks/ses-notification-email-delivery-smoke-test.md`

## Preconditions

```text
SES sender identity verified:                  not run
SES sandbox recipient requirement satisfied:   not run
SES SMTP credentials stored in SSM:            not run
SES SMTP VPC endpoint enabled for smoke:       not run
Notification email delivery enabled for smoke: not run
Deployed DB migrations current:                not run
Enabled contact prerequisite confirmed:        not run
```

Contact prerequisite note:

```text
The smoke tenant had an enabled notification contact before delivery was run.
No recipient email address, tenant ID, or contact ID is captured here.
```

## Reminder Scan Results

Sanitized aggregate output:

```text
reminder_scan_status_code:    not run
candidate_count:             not captured
created_count:               not captured
duplicate_count:             not captured
```

## First Delivery Run

Sanitized aggregate output:

```text
delivery_status_code: not run
enabled:              not captured
candidate_count:      not captured
created_count:        not captured
duplicate_count:      not captured
attempted_count:      not captured
sent_count:           not captured
failed_count:         not captured
```

Expected pass condition:

```text
enabled=true, attempted_count>=1, sent_count>=1, failed_count=0
```

## Second Delivery Run

Sanitized aggregate output:

```text
delivery_status_code: not run
enabled:              not captured
candidate_count:      not captured
created_count:        not captured
duplicate_count:      not captured
attempted_count:      not captured
sent_count:           not captured
failed_count:         not captured
```

Expected idempotency condition:

```text
enabled=true, attempted_count=0, sent_count=0, failed_count=0
```

## Cleanup

```text
local smoke temp cleanup:                  not run
delivery disabled after smoke:             not run
SES SMTP VPC endpoint disabled if unused:  not run
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

## Notes

- If first delivery `attempted_count` was `0`, this evidence must not claim
  successful SES delivery.
- If any delivery failed, capture only sanitized failure categories and create a
  follow-up issue. Do not paste raw SMTP or SES output.
