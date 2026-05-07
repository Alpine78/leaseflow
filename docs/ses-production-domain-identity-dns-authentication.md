# SES Production Domain Identity And DNS Authentication Plan

## Purpose

This document defines the production sender identity and DNS authentication
direction for LeaseFlow notification email.

This is a planning artifact only. It does not create SES identities, DNS
records, Terraform resources, production access requests, backend behavior,
frontend behavior, or email-sending changes.

## Current State

- Dev SES SMTP delivery exists as an internal backend worker and is disabled by
  default.
- Dev SES delivery smoke evidence exists for the controlled development path.
- Production sender identity does not exist.
- Production DNS authentication records have not been created.
- SES production access and production deliverability readiness are not in
  place.
- Bounce, complaint, suppression, unsubscribe, monitoring, and cost-control
  hardening remain separate production-readiness work.

## Sender Identity Direction

The production sender identity should be a dedicated sender subdomain, written
generically as `<notification-sender-subdomain>`.

Use an SES domain identity for `<notification-sender-subdomain>` rather than a
single email-address identity. A domain identity is the better production fit
because it supports operational sender addresses under the same controlled
subdomain without verifying each individual address.

Repository docs, evidence, and PRs must not include real production domains,
email addresses, hosted zone names, DNS record values, AWS account IDs, SES
provider responses, tenant IDs, or credentials.

## DNS Authentication Plan

### SES Domain Identity

The future implementation should create or register an SES domain identity for
`<notification-sender-subdomain>` in the selected production SES Region.

The identity must be verified before any production access request or broad
sending rollout is treated as ready.

### DKIM

Easy DKIM is the default DKIM approach.

The future implementation should use SES-generated DKIM records for the domain
identity and publish the required CNAME records through the DNS provider. The
rollout must wait until SES reports the identity and DKIM signing status as
verified before claiming sender authentication is complete.

BYODKIM is out of scope unless a later compliance requirement justifies the
extra key-management responsibility.

### SPF

The first DNS plan should review SPF through SES default MAIL FROM behavior.
With default MAIL FROM, SES uses an Amazon-owned MAIL FROM domain and SPF is
handled by SES for that envelope sender path.

Do not claim strict SPF alignment for the production sender until the project
explicitly decides whether to use a custom MAIL FROM domain.

### DMARC

DMARC should start in monitoring mode.

The initial posture should use monitoring-only policy language such as
`p=none`, with reporting destinations decided outside this repository. Do not
commit real report mailbox addresses or provider-generated DNS values.

Move to stricter DMARC policies only after DKIM alignment, bounce/complaint
handling, suppression behavior, and production monitoring have been validated.

### Custom MAIL FROM

Custom MAIL FROM is deferred to a follow-up decision.

If adopted later, it must use a dedicated MAIL FROM subdomain that is not reused
for normal sending or receiving. The follow-up plan must include the required
MX record, SPF TXT record, behavior on MX failure, operational ownership, and
rollback path.

## Production Access Prerequisites

Before requesting SES production access for LeaseFlow notification email, the
project should have:

- Verified domain identity for `<notification-sender-subdomain>`.
- Easy DKIM verification and signing confirmed.
- Sending use case documented as tenant notification and due reminder
  operational mail.
- Recipient source confirmed as tenant-scoped notification contacts.
- Bounce and complaint handling plan in place.
- Suppression and unsubscribe/preference model planned for applicable message
  types.
- Monitoring, alarms, batch limits, retry limits, and cost controls planned.
- Sanitized runbook/evidence rules for production rollout.

Production access should not be treated as production readiness by itself.

## Security And Cost Boundaries

- Browser routes must not trigger reminder scans, email delivery, or production
  rollout actions.
- Tenant context must continue to come from validated Cognito JWT claims, not
  browser request bodies or query parameters.
- Production identity planning must not make RDS public.
- Production identity planning must not introduce NAT Gateway by default.
- Production identity planning must not commit or log real domains, email
  addresses, DNS values, tenant IDs, JWTs, SMTP credentials, SES credentials,
  SSM values, DB endpoints, notification content, raw SES responses, or raw
  SMTP transcripts.

## Follow-Up Work

- Add SES production domain identity and DNS implementation plan.
- Add SES production access request runbook.
- Add SES bounce and complaint ingestion.
- Add notification suppression and unsubscribe/preference model.
- Add SES delivery monitoring, alarms, and cost controls.
- Add production SES rollout runbook and sanitized evidence template.

## References

- [Amazon SES verified identities](https://docs.aws.amazon.com/ses/latest/dg/verify-addresses-and-domains.html)
- [Amazon SES Easy DKIM](https://docs.aws.amazon.com/ses/latest/dg/send-email-authentication-dkim-easy.html)
- [Amazon SES SPF authentication](https://docs.aws.amazon.com/ses/latest/dg/send-email-authentication-spf.html)
- [Amazon SES custom MAIL FROM](https://docs.aws.amazon.com/ses/latest/dg/mail-from.html)
- [Amazon SES DMARC](https://docs.aws.amazon.com/ses/latest/dg/send-email-authentication-dmarc.html)
- [Amazon SES production access](https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html)
