# Demo Client Safe Demo Runbook

## Purpose

Use the local LeaseFlow demo client to show the deployed dev MVP safely and
capture sanitized portfolio evidence.

This runbook is for demo/reviewer use. It is not production monitoring, load
testing, or full deployed smoke validation. For full deployed validation, use
`docs/runbooks/deployed-dev-smoke-test.md`.

## Guardrails

- Run this only in dev.
- Keep RDS private.
- Use synthetic demo data only.
- Do not capture JWTs, passwords, Cognito test emails, tenant IDs, SSM values,
  DB connection strings, or tenant row contents.
- Do not imply that the local demo client is production software.
- Destroy the dev stack after demo use when it is no longer needed.

## Prerequisites

- Dev stack has been deployed from `infra/environments/dev`.
- Lambda artifact is current for the code being demonstrated.
- Local shell has `aws`, `terraform`, and `python` or `python3`.
- `AWS_PROFILE=terraform`
- `AWS_REGION=eu-north-1`
- Local demo client is run from the repository root.

## Step 1: Load Dev Outputs

What it does: reads deployed values needed by the local demo client.
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

- `$API_URL`, `$USER_POOL_ID`, `$APP_CLIENT_ID`, and `$BACKEND_FUNCTION` are populated.
- Do not paste these values into public evidence if they reveal environment details.

If Terraform reports `No outputs found`, the current state does not contain the
dev stack. Apply the stack first or use an explicit AWS lookup path.

## Step 2: Run Deployed DB Migrations

What it does: invokes the backend Lambda internal migration event.
Target service: AWS Lambda function `leaseflow-dev-backend`.

```bash
cd /mnt/c/Repos/LeaseFlow

cat > /tmp/leaseflow-migration-payload.json <<'JSON'
{"source":"leaseflow.internal","detail-type":"run_db_migrations","detail":{}}
JSON

aws lambda invoke \
  --region "$AWS_REGION" \
  --function-name "$BACKEND_FUNCTION" \
  --cli-binary-format raw-in-base64-out \
  --payload fileb:///tmp/leaseflow-migration-payload.json \
  /tmp/leaseflow-migration-response.json

cat /tmp/leaseflow-migration-response.json
```

Expected result:

- Lambda response contains `statusCode` `200`.

`GET /health` can pass even when the RDS schema is missing. Run migrations
before protected property, lease, reminder, or notification actions.

## Step 3: Create Temporary Cognito User And Token

What it does: creates a temporary dev-only Cognito user with a tenant claim.
Target service: Amazon Cognito user pool.

```bash
export DEMO_STAMP=$(date -u +%Y%m%d%H%M%S)
export DEMO_EMAIL="demo-${DEMO_STAMP}@example.com"
export DEMO_PASSWORD='LeaseFlowDemo123!'
export DEMO_TENANT="demo-tenant-${DEMO_STAMP}"

aws cognito-idp admin-create-user \
  --user-pool-id "$USER_POOL_ID" \
  --username "$DEMO_EMAIL" \
  --user-attributes \
    Name=email,Value="$DEMO_EMAIL" \
    Name=email_verified,Value=true \
    Name=custom:tenant_id,Value="$DEMO_TENANT" \
  --message-action SUPPRESS

aws cognito-idp admin-set-user-password \
  --user-pool-id "$USER_POOL_ID" \
  --username "$DEMO_EMAIL" \
  --password "$DEMO_PASSWORD" \
  --permanent

export ID_TOKEN=$(
  aws cognito-idp admin-initiate-auth \
    --user-pool-id "$USER_POOL_ID" \
    --client-id "$APP_CLIENT_ID" \
    --auth-flow ADMIN_USER_PASSWORD_AUTH \
    --auth-parameters USERNAME="$DEMO_EMAIL",PASSWORD="$DEMO_PASSWORD" \
    --query 'AuthenticationResult.IdToken' \
    --output text
)
```

Verify the token shape:

```bash
printf '%s\n' "$ID_TOKEN" | awk -F. '{print NF-1}'
```

Expected result:

- `2`

Copy only the token value into the demo client:

```bash
printf '%s' "$ID_TOKEN"
```

Do not include `Bearer `. Do not capture the token in evidence.

## Step 4: Start The Local Demo Client

What it does: serves the local browser UI and localhost proxy.
Target service: local development machine.

From the repository root:

```bash
make demo-client
```

If `make` is not installed:

```bash
python scripts/demo_client_server.py
```

In WSL:

```bash
python3 scripts/demo_client_server.py
```

Open:

```text
http://127.0.0.1:8765
```

Fill the UI fields:

- API base URL: use `$API_URL`
- ID token: paste `$ID_TOKEN` without `Bearer `
- AWS region: `eu-north-1`
- Backend function: `leaseflow-dev-backend`

## Step 5: Run The Demo Flow

Click the actions in this order:

1. `Health`
2. `Create property`
3. `List properties`
4. `Create lease`
5. `List leases`
6. `Due soon`
7. `Reminder scan`
8. `Notifications`
9. `Mark read`

Safe expected evidence:

```text
GET /health: 200
POST /properties: 201
tenant override check: passed
GET /properties: 200
POST /leases: 201
GET /leases: 200
GET /lease-reminders/due-soon?days=7: 200
reminder scan status: 200
reminder scan candidate_count: <count>
reminder scan created_count: <count>
reminder scan duplicate_count: <count>
GET /notifications: 200
PATCH /notifications/{notification_id}/read: 200
notification read check: passed
```

Tenant isolation explanation for reviewers:

- The demo property request intentionally includes a client-supplied `tenant_id`.
- The backend ignores that value.
- The response is checked against the authenticated Cognito JWT tenant claim.
- The raw tenant value must not be displayed or captured.

## Step 6: Capture Sanitized Evidence

Allowed evidence:

- date
- operator name or role
- branch or commit reference
- AWS account label, not account ID if evidence may become public
- AWS region
- route names and HTTP status codes
- pass/fail checks
- sanitized reminder scan counts
- Cognito cleanup result
- dev stack destroy result or reason for leaving it running

Prohibited evidence:

- JWTs or ID tokens
- passwords
- Cognito test user email
- tenant IDs
- property names or addresses
- resident names
- notification titles or messages
- SSM values
- full DB connection strings
- raw tenant row contents
- screenshots showing sensitive fields

Copyable evidence template:

````markdown
# LeaseFlow Demo Client Evidence - <YYYY-MM-DD>

## Context

- Operator: <operator role or name>
- Branch/commit: <branch or commit>
- AWS account: <account label only>
- Region: <region>
- Demo client runbook: `docs/runbooks/demo-client-safe-demo.md`

## Setup

- Dev stack available: <yes/no>
- Lambda artifact current: <yes/no>
- DB migration event status: <status code>
- Temporary Cognito user created: <yes/no>
- ID token shape check: <passed/failed>

## Demo Results

```text
GET /health: <status>
POST /properties: <status>
tenant override check: <passed/failed>
GET /properties: <status>
POST /leases: <status>
GET /leases: <status>
GET /lease-reminders/due-soon?days=7: <status>
reminder scan status: <status>
reminder scan candidate_count: <count>
reminder scan created_count: <count>
reminder scan duplicate_count: <count>
GET /notifications: <status>
PATCH /notifications/{notification_id}/read: <status>
notification read check: <passed/failed>
```

## Cleanup

- Temporary Cognito user deleted: <yes/no>
- Local token variables unset: <yes/no>
- Dev stack destroyed: <yes/no or documented reason>

## Evidence Hygiene

This evidence intentionally excludes JWTs, passwords, Cognito emails, tenant
IDs, tenant data values, SSM values, and DB connection strings.
````

## Step 7: Cleanup

What it does: deletes the temporary Cognito user.
Target service: Amazon Cognito user pool.

```bash
aws cognito-idp admin-delete-user \
  --user-pool-id "$USER_POOL_ID" \
  --username "$DEMO_EMAIL"
```

Remove local shell values:

```bash
unset ID_TOKEN DEMO_PASSWORD DEMO_EMAIL DEMO_TENANT
rm -f /tmp/leaseflow-migration-payload.json /tmp/leaseflow-migration-response.json
```

Destroy the dev stack if it is not needed:

```bash
cd /mnt/c/Repos/LeaseFlow/infra/environments/dev
terraform destroy -var db_engine_version=15.17
```

## Troubleshooting

`make: command not found`

- Run `python scripts/demo_client_server.py` from the repository root.
- In WSL, run `python3 scripts/demo_client_server.py`.

`No outputs found`

- Terraform state does not contain the deployed dev stack outputs.
- Apply the dev stack first or use an explicit AWS lookup path.

`API base URL must be an https URL`

- Paste the full API Gateway stage URL into the UI.
- It must start with `https://` and include the stage path.

`Token is not a JWT`

- Paste only the ID token.
- Do not include `Bearer `.
- Verify `printf '%s\n' "$ID_TOKEN" | awk -F. '{print NF-1}'` returns `2`.

`Incorrect username or password`

- Confirm `admin-set-user-password` was run after `admin-create-user`.
- Confirm `DEMO_EMAIL`, `DEMO_PASSWORD`, `USER_POOL_ID`, and `APP_CLIENT_ID`
  belong to the same shell/session and Cognito stack.

`Create property` returns `500`

- Check Lambda logs.
- If logs show `relation "properties" does not exist`, run the deployed DB
  migration event before retrying.

`Reminder scan` fails

- Confirm the local server process has AWS CLI access through the intended
  profile/environment.
- Confirm AWS region is `eu-north-1`.
- Confirm backend function is `leaseflow-dev-backend`.
