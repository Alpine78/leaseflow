# SES Notification Email Delivery Smoke Test Runbook

## Purpose

Validate the disabled-by-default internal notification email delivery worker in a
controlled dev stack. The smoke path verifies that persisted due reminder
notifications can be delivered through SES SMTP and that a second delivery run
does not resend already-sent delivery rows.

This is an operator-run dev validation. It is not production email readiness,
monitoring, a browser feature, or an automated scheduler.

## Guardrails

- Run this only in dev.
- Keep RDS private; do not make RDS public to create or inspect contacts.
- Do not add a NAT Gateway.
- Do not expose scan or delivery through browser routes.
- Do not capture recipient emails, Cognito emails, tenant IDs, JWTs,
  authorization headers, SMTP credentials, SSM values, DB endpoints,
  notification titles, notification bodies, raw SES responses, or raw SMTP
  transcripts.
- Use synthetic test data only.
- Disable delivery and the SES SMTP VPC endpoint after validation unless more
  dev testing is planned.

## Current Limitation

Successful smoke validation requires an enabled `notification_contacts` row for
the smoke tenant. The current app has the DB model and backend data-access
methods, but no browser route, public API, or internal operator event for
creating contacts.

If the controlled dev tenant does not already have an enabled contact row, stop
this runbook and create a separate follow-up ticket for a safe operator contact
setup path. Do not work around this by making RDS public or committing local DB
payloads.

## Preconditions

- WSL/Linux shell has `aws`, `terraform`, `jq`, and `curl`.
- `AWS_PROFILE=terraform` and `AWS_REGION=eu-north-1` are set.
- Dev stack exists and uses the latest backend artifact that includes the
  `deliver_notification_emails` internal event.
- Deployed DB migrations have been run after the delivery migration was added.
- SES sender identity is verified in the same AWS Region.
- In SES sandbox, the intended test recipient is also verified unless an SES
  mailbox simulator address is used.
- SES SMTP credentials have been created by the operator outside Terraform and
  stored in SSM SecureString parameters.
- The smoke tenant has at least one enabled notification contact and at least
  one due-soon reminder notification candidate.

References:

- SES verified identities and sandbox restrictions:
  <https://docs.aws.amazon.com/ses/latest/dg/verify-addresses-and-domains.html>
- SES SMTP credentials:
  <https://docs.aws.amazon.com/ses/latest/dg/smtp-credentials.html>
- SES SMTP VPC endpoints:
  <https://docs.aws.amazon.com/ses/latest/dg/send-email-set-up-vpc-endpoints.html>
- SES SMTP TLS/STARTTLS:
  <https://docs.aws.amazon.com/ses/latest/dg/smtp-connect.html>

## Step 1: Configure Delivery In Local Terraform Vars

What it does: enables only the existing dev SES SMTP delivery path.
Target filename/service: ignored `infra/environments/dev/terraform.tfvars` and
Terraform-managed dev stack.

Set the existing variables in local `terraform.tfvars`. Use real local values
only in the ignored file, never in committed docs or evidence.

```hcl
ses_sender_email              = "<verified-sender-email>"
ses_smtp_vpc_endpoint_enabled = true

notification_email_delivery_enabled = true
notification_email_sender           = "<verified-sender-email>"
notification_email_smtp_host        = ""
notification_email_smtp_port        = 587

notification_email_smtp_username_ssm_param = "/leaseflow/dev/notification-email/smtp/username"
notification_email_smtp_password_ssm_param = "/leaseflow/dev/notification-email/smtp/password"

notification_email_batch_size   = 10
notification_email_max_attempts = 3
```

Expected result:

- Local ignored Terraform vars are ready for an intentional dev apply.
- SMTP credential values are not placed in Terraform files.

## Step 2: Verify SSM Parameter Presence Without Printing Values

What it does: checks that configured SSM parameters exist and are decryptable
without printing parameter values.
Target service: AWS Systems Manager Parameter Store.

