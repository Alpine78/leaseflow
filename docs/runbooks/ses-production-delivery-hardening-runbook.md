# SES Production Delivery Hardening Runbook

## Purpose

Execute the controlled production SES enablement path after all pre-flight
planning documents have been reviewed and the required backend capabilities are
deployed.

This runbook validates that production SES SMTP delivery works end-to-end
through a controlled pilot tenant before real customers are on-boarded. It is
an operator-executed production enablement. It is not a dev runbook, not
automated, and not a browser feature.

Companion planning document:
`docs/ses-production-delivery-hardening.md`

## Guardrails

- Run this only after all preconditions are met.
- Keep RDS private; do not make RDS public at any stage.
- Do not add a NAT Gateway.
- Do not expose scan or delivery through browser routes.
- Do not capture recipient emails, Cognito emails, tenant IDs, JWTs,
  authorization headers, SMTP credentials, SES credentials, SSM values,
  DB endpoints, ARNs, account IDs, notification titles, notification bodies,
  raw SES responses, or raw SMTP transcripts in evidence or committed files.
- Do not commit DKIM CNAME token values, SPF record values, or DMARC tag values.
- Use a controlled pilot tenant with verified contacts only.
- The pilot tenant must not have real customer data.
- Do not record a pass without resolving any failed or zero-attempted-count
  delivery results.

## Preconditions

Before running this runbook, confirm that all of the following are true:

1. `docs/ses-production-delivery-hardening.md` — reviewed and understood.
2. `docs/ses-production-domain-identity-dns-authentication.md` — reviewed;
   sending domain decision is made.
3. `docs/ses-bounce-complaint-ingestion.md` — reviewed; EventBridge ingestion
   path is deployed and the SES feedback processor is deployed.
4. `docs/ses-delivery-monitoring-alarms-cost-controls.md` — reviewed; alarm
   direction is understood and alarms are deployed or this step is explicitly
   deferred.
5. Suppression model is deployed: `notification_contact_suppressions` table
   exists and delivery eligibility excludes suppressed contacts.
6. SES configuration set is created and configured with an EventBridge event
   destination for bounce and complaint feedback.
7. WSL/Linux shell has `aws`, `terraform`, `jq`, `curl`, and `dig`.
8. `AWS_PROFILE=terraform` and `AWS_REGION=eu-north-1` are set for all commands.
9. Production stack is running and the latest backend artifact is deployed.
10. Deployed DB migrations are current.

References:

- SES production access request:
  <https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html>
- SES verified identities:
  <https://docs.aws.amazon.com/ses/latest/dg/verify-addresses-and-domains.html>
- SES Easy DKIM:
  <https://docs.aws.amazon.com/ses/latest/dg/send-email-authentication-dkim-easy.html>
- SES SPF authentication:
  <https://docs.aws.amazon.com/ses/latest/dg/send-email-authentication-spf.html>
- SES DMARC:
  <https://docs.aws.amazon.com/ses/latest/dg/send-email-authentication-dmarc.html>
- SES SMTP credentials:
  <https://docs.aws.amazon.com/ses/latest/dg/smtp-credentials.html>
- SES SMTP VPC endpoints:
  <https://docs.aws.amazon.com/ses/latest/dg/send-email-set-up-vpc-endpoints.html>
- SES configuration sets:
  <https://docs.aws.amazon.com/ses/latest/dg/using-configuration-sets.html>
- SES event publishing:
  <https://docs.aws.amazon.com/ses/latest/dg/monitor-using-event-publishing.html>

## Step 1: Submit SES Production Access Request

What it does: requests that AWS move the SES account out of sandbox mode.
Target service: AWS Support.

Open an AWS Support case requesting production access for SES in
`eu-north-1`. The request should describe the use case (operational due
reminder emails for tenants of a property management tool), expected daily send
volume, expected bounce/complaint handling, and how unsubscribe requests are
handled.

Required AWS information for the request:

- Use case description
- Expected daily send volume
- How to handle bounces, complaints, and unsubscribes

