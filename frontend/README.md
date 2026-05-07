# LeaseFlow Frontend

This is the first real browser frontend slice for LeaseFlow.

It is local-first and targets the deployed dev API directly from the browser.
It is separate from `demo-client`, which remains a local portfolio/operator
tool.

## What it includes

- Cognito Hosted UI sign in and sign out
- OAuth authorization code flow with PKCE
- protected browser routes
- authenticated dashboard summary
- properties list, create, and update
- leases list, create, and update
- due-soon reminder candidate list
- persisted notifications list and mark-read action

This slice does not include notification creation, email delivery, custom
domains, or production-ready deploy automation.

## Prerequisites

- Node.js 20+
- npm
- a deployed dev stack with Hosted UI and browser CORS configured
- Terraform and AWS CLI access to the dev stack for reading outputs
- Python 3 for generating temporary browser smoke-test passwords

## Environment

Copy `.env.example` to `.env.local` and fill the values from Terraform outputs.

What it does: writes `frontend/.env.local` from the deployed dev Terraform
outputs.
Target filename/service: `frontend/.env.local`.

```bash
cd /mnt/c/Repos/LeaseFlow
bash scripts/dev/write-frontend-env.sh
```

The manual commands below are useful when troubleshooting individual values.

What it does: reads the deployed API, Cognito, and hosted frontend values as
named lines so the values are easy to copy without mixing them together.
Target filename/service: `infra/environments/dev` / Terraform outputs.

```bash
cd /mnt/c/Repos/LeaseFlow/infra/environments/dev
export AWS_PROFILE=terraform
export AWS_REGION=eu-north-1

export API_URL=$(terraform output -raw api_stage_invoke_url)
export COGNITO_HOSTED_UI=$(terraform output -raw cognito_hosted_ui_base_url)
export COGNITO_CLIENT_ID=$(terraform output -raw cognito_user_pool_client_id)
export FRONTEND_URL=$(terraform output -raw frontend_cloudfront_url)

printf 'API_URL=%s\n' "$API_URL"
printf 'COGNITO_HOSTED_UI=%s\n' "$COGNITO_HOSTED_UI"
printf 'COGNITO_CLIENT_ID=%s\n' "$COGNITO_CLIENT_ID"
printf 'FRONTEND_URL=%s\n' "$FRONTEND_URL"
```

Required env vars:

- `VITE_API_BASE_URL`
- `VITE_COGNITO_HOSTED_UI_BASE_URL`
- `VITE_COGNITO_CLIENT_ID`

What it does: writes the local Vite environment file from the Terraform output
values loaded above.
Target filename/service: `frontend/.env.local`.

```bash
cd /mnt/c/Repos/LeaseFlow/frontend
cat > .env.local <<EOF
VITE_API_BASE_URL=${API_URL}
VITE_COGNITO_HOSTED_UI_BASE_URL=${COGNITO_HOSTED_UI}
VITE_COGNITO_CLIENT_ID=${COGNITO_CLIENT_ID}
EOF
```

The `.env.local` values must match the Terraform outputs exactly. A wrong
`VITE_COGNITO_CLIENT_ID` can make Cognito Hosted UI redirect to
`invalid_request` before the login page is shown.

Restart the Vite dev server after changing `.env.local`; Vite reads these
values at startup. Hosted CloudFront builds embed the same Vite env values at
build time, so hosted validation requires a rebuild, S3 sync, and CloudFront
invalidation after env changes.

## Temporary browser login user

No browser login email/password exists by default. Create a temporary Cognito
user in the deployed dev user pool before browser smoke testing.

What it does: creates a temporary Cognito Hosted UI user and prints only the
local email/password values needed for browser login.
Target service: Amazon Cognito user pool.

```bash
cd /mnt/c/Repos/LeaseFlow
bash scripts/dev/create-demo-user.sh
```

`create-demo-user.sh` creates an empty tenant for manual browser testing. If you
want a ready portfolio/demo tenant with synthetic properties, leases, and
notifications, use the seed script instead:

