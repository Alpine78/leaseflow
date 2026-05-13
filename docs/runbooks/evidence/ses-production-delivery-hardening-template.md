# SES Production Delivery Hardening Evidence - YYYY-MM-DD

## Summary

This template is for sanitized evidence after manually running
`docs/runbooks/ses-production-delivery-hardening-runbook.md`.

Result:

- SES production access request submitted: `not run`
- Domain identity created in SES: `not run`
- DKIM DNS records propagated: `not run`
- SPF DNS record propagated: `not run`
- DMARC DNS record propagated: `not run`
- SES domain identity verification status: `not run`
- CloudWatch alarm review: `not run`
- SSM parameter type check: `not run`
- Production stack applied with delivery enabled: `not run`
- Pilot tenant precondition confirmed: `not run`
- Reminder scan invocation: `not run`
- First production delivery invocation: `not run`
- Second idempotency invocation: `not run`
- Cleanup: `not run`
- Go-live or deferred decision: `not run`

Do not use this template itself as proof that production validation passed. Copy
it to a dated evidence file only after the operator-run runbook is completed.

## Context

- Date: `YYYY-MM-DD`
- Branch: `<branch-name>`
- Related issue: `#217 Add production SES rollout runbook and sanitized evidence template`
- Region: `eu-north-1`
- Runbook: `docs/runbooks/ses-production-delivery-hardening-runbook.md`

## Preconditions

```text
Planning docs reviewed:                              not run
SES feedback processor deployed:                     not run
Suppression model deployed:                          not run
SES configuration set with EventBridge destination:  not run
Production stack running with current artifact:      not run
DB migrations current:                               not run
```

## SES Production Access Request

```text
AWS Support case submitted: not run
AWS approval received:      not run
```

Note: case number recorded locally only; not captured in evidence.

## Domain Identity And DNS Authentication

```text
Domain identity created in SES:     not run
SES domain identity status:         not captured
DKIM CNAME records (3) propagated:  not run
SPF TXT record propagated:          not run
DMARC TXT record propagated:        not run
```

DNS authentication note:

```text
DKIM token values, SPF record contents, DMARC tag values, and DMARC rua
addresses are not captured here.
```

## CloudWatch Alarms

```text
Alarm review completed:         not run
Bounce rate alarm deployed:     not captured
Complaint rate alarm deployed:  not captured
Failure alarm deployed:         not captured
All alarms in OK state:         not captured
```

## SSM Parameter Check

```text
SMTP username parameter type: not run
SMTP password parameter type: not run
```

Expected: both `SecureString`. No credential values captured.

## Pilot Tenant Precondition

```text
Pilot tenant has enabled contact:      not run
Contact has no active suppression:     not run
Tenant has due-soon reminder data:     not run
```

Note: no recipient email, tenant ID, or contact ID is captured here.

## Reminder Scan Results

Sanitized aggregate output:

```text
reminder_scan_status_code: not run
candidate_count:           not captured
created_count:             not captured
duplicate_count:           not captured
```

## First Production Delivery Run

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
local production temp cleanup:                     not run
delivery state documented (go-live or disabled):   not run
SMTP VPC endpoint state documented:                not run
```

## Evidence Hygiene

This evidence intentionally does not include:

- Recipient email addresses
- Cognito emails
- Tenant IDs
- JWTs or authorization headers
- SMTP or SES credentials
- DKIM token values
- SSM values
- DB endpoints or connection strings
- Account IDs or ARNs
- Notification titles or message bodies
- Raw SES responses or SMTP transcripts
- DMARC rua or ruf email addresses
- Screenshots with sensitive values

## Notes

- If first delivery `attempted_count` was `0`, this evidence must not claim
  successful production SES delivery.
- If any delivery failed, capture only sanitized failure categories and create a
  follow-up issue. Do not paste raw SMTP or SES output.
- SES domain identity verification (`SUCCESS`) must be confirmed before the
  first real send. A `PENDING` status means DNS has not propagated yet.
- Bounce and complaint alarms must be deployed and in `OK` state before the
  first real send. Do not skip the alarm review step.