Do not include account IDs, tenant IDs, recipient emails, or real customer data
in evidence. Record only the support case number in sanitized evidence.

Expected result:

- AWS Support case is open.
- Case number is noted locally for tracking.
- AWS approves production access before Step 9 is executed.

## Step 2: Create Domain Identity In SES And Record DKIM Token Count

What it does: creates a domain identity in SES and generates DKIM CNAME
tokens that must be published in DNS.
Target service: AWS SES in `eu-north-1`.

Create the domain identity in the SES console or via CLI. After creation,
SES generates three DKIM CNAME token names and target values for Easy DKIM.
Note the token names locally; do not commit token values.

```bash
export AWS_PROFILE=terraform
export AWS_REGION=eu-north-1

aws sesv2 get-email-identity \
  --email-identity "<sending-domain>" \
  --query '{DkimStatus: DkimAttributes.Status, DkimTokenCount: length(DkimAttributes.Tokens)}' \
  --output json
```

Expected result:

- Identity exists and reports a `DkimTokenCount` of `3`.
- DKIM status is `PENDING` until DNS records are published in Step 3.
- Token values are not printed into evidence.

## Step 3: Publish DNS Authentication Records

What it does: adds DKIM, SPF, and DMARC DNS records at the domain registrar.
Target service: DNS registrar for the sending domain.

### DKIM

Add the three CNAME records provided by SES Easy DKIM. Each record maps a
SES-generated subdomain to a SES verification target. The exact values come
from the SES console or the output of:

```bash
aws sesv2 get-email-identity \
  --email-identity "<sending-domain>" \
  --query 'DkimAttributes.Tokens' \
  --output json
```

Do not commit the token values. Verify propagation with:

```bash
for TOKEN in token1 token2 token3; do
  dig CNAME "${TOKEN}._domainkey.<sending-domain>" +short | head -1
done
```

Expected result: each `dig` line returns a non-empty CNAME target.

### SPF

Add or update the TXT record for the sending domain. If a custom MAIL FROM
domain is used, add the SPF record for that subdomain instead. A minimal record
allowing SES:

```
"v=spf1 include:amazonses.com ~all"
```

Verify propagation:

```bash
dig TXT "<sending-domain>" +short | grep spf
```

Expected result: SPF record includes `amazonses.com`.

### DMARC

Add a DMARC TXT record at `_dmarc.<sending-domain>`. Start with a monitoring
posture (`p=none`) before applying any stricter policy:

```
"v=DMARC1; p=none; rua=mailto:<dmarc-aggregate-inbox>"
```

Do not commit the `rua` email address value in evidence.

Verify propagation:

```bash
dig TXT "_dmarc.<sending-domain>" +short | grep DMARC
```

Expected result: DMARC record is present with `p=none`.

## Step 4: Confirm SES Domain Identity Verification Status

What it does: confirms that SES has validated the DKIM CNAME records and
marks the domain identity as verified.
Target service: AWS SES in `eu-north-1`.

DNS propagation can take minutes to hours. Poll until the status is
`SUCCESS`:

```bash
aws sesv2 get-email-identity \
  --email-identity "<sending-domain>" \
  --query '{DkimStatus: DkimAttributes.Status, IdentityType: IdentityType}' \
  --output json
```

Expected result:

- `DkimStatus` is `SUCCESS`.
- `IdentityType` is `DOMAIN`.
- The sending domain value is not printed into evidence.

## Step 5: Review Production Alarm Thresholds

What it does: confirms that CloudWatch alarms for bounce rate, complaint rate,
delivery failures, and send volume are deployed and set to production-appropriate
thresholds before any real send.
Target service: CloudWatch alarms in `eu-north-1`.

Review `docs/ses-delivery-monitoring-alarms-cost-controls.md` and confirm:

- Bounce rate alarm threshold is set appropriately (below the SES 5% bounce
  rate hard limit).
- Complaint rate alarm threshold is set appropriately (below the SES 0.1%
  complaint rate hard limit).