What it does: creates a temporary Cognito login user and synthetic demo data
through the deployed dev API.
Target service: Amazon Cognito and LeaseFlow deployed dev API.

```bash
cd /mnt/c/Repos/LeaseFlow
bash scripts/dev/seed-demo-data.sh
```

Seeded data is disposable dev/demo data. It is removed when the dev database is
destroyed with the stack.

The manual commands below are useful when troubleshooting user creation.

What it does: loads the Cognito user pool and app client IDs needed for local
operator setup.
Target filename/service: `infra/environments/dev` / Terraform outputs.

```bash
cd /mnt/c/Repos/LeaseFlow/infra/environments/dev
export AWS_PROFILE=terraform
export AWS_REGION=eu-north-1

export USER_POOL_ID=$(terraform output -raw cognito_user_pool_id)
export COGNITO_CLIENT_ID=$(terraform output -raw cognito_user_pool_client_id)
```

What it does: creates a temporary dev-only Cognito user with the required tenant
claim for Hosted UI browser login.
Target service: Amazon Cognito user pool.

```bash
export DEMO_STAMP=$(date -u +%Y%m%d%H%M%S)
export DEMO_EMAIL="browser-demo-${DEMO_STAMP}@example.com"
export DEMO_TENANT="browser-demo-${DEMO_STAMP}"
export DEMO_PASSWORD=$(python3 -c "import secrets,string; chars=string.ascii_letters+string.digits; print('Lf-'+''.join(secrets.choice(chars) for _ in range(18))+'!Aa1')")

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
```

What it does: prints only the local temporary credentials you need to type into
Cognito Hosted UI.
Target service: local terminal only.

```bash
printf 'DEMO_EMAIL=%s\n' "$DEMO_EMAIL"
printf 'DEMO_PASSWORD=%s\n' "$DEMO_PASSWORD"
```

Do not commit or paste the temporary email, password, tenant value, JWTs, or
session storage values into evidence. Cognito passwords cannot be retrieved
later; if you lose the password, set a new one with `admin-set-user-password`.
The browser frontend must still use Hosted UI login, not admin auth APIs.

## Run

What it does: installs frontend dependencies.
Target filename/service: `frontend/package.json`.

```bash
cd frontend
npm ci --ignore-scripts
```

`frontend/.npmrc` sets `ignore-scripts=true`, so dependency install lifecycle
scripts are disabled by default. Explicit project commands such as
`npm run dev`, `npm run lint`, `npm run test`, and `npm run build` still run
intentionally.

What it does: starts the local Vite dev server.
Target filename/service: `frontend/` browser app.

```bash
npm run dev
```

Then open `http://localhost:5173`.

## Hosted dev deploy

Terraform creates the S3 bucket and CloudFront distribution. Frontend asset
upload can be done either with the local operator script or the manual GitHub
Actions workflow. If any `VITE_*` value changes, rebuild and upload the
frontend again because the static assets contain those values.

The manual GitHub Actions workflow is `.github/workflows/deploy-frontend-dev.yml`.
It uses GitHub OIDC, the `dev` GitHub Environment, and non-secret environment
variables copied from Terraform outputs. It does not use static AWS access
keys and does not run Terraform.

Required GitHub Environment `dev` variables:

- `AWS_REGION`
- `FRONTEND_DEPLOY_ROLE_ARN`
- `FRONTEND_BUCKET_NAME`
- `FRONTEND_CLOUDFRONT_DISTRIBUTION_ID`
- `FRONTEND_CLOUDFRONT_URL`
- `VITE_API_BASE_URL`
- `VITE_COGNITO_HOSTED_UI_BASE_URL`
- `VITE_COGNITO_CLIENT_ID`

What it does: prints the required GitHub Environment variables as named lines
from Terraform outputs.
Target service: GitHub Environment `dev` setup reference.

```bash
cd /mnt/c/Repos/LeaseFlow
bash scripts/dev/print-github-frontend-deploy-vars.sh
```

