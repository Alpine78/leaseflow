# Deployed Dev Smoke Test Runbook

## Purpose

Validate that the Terraform-managed dev stack works end to end after `terraform
apply`: API Gateway, Cognito, Lambda, private RDS, migrations, reminder scan,
notifications, and cleanup.

This is an operator-run dev smoke test. It is not production monitoring or a
load test.

## Guardrails

- Run this only in dev.
- Keep RDS private.
- Do not print JWTs, passwords, SSM values, or full connection strings.
- Use synthetic smoke data only.
- Do not store tenant IDs, emails, property names, addresses, or resident names
  in evidence notes.
- Destroy the dev stack after testing if it is no longer needed.

## Preconditions

- WSL/Linux shell has `aws`, `terraform`, `curl`, and `jq`.
- `AWS_PROFILE=terraform` and `AWS_REGION=eu-north-1` are set.
- `dist/leaseflow-backend.zip` was built with `make build-lambda-artifact`.
- Dev stack was applied from `infra/environments/dev`.
- Deployed Lambda uses the current artifact.

## Step 1: Load Dev Outputs

What it does: reads deployed Terraform outputs needed by the smoke test.
Target service: Terraform-managed AWS dev environment.

```bash
cd /mnt/c/Repos/LeaseFlow/infra/environments/dev
export AWS_PROFILE=terraform
export AWS_REGION=eu-north-1

export API_URL=$(terraform output -raw api_stage_invoke_url)
export USER_POOL_ID=$(terraform output -raw cognito_user_pool_id)
export APP_CLIENT_ID=$(terraform output -raw cognito_user_pool_client_id)
export BACKEND_FUNCTION=leaseflow-dev-backend
```

Expected result:

- `$API_URL`, `$USER_POOL_ID`, and `$APP_CLIENT_ID` are populated.
- Do not paste Cognito tokens or future passwords into evidence.

## Step 2: Run Deployed DB Migrations

What it does: invokes the backend Lambda internal migration event.
Target service: AWS Lambda function `leaseflow-dev-backend`.

```bash
cd /mnt/c/Repos/LeaseFlow
cat > migration-payload.json <<'JSON'
{"source":"leaseflow.internal","detail-type":"run_db_migrations","detail":{}}
JSON

aws lambda invoke \
  --region "$AWS_REGION" \
  --function-name "$BACKEND_FUNCTION" \
  --cli-binary-format raw-in-base64-out \
  --payload fileb://migration-payload.json \
  migration-response.json

jq '{statusCode, body}' migration-response.json
```

Expected result:

- `statusCode` is `200`.
- Response body includes migration revision fields.
- Do not capture DB credentials or connection strings.

## Step 3: Check Public Health Route

What it does: calls the unauthenticated health endpoint through API Gateway.
Target service: Amazon API Gateway HTTP API.

```bash
curl -sS -i "$API_URL/health"
```

Expected result:

- HTTP status is `200`.
- Response body is safe to capture.

## Step 4: Create Temporary Cognito Smoke User

What it does: creates a temporary Cognito user with a tenant claim and obtains an
ID token for protected API calls.
Target service: Amazon Cognito user pool.

```bash
export TEST_STAMP=$(date -u +%Y%m%d%H%M%S)
export TEST_EMAIL="smoke-${TEST_STAMP}@example.com"
export TEST_PASSWORD='LeaseFlow123!'
export TEST_TENANT="smoke-tenant-${TEST_STAMP}"

aws cognito-idp admin-create-user \
  --user-pool-id "$USER_POOL_ID" \
  --username "$TEST_EMAIL" \
  --user-attributes \
    Name=email,Value="$TEST_EMAIL" \
    Name=email_verified,Value=true \
    Name=custom:tenant_id,Value="$TEST_TENANT" \
  --message-action SUPPRESS

aws cognito-idp admin-set-user-password \
  --user-pool-id "$USER_POOL_ID" \
  --username "$TEST_EMAIL" \
  --password "$TEST_PASSWORD" \
  --permanent

export ID_TOKEN=$(
  aws cognito-idp admin-initiate-auth \
    --user-pool-id "$USER_POOL_ID" \
    --client-id "$APP_CLIENT_ID" \
    --auth-flow ADMIN_USER_PASSWORD_AUTH \
    --auth-parameters USERNAME="$TEST_EMAIL",PASSWORD="$TEST_PASSWORD" \
    --query 'AuthenticationResult.IdToken' \
    --output text
)
```