- Delivery failure alarm exists and is not stuck in INSUFFICIENT_DATA.
- Send volume spike alarm exists.
- All alarms notify an operator-owned SNS topic.

```bash
aws cloudwatch describe-alarms \
  --alarm-name-prefix "leaseflow-" \
  --query 'MetricAlarms[].{Name:AlarmName,State:StateValue}' \
  --output table
```

Expected result:

- Relevant alarms are listed and none are in ALARM state before the first send.
- Alarm names and states are safe to capture in evidence; do not capture alarm
  ARNs or SNS topic values.

## Step 6: Configure Production Terraform Vars

What it does: enables the production SES SMTP delivery path.
Target filename: ignored production `terraform.tfvars`.

Set the required variables in the local ignored `terraform.tfvars`. Use real
local values only in the ignored file, never in committed docs or evidence.

```hcl
ses_sender_email              = "<verified-sender-email>"
ses_smtp_vpc_endpoint_enabled = true

notification_email_delivery_enabled = true
notification_email_sender           = "<verified-sender-email>"
notification_email_smtp_host        = ""
notification_email_smtp_port        = 587

notification_email_smtp_username_ssm_param = "/leaseflow/prod/notification-email/smtp/username"
notification_email_smtp_password_ssm_param = "/leaseflow/prod/notification-email/smtp/password"

notification_email_batch_size   = 10
notification_email_max_attempts = 3
```

Expected result:

- Local ignored Terraform vars are ready for an intentional production apply.
- SMTP credential values are not placed in Terraform files.

## Step 7: Verify SSM Parameter Presence Without Printing Values

What it does: checks that production SMTP credential SSM parameters exist and
are decryptable without printing values.
Target service: AWS Systems Manager Parameter Store.

```bash
export SMTP_USERNAME_PARAM="/leaseflow/prod/notification-email/smtp/username"
export SMTP_PASSWORD_PARAM="/leaseflow/prod/notification-email/smtp/password"

aws ssm get-parameter \
  --name "$SMTP_USERNAME_PARAM" \
  --with-decryption \
  --query 'Parameter.Type' \
  --output text

aws ssm get-parameter \
  --name "$SMTP_PASSWORD_PARAM" \
  --with-decryption \
  --query 'Parameter.Type' \
  --output text
```

Expected result:

- Both commands print `SecureString`.
- No SMTP username or password value is printed.

## Step 8: Apply Production Stack

What it does: applies the production Terraform configuration with delivery
enabled and the SES SMTP VPC endpoint active.
Target service: Terraform-managed production stack and backend Lambda.

```bash
cd /mnt/c/Repos/LeaseFlow
bash scripts/dev/build-lambda.sh
bash scripts/dev/apply-stack.sh
```

Confirm the Lambda has the expected delivery environment variables without
printing values:

```bash
aws lambda get-function-configuration \
  --function-name leaseflow-prod-backend \
  --query 'Environment.Variables | keys(@)' \
  --output json
```

Expected result:

- Terraform apply completes after explicit operator approval.
- Lambda environment variable key list includes delivery-related keys.
- No env var values are printed.

## Step 9: Prepare Controlled Pilot Tenant

What it does: identifies or creates a controlled pilot tenant with at least one
enabled, verified-domain notification contact and at least one due-soon reminder
candidate.
Target service: Cognito, API Gateway, Lambda, and private RDS through existing
supported paths.

```bash
cd /mnt/c/Repos/LeaseFlow/infra/environments/prod
export USER_POOL_ID=$(terraform output -raw cognito_user_pool_id)
export PILOT_COGNITO_USERNAME="<local-pilot-cognito-username>"

export PILOT_TENANT=$(
  aws cognito-idp admin-get-user \
    --user-pool-id "$USER_POOL_ID" \
    --username "$PILOT_COGNITO_USERNAME" \
    --query 'UserAttributes[?Name==`custom:tenant_id`].Value | [0]' \
    --output text
)

test -n "$PILOT_TENANT"
test "$PILOT_TENANT" != "None"
```

