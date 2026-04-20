# LeaseFlow MVP Demo Flow

## Purpose

Use this document when you want to show LeaseFlow to a reviewer, interviewer,
or developer audience in 5 to 10 minutes.

This is a presentation-friendly walkthrough, not a full operator validation
runbook. For full deployed verification and evidence capture, use
`docs/runbooks/deployed-dev-smoke-test.md`.

If you want a local browser helper instead of manually running each `curl`
command, start the local demo client:

```bash
make demo-client
```

If `make` is not installed, run this from the repository root instead:

```bash
python scripts/demo_client_server.py
```

Then open `http://127.0.0.1:8765`. The client uses a localhost proxy because
the deployed HTTP API is not configured as a browser product API with CORS.
See `demo-client/README.md` for the browser-client setup checklist, including
DB migrations, temporary Cognito user creation, token verification, and cleanup.
For sanitized portfolio evidence capture, use
`docs/runbooks/demo-client-safe-demo.md`.

## Audience and Demo Goal

Audience:

- software developers
- cloud reviewers
- interviewers
- portfolio viewers

Goal:

- show the MVP works end to end on AWS
- explain tenant isolation clearly
- show the reminder and notification path
- keep the demo short and safe for recording or screenshots

## Guardrails

- Run this only in dev.
- Keep RDS private.
- Do not show JWTs, passwords, tenant IDs, or test emails on screen.
- Do not capture property names, addresses, resident names, or notification
  message text in slides or screenshots.
- Use synthetic demo data only.
- If the stack is no longer needed after the demo, destroy it the same day.

## Prerequisites

- WSL/Linux shell with `aws`, `terraform`, `curl`, and `python3`.
- Lambda artifact built with `make build-lambda-artifact`.
- `AWS_PROFILE=terraform`
- `AWS_REGION=eu-north-1`
- Branch and deployed code are in the state you want to present.

## Before the Live Demo

Do these steps before screen sharing if you want the live demo itself to stay
short.

### 1. Confirm the dev stack exists

What to say:

`This MVP runs on API Gateway, Lambda, Cognito, and private RDS managed by Terraform.`

Command:

```bash
cd /mnt/c/Repos/LeaseFlow/infra/environments/dev
export AWS_PROFILE=terraform
export AWS_REGION=eu-north-1

terraform output -raw api_stage_invoke_url
```

If that command fails, apply the stack first:

```bash
terraform apply -var db_engine_version=15.17
```

### 2. Load deployed outputs

What to say:

`I load only the deployed values I need for the demo: the API URL and Cognito identifiers.`

Command:

```bash
export API_URL=$(terraform output -raw api_stage_invoke_url)
export USER_POOL_ID=$(terraform output -raw cognito_user_pool_id)
export APP_CLIENT_ID=$(terraform output -raw cognito_user_pool_client_id)
export BACKEND_FUNCTION=leaseflow-dev-backend
export DEMO_DIR=$(mktemp -d)
```

### 3. Run the deployed migration path

What to say:

`A successful deploy is not enough. I also verify that the deployed Lambda can reach the private database and run migrations.`

Command:

```bash
cd /mnt/c/Repos/LeaseFlow
cat > "$DEMO_DIR/migration-payload.json" <<'JSON'
{"source":"leaseflow.internal","detail-type":"run_db_migrations","detail":{}}
JSON

aws lambda invoke \
  --region "$AWS_REGION" \
  --function-name "$BACKEND_FUNCTION" \
  --cli-binary-format raw-in-base64-out \
  --payload fileb://"$DEMO_DIR/migration-payload.json" \
  "$DEMO_DIR/migration-response.json" >/dev/null

python3 - "$DEMO_DIR/migration-response.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    print(f"migration_status={json.load(handle)['statusCode']}")
PY
```

Expected result:

- `migration_status=200`

### 4. Create a temporary Cognito demo user and get an ID token

What to say:

`For the protected routes I use a temporary Cognito user. The important part is that the backend gets tenant context from the Cognito JWT claim, not from the request body.`

Command:

```bash
export DEMO_STAMP=$(date -u +%Y%m%d%H%M%S)
export DEMO_EMAIL="demo-${DEMO_STAMP}@example.com"
export DEMO_PASSWORD=$(python3 - <<'PY'
import secrets
print(f"Lf!{secrets.token_urlsafe(12)}9A")
PY
)
export DEMO_TENANT="demo-tenant-${DEMO_STAMP}"

aws cognito-idp admin-create-user \
  --user-pool-id "$USER_POOL_ID" \
  --username "$DEMO_EMAIL" \
  --user-attributes \
    Name=email,Value="$DEMO_EMAIL" \
    Name=email_verified,Value=true \
    Name=custom:tenant_id,Value="$DEMO_TENANT" \
  --message-action SUPPRESS >/dev/null

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

Expected result:

- `ID_TOKEN` is populated.
- Do not echo `ID_TOKEN`, `DEMO_PASSWORD`, `DEMO_EMAIL`, or `DEMO_TENANT`.

## Live Demo Sequence

### 1. Health check

What to say:

`First I verify the public health route through API Gateway. This proves the deployed HTTP entry point is alive.`

Command:

```bash
curl -sS -o /dev/null -w "GET /health => %{http_code}\n" "$API_URL/health"
```

Expected result:

- `GET /health => 200`

### 2. Create a property and prove tenant isolation

What to say:

`Now I create a property, but I intentionally send a wrong tenant_id in the request body. The backend should ignore it and use the tenant from the Cognito JWT instead.`

Command:

```bash
cat > "$DEMO_DIR/property-request.json" <<'JSON'
{
  "tenant_id": "client-supplied-tenant-must-be-ignored",
  "name": "Demo Property",
  "address": "Demo Address"
}
JSON

PROPERTY_HTTP=$(curl -sS \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d @"$DEMO_DIR/property-request.json" \
  -o "$DEMO_DIR/property-response.json" \
  -w "%{http_code}" \
  "$API_URL/properties")

export PROPERTY_ID=$(python3 - "$DEMO_DIR/property-response.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    print(json.load(handle)["property_id"])
PY
)

python3 - "$DEMO_DIR/property-response.json" "$DEMO_TENANT" "$PROPERTY_HTTP" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)
assert data["tenant_id"] == sys.argv[2]
print(f"POST /properties => {sys.argv[3]}")
print("tenant_override_check=passed")
PY
```

Expected result:

- `POST /properties => 201`
- `tenant_override_check=passed`

### 3. Create a lease due today

What to say:

`Next I create a lease under that property. I set the due day to today so the reminder flow can be demonstrated immediately.`

Command:

```bash
export TODAY=$(date -u +%Y-%m-%d)
export END_DATE=$(date -u -d '+30 days' +%Y-%m-%d)
export RENT_DUE_DAY=$(date -u +%-d)

python3 - "$DEMO_DIR/lease-request.json" "$PROPERTY_ID" "$RENT_DUE_DAY" "$TODAY" "$END_DATE" <<'PY'
import json
import sys

path, property_id, rent_due_day, start_date, end_date = sys.argv[1:]
with open(path, "w", encoding="utf-8") as handle:
    json.dump(
        {
            "property_id": property_id,
            "resident_name": "Demo Resident",
            "rent_due_day_of_month": int(rent_due_day),
            "start_date": start_date,
            "end_date": end_date,
        },
        handle,
    )
PY

LEASE_HTTP=$(curl -sS \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d @"$DEMO_DIR/lease-request.json" \
  -o "$DEMO_DIR/lease-response.json" \
  -w "%{http_code}" \
  "$API_URL/leases")

export LEASE_ID=$(python3 - "$DEMO_DIR/lease-response.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    print(json.load(handle)["lease_id"])
PY
)

echo "POST /leases => $LEASE_HTTP"
```

Expected result:

- `POST /leases => 201`

### 4. Show the tenant-scoped list routes

What to say:

`These list routes are tenant-scoped by design. I only see the property and lease belonging to the authenticated tenant.`

Command:

```bash
PROPERTIES_HTTP=$(curl -sS \
  -H "Authorization: Bearer $ID_TOKEN" \
  -o "$DEMO_DIR/properties-list-response.json" \
  -w "%{http_code}" \
  "$API_URL/properties")

LEASES_HTTP=$(curl -sS \
  -H "Authorization: Bearer $ID_TOKEN" \
  -o "$DEMO_DIR/leases-list-response.json" \
  -w "%{http_code}" \
  "$API_URL/leases")

python3 - "$DEMO_DIR/properties-list-response.json" "$DEMO_DIR/leases-list-response.json" "$PROPERTY_ID" "$LEASE_ID" "$PROPERTIES_HTTP" "$LEASES_HTTP" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    properties = json.load(handle)
with open(sys.argv[2], encoding="utf-8") as handle:
    leases = json.load(handle)

assert any(item["property_id"] == sys.argv[3] for item in properties["items"])
assert any(item["lease_id"] == sys.argv[4] for item in leases["items"])
print(f"GET /properties => {sys.argv[5]}")
print("property_list_check=passed")
print(f"GET /leases => {sys.argv[6]}")
print("lease_list_check=passed")
PY
```

Expected result:

- `GET /properties => 200`
- `property_list_check=passed`
- `GET /leases => 200`
- `lease_list_check=passed`

### 5. Show the due-soon reminder candidate query

What to say:

`This route asks the application which leases are due soon based on live RDS data. It does not yet depend on an external notification channel.`

Command:

```bash
REMINDER_HTTP=$(curl -sS \
  -H "Authorization: Bearer $ID_TOKEN" \
  -o "$DEMO_DIR/reminder-candidates-response.json" \
  -w "%{http_code}" \
  "$API_URL/lease-reminders/due-soon?days=7")