```bash
export SMTP_USERNAME_PARAM="/leaseflow/dev/notification-email/smtp/username"
export SMTP_PASSWORD_PARAM="/leaseflow/dev/notification-email/smtp/password"

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

## Step 3: Apply Dev Stack And Run Migrations

What it does: applies the configured dev stack and runs DB migrations through
the internal migration event.
Target service: Terraform-managed dev stack and backend Lambda.

```bash
cd /mnt/c/Repos/LeaseFlow
bash scripts/dev/build-lambda.sh
bash scripts/dev/apply-stack.sh
bash scripts/dev/run-migrations.sh
```

Expected result:

- Terraform apply completes after explicit operator approval.
- Lambda has delivery env vars and scoped SSM/KMS access.
- Migration response succeeds.

## Step 4: Prepare Controlled Smoke Data

What it does: creates or identifies synthetic tenant data for the delivery run.
Target service: Cognito, API Gateway, Lambda, and private RDS through existing
supported paths.

Use an existing controlled dev tenant or create one with the current seed flow:

```bash
bash scripts/dev/seed-demo-data.sh
```

If using a Cognito user, store the username locally and derive the tenant claim
without printing it:

```bash
cd /mnt/c/Repos/LeaseFlow/infra/environments/dev
export USER_POOL_ID=$(terraform output -raw cognito_user_pool_id)
export SMOKE_COGNITO_USERNAME="<local-cognito-username>"

export SMOKE_TENANT=$(
  aws cognito-idp admin-get-user \
    --user-pool-id "$USER_POOL_ID" \
    --username "$SMOKE_COGNITO_USERNAME" \
    --query 'UserAttributes[?Name==`custom:tenant_id`].Value | [0]' \
    --output text
)

test -n "$SMOKE_TENANT"
test "$SMOKE_TENANT" != "None"
```

Expected result:

- `$SMOKE_TENANT` is set locally but not printed into evidence.
- The tenant has due-soon reminder source data.
- The tenant already has at least one enabled `notification_contacts` row.

Stop condition:

- If no enabled contact exists for this tenant, stop. Do not mark smoke as
  passed.

## Step 5: Load Safe Dev Runtime Values

What it does: reads local operator values needed for Lambda invocation.
Target service: Terraform-managed dev stack.

```bash
cd /mnt/c/Repos/LeaseFlow/infra/environments/dev
export AWS_PROFILE=terraform
export AWS_REGION=eu-north-1
export BACKEND_FUNCTION=leaseflow-dev-backend
export SMOKE_TMP_DIR=$(mktemp -d)
trap 'rm -rf "${SMOKE_TMP_DIR}"' EXIT
```

Expected result:

- `$SMOKE_TMP_DIR` is outside the repo.
- No secrets or tenant values are printed.

## Step 6: Run Reminder Scan For The Smoke Tenant

What it does: creates or de-duplicates persisted due reminder notifications
before delivery.
Target service: backend Lambda internal reminder scan event.

```bash
jq -n \
  --arg tenant "$SMOKE_TENANT" \
  '{
    source: "leaseflow.internal",
    "detail-type": "scan_due_lease_reminders",
    detail: {
      tenant_id: $tenant,
      days: 7
    }
  }' > "${SMOKE_TMP_DIR}/reminder-scan-payload.json"

aws lambda invoke \
  --region "$AWS_REGION" \
  --function-name "$BACKEND_FUNCTION" \
  --cli-binary-format raw-in-base64-out \
  --payload "fileb://${SMOKE_TMP_DIR}/reminder-scan-payload.json" \
  "${SMOKE_TMP_DIR}/reminder-scan-response.json"

jq -e '.statusCode == 200' "${SMOKE_TMP_DIR}/reminder-scan-response.json"
jq -r '.body | fromjson | {candidate_count, created_count, duplicate_count}' \
  "${SMOKE_TMP_DIR}/reminder-scan-response.json"
```

Expected result:

- Lambda response `statusCode` is `200`.
- Aggregate counts are visible.
- No tenant ID or notification body is captured.

## Step 7: Run First Delivery Invocation

What it does: invokes internal email delivery for the smoke tenant.
Target service: backend Lambda internal delivery event and SES SMTP path.

```bash
jq -n \
  --arg tenant "$SMOKE_TENANT" \
  '{
    source: "leaseflow.internal",
    "detail-type": "deliver_notification_emails",
    detail: {
      tenant_id: $tenant
    }
  }' > "${SMOKE_TMP_DIR}/delivery-payload.json"

aws lambda invoke \
  --region "$AWS_REGION" \
  --function-name "$BACKEND_FUNCTION" \
  --cli-binary-format raw-in-base64-out \
  --payload "fileb://${SMOKE_TMP_DIR}/delivery-payload.json" \
  "${SMOKE_TMP_DIR}/delivery-response-1.json"