Expected result:

- `$PILOT_TENANT` is set locally but not printed into evidence.
- The pilot tenant has due-soon reminder source data.
- The tenant has at least one enabled notification contact with an address in
  the verified production domain.
- The contact has no active suppression.

## Step 10: Load Safe Production Runtime Values

What it does: reads local operator values needed for Lambda invocation.
Target service: Terraform-managed production stack.

```bash
export AWS_PROFILE=terraform
export AWS_REGION=eu-north-1
export BACKEND_FUNCTION=leaseflow-prod-backend
export PROD_TMP_DIR=$(mktemp -d)
trap 'rm -rf "${PROD_TMP_DIR}"' EXIT
```

Expected result:

- `$PROD_TMP_DIR` is outside the repo.
- No secrets or tenant values are printed.

## Step 11: Run Reminder Scan For Pilot Tenant

What it does: creates or de-duplicates persisted due reminder notifications
for the pilot tenant before delivery.
Target service: backend Lambda internal reminder scan event.

```bash
jq -n \
  --arg tenant "$PILOT_TENANT" \
  '{
    source: "leaseflow.internal",
    "detail-type": "scan_due_lease_reminders",
    detail: {
      tenant_id: $tenant,
      days: 7
    }
  }' > "${PROD_TMP_DIR}/reminder-scan-payload.json"

aws lambda invoke \
  --region "$AWS_REGION" \
  --function-name "$BACKEND_FUNCTION" \
  --cli-binary-format raw-in-base64-out \
  --payload "fileb://${PROD_TMP_DIR}/reminder-scan-payload.json" \
  "${PROD_TMP_DIR}/reminder-scan-response.json"

jq -e '.statusCode == 200' "${PROD_TMP_DIR}/reminder-scan-response.json"
jq -r '.body | fromjson | {candidate_count, created_count, duplicate_count}' \
  "${PROD_TMP_DIR}/reminder-scan-response.json"
```

Expected result:

- Lambda response `statusCode` is `200`.
- Aggregate counts are visible.
- No tenant ID or notification body is captured.

## Step 12: Run First Production Delivery Invocation

What it does: invokes internal email delivery for the pilot tenant through the
production SES SMTP path.
Target service: backend Lambda internal delivery event and production SES SMTP.

```bash
jq -n \
  --arg tenant "$PILOT_TENANT" \
  '{
    source: "leaseflow.internal",
    "detail-type": "deliver_notification_emails",
    detail: {
      tenant_id: $tenant
    }
  }' > "${PROD_TMP_DIR}/delivery-payload.json"

aws lambda invoke \
  --region "$AWS_REGION" \
  --function-name "$BACKEND_FUNCTION" \
  --cli-binary-format raw-in-base64-out \
  --payload "fileb://${PROD_TMP_DIR}/delivery-payload.json" \
  "${PROD_TMP_DIR}/delivery-response-1.json"

jq -e '.statusCode == 200' "${PROD_TMP_DIR}/delivery-response-1.json"
jq -r '.body | fromjson | {
  enabled,
  candidate_count,
  created_count,
  duplicate_count,
  attempted_count,
  sent_count,
  failed_count
}' "${PROD_TMP_DIR}/delivery-response-1.json"
```

Expected result for pass:

- `enabled` is `true`.
- `candidate_count` is at least `1`.
- `attempted_count` is at least `1`.
- `sent_count` is at least `1`.
- `failed_count` is `0`.

If `attempted_count` is `0`, the likely causes are missing enabled contact,
missing due notification, exhausted attempts, existing suppression, or already
sent deliveries. Do not record a pass without resolving the cause.

## Step 13: Run Second Delivery Invocation For Idempotency

What it does: verifies that sent delivery rows are not selected again on a
repeat invocation.
Target service: backend Lambda internal delivery event.