What it does: writes the same variables directly to GitHub Environment `dev`
using `gh variable set`. Values are not printed.
Target service: GitHub repository environment variables.

```bash
cd /mnt/c/Repos/LeaseFlow
bash scripts/dev/set-github-frontend-deploy-vars.sh
```

Use `GITHUB_REPOSITORY` or `GITHUB_ENVIRONMENT` to override the defaults
`Alpine78/leaseflow` and `dev`.

Run the workflow manually with `environment=dev`, `confirm_dev_deploy=true`,
and `invalidation_path=/*`. The local upload path below remains supported for
operator testing and troubleshooting.

If a hosted deploy needs rollback, use
`docs/runbooks/hosted-frontend-deploy-rollback.md`.

What it does: builds and uploads the hosted frontend, then invalidates
CloudFront.
Target service: S3 frontend hosting bucket and CloudFront distribution.

```bash
cd /mnt/c/Repos/LeaseFlow
bash scripts/dev/upload-frontend.sh
```

The manual commands below are useful when troubleshooting hosted upload steps.

What it does: reads hosted frontend deployment outputs.
Target filename/service: `infra/environments/dev` / Terraform outputs.

```bash
cd /mnt/c/Repos/LeaseFlow/infra/environments/dev
export FRONTEND_BUCKET=$(terraform output -raw frontend_bucket_name)
export FRONTEND_DISTRIBUTION_ID=$(terraform output -raw frontend_cloudfront_distribution_id)
export FRONTEND_URL=$(terraform output -raw frontend_cloudfront_url)
```

What it does: builds and uploads the static SPA assets.
Target filename/service: `frontend/dist` / S3 frontend bucket.

```bash
cd /mnt/c/Repos/LeaseFlow/frontend
npm run build
aws s3 sync dist/ "s3://${FRONTEND_BUCKET}/" --delete
```

What it does: clears CloudFront cache after uploading a new SPA build.
Target filename/service: CloudFront hosted frontend distribution.

```bash
aws cloudfront create-invalidation \
  --distribution-id "$FRONTEND_DISTRIBUTION_ID" \
  --paths "/*"
```

Then open the value of `FRONTEND_URL`.

## Hosted UI `invalid_request` checklist

If Cognito redirects to `/error?error=invalid_request` before the login page,
compare the browser authorize URL against Terraform outputs and app client
settings:

- `client_id` exactly matches `terraform output -raw cognito_user_pool_client_id`.
- `redirect_uri` is `http://localhost:5173/auth/callback` for local Vite or
  `${FRONTEND_URL}/auth/callback` for CloudFront.
- `scope` is exactly `openid email profile`.
- Hosted UI base URL exactly matches
  `terraform output -raw cognito_hosted_ui_base_url`.
- Cognito app client has OAuth code flow enabled.
- Cognito app client allows callback and logout URLs for the current origin.
- Cognito app client allows scopes `openid`, `email`, and `profile`.

## Checks

What it does: checks installed frontend dependencies for high-severity npm audit
findings.
Target filename/service: `frontend/package-lock.json`.

```bash
npm audit --audit-level=high
```

What it does: runs the frontend linter.
Target filename/service: `frontend/`.

```bash
npm run lint
```

What it does: runs the frontend test suite.
Target filename/service: `frontend/`.

```bash
npm run test
```

What it does: builds the frontend production bundle.
Target filename/service: `frontend/`.

```bash
npm run build
```

## Security notes

- Browser auth uses Cognito Hosted UI, not admin auth APIs.
- Protected API calls use the Cognito `id_token` because the backend depends on
  `custom:tenant_id`.
- Hosted UI requests `openid email profile` so readable custom attributes can
  be included in the ID token.
- Session state is stored in `sessionStorage`.
- Dependency install lifecycle scripts are disabled by default with
  `ignore-scripts=true`.
- Review `package-lock.json` diffs when adding npm packages, avoid unnecessary
  dependencies, and document any deliberate lifecycle-script exception in the
  PR.
- Do not commit `.env.local`, tokens, tenant IDs, or any real user data.