jq -e '.statusCode == 200' "${SMOKE_TMP_DIR}/delivery-response-1.json"
jq -r '.body | fromjson | {
  enabled,
  candidate_count,
  created_count,
  duplicate_count,
  attempted_count,
  sent_count,
  failed_count
}' "${SMOKE_TMP_DIR}/delivery-response-1.json"
```

Expected result for pass:

- `enabled` is `true`.
- `candidate_count` is at least `1`.
- `attempted_count` is at least `1`.
- `sent_count` is at least `1`.
- `failed_count` is `0`.

If `attempted_count` is `0`, the likely causes are missing enabled contact,
missing due notification, exhausted attempts, or already-sent deliveries. Do not
record a pass without resolving the cause.

## Step 8: Run Second Delivery Invocation For Idempotency

What it does: verifies sent delivery rows are not selected again.
Target service: backend Lambda internal delivery event.

```bash
aws lambda invoke \
  --region "$AWS_REGION" \
  --function-name "$BACKEND_FUNCTION" \
  --cli-binary-format raw-in-base64-out \
  --payload "fileb://${SMOKE_TMP_DIR}/delivery-payload.json" \
  "${SMOKE_TMP_DIR}/delivery-response-2.json"

jq -e '.statusCode == 200' "${SMOKE_TMP_DIR}/delivery-response-2.json"
jq -r '.body | fromjson | {
  enabled,
  candidate_count,
  created_count,
  duplicate_count,
  attempted_count,
  sent_count,
  failed_count
}' "${SMOKE_TMP_DIR}/delivery-response-2.json"
```

Expected result for pass:

- `enabled` is `true`.
- `attempted_count` is `0`.
- `sent_count` is `0`.
- `failed_count` is `0`.
- `duplicate_count` may increase because the delivery rows already exist.

## Step 9: Clean Up Local Smoke Files And Variables

What it does: removes local payload/response files that can contain tenant
scoped values.
Target service: local WSL/Linux shell.

```bash
rm -rf "$SMOKE_TMP_DIR"
trap - EXIT
unset SMOKE_TMP_DIR SMOKE_TENANT SMOKE_COGNITO_USERNAME
unset SMTP_USERNAME_PARAM SMTP_PASSWORD_PARAM
```

Expected result:

- Temporary local smoke files are deleted.
- Sensitive shell variables are cleared.

## Step 10: Disable Delivery And Optional Endpoint

What it does: returns the dev stack to low-cost defaults after validation.
Target service: Terraform-managed dev stack.

In local `terraform.tfvars`, set:

```hcl
ses_smtp_vpc_endpoint_enabled      = false
notification_email_delivery_enabled = false
```

Then apply intentionally:

```bash
cd /mnt/c/Repos/LeaseFlow
bash scripts/dev/apply-stack.sh
```

Expected result:

- Delivery is disabled.
- The optional billable SMTP VPC endpoint is removed if no further delivery
  testing is planned.

## Evidence To Capture

Use `docs/runbooks/evidence/ses-notification-email-delivery-smoke-test-template.md`
as the starting point for a dated evidence file.

Safe evidence:

- Date.
- Branch.
- Issue number.
- Region.
- Precondition pass/fail lines.
- Reminder scan aggregate counts.
- First delivery aggregate counts.
- Second delivery aggregate counts.
- Cleanup pass/fail lines.

Forbidden evidence:

- Recipient email addresses.
- Cognito emails.
- Tenant IDs.
- JWTs or authorization headers.
- SMTP or SES credentials.
- SSM values.
- DB endpoints or connection strings.
- Notification titles or message bodies.
- Raw SES responses or SMTP transcripts.
- Screenshots with sensitive values.

## Success Criteria

- Sender identity and sandbox recipient requirements are satisfied.
- SMTP credential parameters exist as `SecureString` and values are not printed.
- Dev delivery is explicitly enabled only for the smoke window.
- Reminder scan returns `200`.
- First delivery run returns `200` with at least one sent delivery and no failed
  deliveries.
- Second delivery run returns `200` with no new attempted/sent/failed
  deliveries for the same tenant.
- Local smoke files are removed.
- Delivery and optional SMTP endpoint are disabled after validation unless more
  testing is planned.