Expected result:

- Cognito user is created.
- `$ID_TOKEN` is populated.
- Do not echo or store `$ID_TOKEN`, `$TEST_PASSWORD`, `$TEST_EMAIL`, or
  `$TEST_TENANT` in evidence.

## Step 5: Create a Tenant-Scoped Property

What it does: creates a property and verifies client-supplied `tenant_id` is
ignored in favor of the JWT tenant claim.
Target service: LeaseFlow deployed backend API.

```bash
cat > property-request.json <<'JSON'
{
  "tenant_id": "client-supplied-tenant-must-be-ignored",
  "name": "Smoke Property",
  "address": "Smoke Address"
}
JSON

curl -sS \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d @property-request.json \
  "$API_URL/properties" \
  -o property-response.json

export PROPERTY_ID=$(jq -r '.property_id' property-response.json)
jq -e --arg tenant "$TEST_TENANT" '.tenant_id == $tenant and .property_id != null' \
  property-response.json
```

Expected result:

- Check exits successfully.
- Response `tenant_id` matches the Cognito `custom:tenant_id` claim.
- Evidence may say the tenant override check passed, but must not include the
  tenant value or property details.

## Step 6: Create a Lease Due Today

What it does: creates a lease that should be returned by the due-soon reminder
flow.
Target service: LeaseFlow deployed backend API.

```bash
export TODAY=$(date -u +%Y-%m-%d)
export END_DATE=$(date -u -d '+30 days' +%Y-%m-%d)
export RENT_DUE_DAY=$(date -u +%-d)

jq -n \
  --arg property_id "$PROPERTY_ID" \
  --arg resident_name "Smoke Resident" \
  --argjson rent_due_day "$RENT_DUE_DAY" \
  --arg start_date "$TODAY" \
  --arg end_date "$END_DATE" \
  '{
    property_id: $property_id,
    resident_name: $resident_name,
    rent_due_day_of_month: $rent_due_day,
    start_date: $start_date,
    end_date: $end_date
  }' > lease-request.json

curl -sS \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d @lease-request.json \
  "$API_URL/leases" \
  -o lease-response.json

export LEASE_ID=$(jq -r '.lease_id' lease-response.json)
jq -e --arg tenant "$TEST_TENANT" --arg property "$PROPERTY_ID" \
  '.tenant_id == $tenant and .property_id == $property and .lease_id != null' \
  lease-response.json
```

Expected result:

- Check exits successfully.
- Lease is tied to the property created under the same JWT tenant context.

## Step 7: Check Protected List Routes

What it does: verifies protected list routes work with the Cognito ID token.
Target service: LeaseFlow deployed backend API.

```bash
curl -sS \
  -H "Authorization: Bearer $ID_TOKEN" \
  "$API_URL/properties" \
  -o properties-list-response.json

curl -sS \
  -H "Authorization: Bearer $ID_TOKEN" \
  "$API_URL/leases" \
  -o leases-list-response.json

jq -e --arg property "$PROPERTY_ID" '.items | any(.property_id == $property)' \
  properties-list-response.json
jq -e --arg lease "$LEASE_ID" '.items | any(.lease_id == $lease)' \
  leases-list-response.json
```

Expected result:

- Both checks exit successfully.
- Evidence should capture route names and status, not row contents.

## Step 8: Verify Due-Soon Reminder Candidate

What it does: verifies the lease appears as a due-soon reminder candidate.
Target service: LeaseFlow deployed backend API.

```bash
curl -sS \
  -H "Authorization: Bearer $ID_TOKEN" \
  "$API_URL/lease-reminders/due-soon?days=7" \
  -o reminder-candidates-response.json

jq -e --arg lease "$LEASE_ID" '.items | any(.lease_id == $lease)' \
  reminder-candidates-response.json
```

Expected result:

- Check exits successfully.
- This proves live reminder candidate queries use deployed RDS data.

## Step 9: Run Reminder Scan and Read Notification

What it does: invokes the internal reminder scan for the smoke tenant, lists
persisted notifications, and marks one notification as read.
Target service: AWS Lambda and LeaseFlow deployed backend API.