python3 - "$DEMO_DIR/reminder-candidates-response.json" "$LEASE_ID" "$REMINDER_HTTP" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)
assert any(item["lease_id"] == sys.argv[2] for item in data["items"])
print(f"GET /lease-reminders/due-soon?days=7 => {sys.argv[3]}")
print("reminder_candidate_check=passed")
PY
```

Expected result:

- `GET /lease-reminders/due-soon?days=7 => 200`
- `reminder_candidate_check=passed`

### 6. Run the internal reminder scan

What to say:

`Now I trigger the internal reminder scan. This is the background path that turns a due-soon candidate into a persisted notification.`

Command:

```bash
python3 - "$DEMO_DIR/reminder-scan-payload.json" "$DEMO_TENANT" "$TODAY" <<'PY'
import json
import sys

path, tenant_id, as_of_date = sys.argv[1:]
with open(path, "w", encoding="utf-8") as handle:
    json.dump(
        {
            "source": "leaseflow.internal",
            "detail-type": "scan_due_lease_reminders",
            "detail": {
                "tenant_id": tenant_id,
                "days": 7,
                "as_of_date": as_of_date,
            },
        },
        handle,
    )
PY

aws lambda invoke \
  --region "$AWS_REGION" \
  --function-name "$BACKEND_FUNCTION" \
  --cli-binary-format raw-in-base64-out \
  --payload fileb://"$DEMO_DIR/reminder-scan-payload.json" \
  "$DEMO_DIR/reminder-scan-response.json" >/dev/null

python3 - "$DEMO_DIR/reminder-scan-response.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    outer = json.load(handle)
body = json.loads(outer["body"])
print(f"reminder_scan_status={outer['statusCode']}")
print(f"candidate_count={body['candidate_count']}")
print(f"created_count={body['created_count']}")
print(f"duplicate_count={body['duplicate_count']}")
PY
```

Expected result:

- `reminder_scan_status=200`
- safe counts are shown

### 7. Show the notification and mark it read

What to say:

`The reminder scan created a persisted notification, and now I acknowledge it through the API.`

Command:

```bash
NOTIFICATIONS_HTTP=$(curl -sS \
  -H "Authorization: Bearer $ID_TOKEN" \
  -o "$DEMO_DIR/notifications-response.json" \
  -w "%{http_code}" \
  "$API_URL/notifications")

export NOTIFICATION_ID=$(python3 - "$DEMO_DIR/notifications-response.json" "$LEASE_ID" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)
for item in data["items"]:
    if item["lease_id"] == sys.argv[2] and item["type"] == "rent_due_soon":
        print(item["notification_id"])
        break
PY
)

NOTIFICATION_READ_HTTP=$(curl -sS \
  -X PATCH \
  -H "Authorization: Bearer $ID_TOKEN" \
  -o "$DEMO_DIR/notification-read-response.json" \
  -w "%{http_code}" \
  "$API_URL/notifications/$NOTIFICATION_ID/read")

python3 - "$DEMO_DIR/notification-read-response.json" "$NOTIFICATIONS_HTTP" "$NOTIFICATION_READ_HTTP" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)
assert data["read_at"] is not None
print(f"GET /notifications => {sys.argv[2]}")
print(f"PATCH /notifications/{{notification_id}}/read => {sys.argv[3]}")
print("notification_read_check=passed")
PY
```

Expected result:

- `GET /notifications => 200`
- `PATCH /notifications/{notification_id}/read => 200`
- `notification_read_check=passed`

## Cleanup

### 1. Delete the temporary Cognito user

What to say:

`I always remove the temporary demo identity after the presentation.`

Command:

```bash
aws cognito-idp admin-delete-user \
  --user-pool-id "$USER_POOL_ID" \
  --username "$DEMO_EMAIL"
```

### 2. Remove local temp files and secrets from the shell

Command:

```bash
rm -rf "$DEMO_DIR"
unset ID_TOKEN DEMO_PASSWORD DEMO_EMAIL DEMO_TENANT
```

### 3. Decide whether to destroy the dev stack

What to say:

`If I do not need the environment anymore, I destroy it the same day so dev verification does not turn into background AWS cost.`

Command:

```bash
cd /mnt/c/Repos/LeaseFlow/infra/environments/dev
terraform destroy -var db_engine_version=15.17
```

Use destroy when:

- the presentation is over
- no more deployed testing is needed that day

Keep the stack only if:

- you have another planned validation session immediately after
- you explicitly accept the short-lived dev cost

## Short Closing Script

If you need one short closing line for the demo:

`This shows the MVP path working on AWS: Cognito carries tenant identity, Lambda enforces tenant scope, data lives in private RDS, reminder candidates become persisted notifications, and the environment can be cleaned up after the demo.`
