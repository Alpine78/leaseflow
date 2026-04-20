# LeaseFlow Demo Client

This is a local portfolio/demo client for the deployed LeaseFlow dev API.

It is not a production frontend.

## Run

From the repository root:

```bash
make demo-client
```

If `make` is not installed, for example in Git Bash, run the server directly:

```bash
python scripts/demo_client_server.py
```

In WSL, use:

```bash
python3 scripts/demo_client_server.py
```

Then open:

```text
http://127.0.0.1:8765
```

Do not run the command from `backend/`; the server expects the repository root.

## Before Using The UI

Run these steps before clicking the protected demo actions.

### 1. Load deployed outputs

```bash
cd /mnt/c/Repos/LeaseFlow/infra/environments/dev
export AWS_PROFILE=terraform
export AWS_REGION=eu-north-1

export API_URL=$(terraform output -raw api_stage_invoke_url)
export USER_POOL_ID=$(terraform output -raw cognito_user_pool_id)
export APP_CLIENT_ID=$(terraform output -raw cognito_user_pool_client_id)
```

If Terraform says `No outputs found`, the current state does not contain the
dev stack. Apply the stack first or use the AWS CLI lookup flow from
`docs/portfolio-demo-flow.md`.

### 2. Run deployed DB migrations

`GET /health` can pass even when the RDS schema is missing. Run migrations
before creating properties or leases.

```bash
cd /mnt/c/Repos/LeaseFlow

cat > /tmp/leaseflow-migration-payload.json <<'JSON'
{"source":"leaseflow.internal","detail-type":"run_db_migrations","detail":{}}
JSON

aws lambda invoke \
  --region "$AWS_REGION" \
  --function-name leaseflow-dev-backend \
  --cli-binary-format raw-in-base64-out \
  --payload fileb:///tmp/leaseflow-migration-payload.json \
  /tmp/leaseflow-migration-response.json

cat /tmp/leaseflow-migration-response.json
```

Expected result: `statusCode` is `200`.

### 3. Create a temporary Cognito user and token

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

Expected result: `2`.

Copy only the token value into the UI:

```bash
printf '%s' "$ID_TOKEN"
```

Do not include `Bearer `.

## Inputs

The UI asks for:

- deployed API base URL
- temporary Cognito ID token
- AWS region, default `eu-north-1`
- backend Lambda function name, default `leaseflow-dev-backend`

The ID token is kept in browser memory and sent only to the local demo server.
Do not paste production tokens.

## Recommended Click Order

1. `Health`
2. `Create property`
3. `List properties`
4. `Create lease`
5. `List leases`
6. `Due soon`
7. `Reminder scan`
8. `Notifications`
9. `Mark read`

If `Create property` returns `500`, check Lambda logs. The most common setup
issue is a missing RDS schema, which is fixed by running the deployed migration
event above.

## Safety

- Use synthetic demo data only.
- Do not screenshot JWTs, passwords, emails, tenant IDs, SSM values, or real tenant data.
- Keep RDS private.
- Destroy the dev stack after demo use when it is not needed.

Cleanup the temporary Cognito user:

```bash
aws cognito-idp admin-delete-user \
  --user-pool-id "$USER_POOL_ID" \
  --username "$DEMO_EMAIL"
```

## Why There Is A Local Server

The deployed HTTP API is not configured as a browser product API with CORS.
The local server lets the browser talk to `localhost` while the server proxies
only the allowlisted demo API calls to the deployed API Gateway.