```bash
jq -n \
  --arg tenant "$TEST_TENANT" \
  --arg as_of_date "$TODAY" \
  '{
    source: "leaseflow.internal",
    "detail-type": "scan_due_lease_reminders",
    detail: {
      tenant_id: $tenant,
      days: 7,
      as_of_date: $as_of_date
    }
  }' > reminder-scan-payload.json

aws lambda invoke \
  --region "$AWS_REGION" \
  --function-name "$BACKEND_FUNCTION" \
  --cli-binary-format raw-in-base64-out \
  --payload fileb://reminder-scan-payload.json \
  reminder-scan-response.json

jq -e '.statusCode == 200' reminder-scan-response.json
jq -r '.body | fromjson | {candidate_count, created_count, duplicate_count}' \
  reminder-scan-response.json

curl -sS \
  -H "Authorization: Bearer $ID_TOKEN" \
  "$API_URL/notifications" \
  -o notifications-response.json

export NOTIFICATION_ID=$(
  jq -r --arg lease "$LEASE_ID" \
    '.items[] | select(.lease_id == $lease and .type == "rent_due_soon") | .notification_id' \
    notifications-response.json | head -n 1
)

test -n "$NOTIFICATION_ID"

curl -sS \
  -X PATCH \
  -H "Authorization: Bearer $ID_TOKEN" \
  "$API_URL/notifications/$NOTIFICATION_ID/read" \
  -o notification-read-response.json

jq -e '.read_at != null' notification-read-response.json
```

Expected result:

- Reminder scan Lambda response has `statusCode` `200`.
- A `rent_due_soon` notification exists for the smoke lease.
- Read acknowledgement sets `read_at`.
- Evidence may capture counts and pass/fail status, not notification message
  contents.

## Step 10: Clean Up Cognito User

What it does: deletes the temporary Cognito user used by the smoke test.
Target service: Amazon Cognito user pool.

```bash
aws cognito-idp admin-delete-user \
  --user-pool-id "$USER_POOL_ID" \
  --username "$TEST_EMAIL"
```

Expected result:

- Command exits successfully.
- The temporary Cognito user is removed.

Property, lease, and notification rows are not deleted by this runbook because
the MVP API intentionally has no delete endpoints. If the dev data must be
removed, destroy the dev stack from the same Terraform state after evidence is
captured.

## Step 11: Clean Up Local Smoke Files

What it does: removes local request and response files that may contain
synthetic tenant-scoped values.
Target service: local WSL/Linux working copy.

```bash
rm -f \
  migration-payload.json \
  migration-response.json \
  property-request.json \
  property-response.json \
  lease-request.json \
  lease-response.json \
  properties-list-response.json \
  leases-list-response.json \
  reminder-candidates-response.json \
  reminder-scan-payload.json \
  reminder-scan-response.json \
  notifications-response.json \
  notification-read-response.json

unset ID_TOKEN TEST_PASSWORD TEST_EMAIL TEST_TENANT
```

Expected result:

- Local smoke files are removed.
- Sensitive shell variables are cleared from the active shell.
- No tenant-scoped smoke payloads are accidentally committed.

## Evidence to Capture

Safe evidence:

- Date and operator.
- AWS account ID and region.
- API route names and HTTP status codes.
- Migration invocation status.
- Reminder scan `candidate_count`, `created_count`, and `duplicate_count`.
- Notification read success.
- Cognito cleanup success.
- Follow-up actions.

Forbidden evidence:

- JWTs or Cognito tokens.
- Passwords or SSM values.
- Cognito test user email.
- Tenant IDs.
- Property names or addresses.
- Resident names.
- Notification titles or messages.
- Full DB connection strings.
- Tenant row contents.

## Success Criteria

- Migration event returns `200`.
- `GET /health` returns `200`.
- Cognito test user can authenticate.
- Protected property and lease API calls succeed.
- Client-supplied `tenant_id` is ignored.
- Due-soon reminder candidate appears.
- Reminder scan creates or de-duplicates a notification.
- Notification read flow sets `read_at`.
- Temporary Cognito user is deleted.

## Cost Notes

- This runbook adds no AWS services.
- It creates short-lived Cognito user state and small synthetic DB rows.
- RDS remains the primary dev cost driver.
- Destroy the dev stack the same day if no further deployed testing is needed.

## SAA-C03 Notes

- A successful `terraform apply` does not prove the application can use RDS.
- Private RDS validation should happen through the deployed private Lambda path,
  not by making RDS public.
- SNS alarm targets and CloudWatch alarms are operational signals; smoke tests
  prove a specific deployed application path works.