```bash
aws lambda invoke \
  --region "$AWS_REGION" \
  --function-name "$BACKEND_FUNCTION" \
  --cli-binary-format raw-in-base64-out \
  --payload "fileb://${PROD_TMP_DIR}/delivery-payload.json" \
  "${PROD_TMP_DIR}/delivery-response-2.json"

jq -e '.statusCode == 200' "${PROD_TMP_DIR}/delivery-response-2.json"
jq -r '.body | fromjson | {
  enabled,
  candidate_count,
  created_count,
  duplicate_count,
  attempted_count,
  sent_count,
  failed_count
}' "${PROD_TMP_DIR}/delivery-response-2.json"
```

Expected result for pass:

- `enabled` is `true`.
- `attempted_count` is `0`.
- `sent_count` is `0`.
- `failed_count` is `0`.
- `duplicate_count` may increase because delivery rows already exist.

## Step 14: Clean Up Local Files And Variables

What it does: removes local payload and response files that can contain
tenant-scoped values.
Target service: local WSL/Linux shell.

```bash
rm -rf "$PROD_TMP_DIR"
trap - EXIT
unset PROD_TMP_DIR PILOT_TENANT PILOT_COGNITO_USERNAME
unset SMTP_USERNAME_PARAM SMTP_PASSWORD_PARAM
```

Expected result:

- Temporary local production files are deleted.
- Sensitive shell variables are cleared.

## Step 15: Post-Validation State

What it does: documents whether production delivery remains enabled or is
disabled after pilot validation.
Target service: Terraform-managed production stack.

After a successful pilot validation:

- Leave `notification_email_delivery_enabled = true` if production sending is
  now go-live.
- Leave `ses_smtp_vpc_endpoint_enabled = true` as long as production sending is
  active; remove it only if sending is fully disabled to avoid interface endpoint
  charges.
- If pilot validation failed or is deferred, disable delivery and the endpoint:

```hcl
ses_smtp_vpc_endpoint_enabled       = false
notification_email_delivery_enabled = false
```

Then apply:

```bash
cd /mnt/c/Repos/LeaseFlow
bash scripts/dev/apply-stack.sh
```

Expected result:

- Production delivery state matches the go-live decision.
- Interface endpoint cost exposure is documented and intentional.

## Evidence To Capture

Use
`docs/runbooks/evidence/ses-production-delivery-hardening-template.md`
as the starting point for a dated evidence file.

Safe evidence:

- Date.
- Branch.
- Issue number.
- Region.
- AWS Support case number (not account ID).
- Precondition pass/fail lines.
- DKIM/SPF/DMARC propagation pass/fail (no token values or record contents).
- SES domain identity verification status (`SUCCESS` or `PENDING`).
- CloudWatch alarm state summary.
- SSM parameter type confirmation (`SecureString`).
- Reminder scan aggregate counts.
- First delivery aggregate counts.
- Second delivery aggregate counts.
- Cleanup pass/fail lines.
- Go-live or deferred decision.

Forbidden evidence:

- Recipient email addresses.
- Cognito emails.
- Tenant IDs.
- JWTs or authorization headers.
- SMTP or SES credentials.
- DKIM token values.
- SSM values.
- DB endpoints or connection strings.
- Account IDs or ARNs.
- Notification titles or message bodies.
- Raw SES responses or SMTP transcripts.
- DMARC `rua` or `ruf` email addresses.
- Screenshots with sensitive values.

## Success Criteria

- SES production access request is submitted and approved.
- Domain identity DKIM status is `SUCCESS` in SES before first send.
- DKIM CNAME, SPF TXT, and DMARC TXT records are propagated and confirmed.
- SMTP credential parameters exist as `SecureString` and values are not printed.
- Bounce and complaint alarms are deployed before the first real send.
- Reminder scan returns `200`.
- First production delivery run returns `200` with at least one sent delivery
  and no failed deliveries.
- Second delivery run returns `200` with no new attempted, sent, or failed
  deliveries for the same tenant.
- Local production files are removed.
- Delivery state is intentional — either go-live or explicitly disabled.
