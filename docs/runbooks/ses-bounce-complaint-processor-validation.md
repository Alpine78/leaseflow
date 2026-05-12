# SES Bounce And Complaint Processor Validation Runbook

## Purpose

Validate that the disabled-by-default SES bounce and complaint feedback
processor handles synthetic provider events safely in a controlled dev stack.
The validation path verifies that the Lambda route handler accepts `aws.ses`
bounce and complaint event types, processes them without error, and returns
safe aggregate response counts.

This is an operator-run dev validation. It is not production readiness,
a browser feature, or an automated scheduler.

## Guardrails

- Run this only in dev.
- Keep RDS private.
- Do not make RDS public to inspect or modify suppression state.
- Do not add a NAT Gateway.
- Do not expose bounce or complaint processing through browser routes.
- Do not capture recipient emails, Cognito emails, tenant IDs, JWTs,
  authorization headers, SMTP credentials, SES credentials, SSM values,
  DB endpoints, contact IDs, notification IDs, or raw SES payloads.
- Use only synthetic correlation tokens that do not exist in the DB.
- Processor invocation with an unknown correlation token is a safe no-op;
  no suppression or delivery state is written.

## Preconditions

- WSL/Linux shell has `aws`, `terraform`, and `jq`.
- `AWS_PROFILE=terraform` and `AWS_REGION=eu-north-1` are set.
- Dev stack exists and uses the latest backend artifact that includes the
  `process_ses_provider_feedback` handler.
- Deployed DB migrations have been run.

## Step 1: Load Safe Dev Runtime Values

What it does: reads the backend Lambda function name from Terraform output.
Target service: Terraform-managed dev stack.

```bash
cd /mnt/c/Repos/LeaseFlow/infra/environments/dev
export AWS_PROFILE=terraform
export AWS_REGION=eu-north-1
export BACKEND_FUNCTION=leaseflow-dev-backend
export VALIDATION_TMP_DIR=$(mktemp -d)
trap 'rm -rf "${VALIDATION_TMP_DIR}"' EXIT
```

Expected result:

- `$VALIDATION_TMP_DIR` is outside the repo.
- No secrets or tenant values are set or printed.

## Step 2: Verify EventBridge Routing Configuration

What it does: checks whether the optional SES feedback EventBridge rule
resource is present in Terraform state. This verifies the routing
configuration without printing resource ARNs or identifiers.

```bash
cd /mnt/c/Repos/LeaseFlow/infra/environments/dev
terraform state list | grep ses_feedback | grep -c eventbridge
```

Expected result:

- Count is `1` if the EventBridge processor module is enabled in the dev
  stack.
- Count is `0` if the module is disabled by default, which is the expected
  dev default. Both outcomes are safe; this step records the configured state.

## Step 3: Invoke Lambda With A Synthetic Bounce Event

What it does: invokes the backend Lambda with a minimal synthetic
`aws.ses` / `Email Bounced` event using a UUID correlation token that does
not exist in the DB. Verifies that the handler accepts the event type and
returns `200` with a safe no-op response.
Target service: backend Lambda.

```bash
jq -n '{
  source: "aws.ses",
  "detail-type": "Email Bounced",
  detail: {
    mail: {
      tags: {
        leaseflow_delivery_correlation: ["00000000-0000-0000-0000-000000000001"]
      }
    },
    bounce: {
      bounceType: "Permanent"
    }
  }
}' > "${VALIDATION_TMP_DIR}/bounce-payload.json"

aws lambda invoke \
  --region "$AWS_REGION" \
  --function-name "$BACKEND_FUNCTION" \
  --cli-binary-format raw-in-base64-out \
  --payload "fileb://${VALIDATION_TMP_DIR}/bounce-payload.json" \
  "${VALIDATION_TMP_DIR}/bounce-response.json"

jq -e '.statusCode == 200' "${VALIDATION_TMP_DIR}/bounce-response.json"
jq -r '.body | fromjson | {
  processed,
  feedback_type,
  bounce_count,
  complaint_count,
  suppressed_contact_count,
  unknown_correlation_count
}' "${VALIDATION_TMP_DIR}/bounce-response.json"
```

Expected result for pass:

- `statusCode` is `200`.
- `processed` is `false`.
- `feedback_type` is `"bounce"`.
- `bounce_count` is `0`.
- `unknown_correlation_count` is `1`.

The unknown correlation is expected and correct. The synthetic token does not
exist in the DB so no delivery or suppression state is written.

## Step 4: Invoke Lambda With A Synthetic Complaint Event

What it does: same as Step 3 using `Email Complaint Received`.
Target service: backend Lambda.

```bash
jq -n '{
  source: "aws.ses",
  "detail-type": "Email Complaint Received",
  detail: {
    mail: {
      tags: {
        leaseflow_delivery_correlation: ["00000000-0000-0000-0000-000000000002"]
      }
    },
    complaint: {
      complaintFeedbackType: "abuse"
    }
  }
}' > "${VALIDATION_TMP_DIR}/complaint-payload.json"

aws lambda invoke \
  --region "$AWS_REGION" \
  --function-name "$BACKEND_FUNCTION" \
  --cli-binary-format raw-in-base64-out \
  --payload "fileb://${VALIDATION_TMP_DIR}/complaint-payload.json" \
  "${VALIDATION_TMP_DIR}/complaint-response.json"

jq -e '.statusCode == 200' "${VALIDATION_TMP_DIR}/complaint-response.json"
jq -r '.body | fromjson | {
  processed,
  feedback_type,
  bounce_count,
  complaint_count,
  suppressed_contact_count,
  unknown_correlation_count
}' "${VALIDATION_TMP_DIR}/complaint-response.json"
```

Expected result for pass:

- `statusCode` is `200`.
- `processed` is `false`.
- `feedback_type` is `"complaint"`.
- `complaint_count` is `0`.
- `unknown_correlation_count` is `1`.

## Step 5: Verify CloudWatch Alarm Configuration

What it does: checks that the bounce and complaint alarms exist by name
without printing ARNs, state details, or identifiers.
Target service: AWS CloudWatch.

```bash
aws cloudwatch describe-alarms \
  --alarm-name-prefix "leaseflow-dev-ses-feedback-" \
  --query 'MetricAlarms[].{name: AlarmName, metric: MetricName, threshold: Threshold}' \
  --output table
```

Expected result:

- Two alarms with names ending in `-ses-feedback-bounce` and
  `-ses-feedback-complaint`.
- Metrics are `bounce_count` and `complaint_count`.
- Threshold is `1` for both.

If no alarms appear, verify that `notification_email_delivery_alarms_enabled`
is `true` in the dev stack and that Terraform has been applied.

## Step 6: Clean Up Local Validation Files And Variables

What it does: removes local payload and response files created during
validation.
Target service: local WSL/Linux shell.

```bash
rm -rf "$VALIDATION_TMP_DIR"
trap - EXIT
unset VALIDATION_TMP_DIR BACKEND_FUNCTION
```

Expected result:

- Temporary local files are deleted.
- Shell variables are cleared.

## Evidence To Capture

Use
`docs/runbooks/evidence/ses-bounce-complaint-monitoring-sanitized-evidence-2026-05-12.md`
as the starting point for a dated evidence file.

Safe evidence:

- Date and branch.
- EventBridge rule presence check (count only, no ARNs).
- Bounce Lambda response aggregate counts.
- Complaint Lambda response aggregate counts.
- Alarm name and threshold check output.
- Cleanup pass/fail lines.

Forbidden evidence:

- Recipient email addresses.
- Cognito emails.
- Tenant IDs.
- JWTs or authorization headers.
- SMTP or SES credentials.
- SSM values.
- DB endpoints or connection strings.
- Contact IDs, notification IDs, or correlation tokens from real deliveries.
- Raw SES responses or SMTP transcripts.
- Screenshots with sensitive values.
- AWS account IDs or resource ARNs.

## Success Criteria

- Lambda returns `200` for both synthetic bounce and complaint events.
- Response counts match expected safe no-op values.
- `unknown_correlation_count` is `1` for each synthetic invocation.
- No real delivery or suppression state was written.
- CloudWatch alarms for `bounce_count` and `complaint_count` exist with
  threshold `1`.
- Local validation files are removed.
