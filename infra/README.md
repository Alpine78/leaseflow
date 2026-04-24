# LeaseFlow Infrastructure

Terraform code is split into reusable modules and environment composition.

## Layout

- `bootstrap/terraform_state`: S3 bucket used by Terraform remote state.
- `modules/network`: VPC, private subnets, Lambda/RDS security groups.
- `modules/rds_postgres`: private PostgreSQL instance and subnet group.
- `modules/cognito`: user pool, app client, and managed Hosted UI domain.
- `modules/frontend_hosting`: private S3 bucket and CloudFront distribution for the SPA.
- `modules/lambda_backend`: backend Lambda function, IAM role, log group.
- `modules/reminder_scheduler`: EventBridge Scheduler + IAM role for daily reminder scans.
- `modules/api_http`: HTTP API, JWT authorizer, route wiring.
- `environments/dev`: MVP dev environment composition.

## Why this shape

- Keeps module interfaces clear.
- Makes dev/prod split straightforward later.
- Preserves low-cost defaults and avoids NAT Gateway.
- Gives the dev environment a remote encrypted Terraform state path with locking.
- The Terraform RDS environment is for deployed AWS verification, not for everyday backend development.
- Normal backend development can use local PostgreSQL in WSL to avoid leaving billable AWS resources running.

## Browser frontend foundation

The dev stack includes browser auth, browser CORS, and a hosted SPA path for
the real frontend.

- Cognito app client is configured for Hosted UI OAuth authorization code flow.
- Cognito uses a managed domain prefix that you must set explicitly in
  `terraform.tfvars`.
- API Gateway HTTP API allows browser calls only from approved origins.
- Default local frontend origin is `http://localhost:5173`.
- Hosted frontend origin is the dev CloudFront distribution URL.
- `allow_credentials = false`; browser calls use bearer tokens, not cookies.
- Terraform creates the hosting bucket/distribution; `aws s3 sync` uploads
  built frontend assets.
- The existing `demo-client` remains a separate local demo/operator tool.

## DB password handling

- The dev environment now generates the RDS master password in Terraform.
- Terraform stores the generated password in AWS Systems Manager Parameter Store as a `SecureString`.
- Lambda reads the password from `DB_PASSWORD_SSM_PARAM` at runtime instead of receiving a plaintext password environment variable.
- The password still exists in Terraform state because both `aws_db_instance.password` and `aws_ssm_parameter.value` are stored there by the current Terraform/provider model.
- Treat Terraform state bucket access as sensitive access.

## Remote Terraform state bootstrap

The dev environment supports an S3 backend with native S3 lockfile locking.

Bootstrap creates only the Terraform state bucket. It does not create the
LeaseFlow dev application stack.

What it does: creates the S3 bucket used for encrypted Terraform remote state.
Target service: Amazon S3.

```bash
cd infra/bootstrap/terraform_state
export AWS_PROFILE=terraform
export AWS_REGION=eu-north-1
terraform init
terraform apply
terraform output -raw dev_backend_config > ../../environments/dev/backend.hcl
```

`backend.hcl` is ignored by Git and must not be committed. It contains
account-specific backend configuration.

The generated dev backend config uses:

- `bucket`: the bootstrap state bucket.
- `key`: `leaseflow/dev/terraform.tfstate`.
- `region`: `eu-north-1`.
- `encrypt = true`.
- `use_lockfile = true`.

Terraform's S3 lockfile support is used instead of DynamoDB locking. DynamoDB
locking is intentionally not added because current Terraform documentation marks
it as deprecated.

### Migrate an existing local dev state

If `infra/environments/dev/terraform.tfstate` already contains the current dev
stack, migrate it manually after `backend.hcl` exists.

What it does: migrates existing dev Terraform state into the configured S3 backend.
Target service: Terraform S3 backend.

```bash
cd infra/environments/dev
terraform init -backend-config=backend.hcl -migrate-state
terraform validate
```

Do not delete the local state file until migration is confirmed. After migration,
use the same `backend.hcl` for future `plan`, `apply`, and `destroy` commands.

If the dev stack was already destroyed and local state is intentionally empty,
the same backend init path creates a fresh remote state backend for the next
apply.

### Remote state safety rules

- Do not commit `backend.hcl`.
- Do not commit `.tfstate` files or Terraform plans.
- Do not delete the remote state bucket casually.
- Keep bucket versioning enabled so accidental state overwrites are recoverable.
- Restrict state bucket access because state may include sensitive values.
- Remote state improves collaboration and recovery, but it does not make the
  workload production-ready by itself.

## First Dev Preflight

Use this manual preflight before the first dev `terraform apply`.

The goal is to:

- build a Linux-compatible Lambda zip in WSL
- verify AWS credentials work inside WSL
- run a real `terraform init` / `validate` / `plan` before creating dev resources

This preflight intentionally keeps:

- local reproducible artifact packaging
- remote Terraform state configuration through `backend.hcl`
- no dev stack `terraform apply`

### Prerequisites

- WSL is available on the Windows machine.
- Python `3.12` is available in WSL to match the Lambda runtime.
- `python3.12-full`, `python3.12-venv`, `make`, `rsync`, and `zip` are installed in WSL.
- Terraform is installed in WSL.
- AWS credentials already work in WSL via environment variables or a configured profile.

### 1. Prepare a Linux-side working copy

If the repository lives under `/mnt/c/...`, create a working copy inside the Linux filesystem before building. This avoids `venv` and packaging permission problems on the mounted Windows drive.

```bash
sudo apt update
sudo apt install -y python3.12-full python3.12-venv make rsync zip
mkdir -p ~/leaseflow-preflight
rsync -a --delete /mnt/c/Repos/LeaseFlow/ ~/leaseflow-preflight/ \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude '.venv-wsl/' \
  --exclude 'dist/' \
  --exclude '__pycache__/'
```

### 2. Build the Lambda deployment zip in WSL

Run these commands from the Linux-side working copy:

```bash
cd ~/leaseflow-preflight
make build-lambda-artifact
```

Terraform expects the Lambda artifact at `dist/leaseflow-backend.zip`, which matches the current dev variable default.

### 3. Sanity-check the artifact

Before running Terraform, verify that the zip exists and contains the backend package plus vendored dependencies:

```bash
cd ~/leaseflow-preflight
test -f dist/leaseflow-backend.zip
unzip -l dist/leaseflow-backend.zip | grep "alembic.ini"
unzip -l dist/leaseflow-backend.zip | grep "migrations/env.py"
unzip -l dist/leaseflow-backend.zip | grep "migrations/versions/"
unzip -l dist/leaseflow-backend.zip | grep "app/"
unzip -l dist/leaseflow-backend.zip | grep "boto3/"
```

### 4. Run the Terraform preflight in WSL

Run the Terraform checks from the dev environment directory:

```bash
cd ~/leaseflow-preflight/infra/environments/dev
cp terraform.tfvars.example terraform.tfvars
test -f backend.hcl || cp backend.hcl.example backend.hcl
grep -q "<aws-account-id>" backend.hcl && echo "Replace backend.hcl bucket with the real bootstrap output first." && exit 1
grep -q "replace-with-a-unique-dev-prefix" terraform.tfvars && echo "Replace cognito_hosted_ui_domain_prefix with a globally unique value first." && exit 1
export AWS_PROFILE=terraform
aws sts get-caller-identity
terraform init -backend-config=backend.hcl
terraform validate
terraform plan
```

### Notes

- Do not run dev stack `terraform apply` as part of this preflight.
- Replace the placeholder bucket in `backend.hcl` with the real bootstrap output
  before using remote state.
- Replace the placeholder `cognito_hosted_ui_domain_prefix` in `terraform.tfvars`
  with a globally unique value before planning or applying the dev stack.
- WSL is used here because the Lambda zip needs Linux-compatible dependencies.
- Use a non-root AWS profile for Terraform work. Do not use the AWS account root profile for preflight or deployment tasks.

## CI Terraform checks

CI runs Terraform checks without AWS credentials.

- `terraform fmt -check -recursive infra` checks formatting.
- `infra/environments/dev` runs `terraform init -backend=false` and `terraform validate`.
- Modules with `.tftest.hcl` coverage run `terraform init -backend=false` and `terraform test`.
- Module tests use mocked providers and do not create AWS resources.
- `modules/rds_postgres` is excluded until it has `.tftest.hcl` coverage.

## Dev cost expectation

- Check AWS Billing before the first `terraform apply`.
- If your account has no Free Tier coverage or credits remaining, treat the dev environment as billable from the start.
- The primary expected cost driver in the current dev stack is RDS PostgreSQL:
  - `db.t3.micro`
  - `20 GB` allocated storage
  - automated backups
- API Gateway, Lambda, Cognito, SSM Parameter Store, and CloudWatch are still real AWS resources, but for light learning use they are expected to be smaller cost contributors than RDS.

## Apply and destroy rule

- Use `terraform apply` only when you are ready to test the deployed AWS environment.
- If you are done testing and do not need the stack running, destroy it the same day.
- Do not leave the dev stack running "just in case" when the goal is learning or short-lived verification.

## Safe destroy workflow

- Use the same working copy and Terraform backend config that created the resources.
- Use the same AWS profile and region that were used during `apply`.
- Do not delete Terraform state before destroying the environment.
- The current dev RDS config uses `skip_final_snapshot = true`, so destroying the stack will permanently delete the dev database contents.

```bash
cd infra/environments/dev
terraform init -backend-config=backend.hcl
terraform plan -destroy -out=tfdestroy
terraform apply tfdestroy
```

Quick checks before destroy:

- verify the active AWS account with `aws sts get-caller-identity`
- verify the intended region
- review the destroy plan before applying it

## RDS engine version note

- RDS engine-version availability is region-specific and changes over time.
- The current dev example pins PostgreSQL `15.17` for `eu-north-1`.
- If `terraform apply` fails with `InvalidParameterCombination` for the DB engine version, query AWS before changing Terraform:

```bash
aws rds describe-db-engine-versions --engine postgres --region eu-north-1 \
  --query 'DBEngineVersions[].EngineVersion' --output text
```

## Commands

```bash
cd infra
terraform fmt -recursive
cd environments/dev
terraform init -backend-config=backend.hcl
terraform plan
```

## Upload hosted frontend assets

Run this after the dev stack exists and `frontend_cloudfront_url` is present in
Terraform outputs.

What it does: builds the local frontend bundle and uploads it to the hosted dev
SPA bucket.
Target service: S3 frontend hosting bucket.

```bash
cd infra/environments/dev
export FRONTEND_BUCKET=$(terraform output -raw frontend_bucket_name)
export FRONTEND_DISTRIBUTION_ID=$(terraform output -raw frontend_cloudfront_distribution_id)

cd ../../../frontend
npm run build
aws s3 sync dist/ "s3://${FRONTEND_BUCKET}/" --delete
```

What it does: invalidates CloudFront so the latest uploaded SPA shell is served.
Target service: CloudFront hosted frontend distribution.

```bash
aws cloudfront create-invalidation \
  --distribution-id "$FRONTEND_DISTRIBUTION_ID" \
  --paths "/*"
```

For a real dev deployment, prefer saving the plan first:

```bash
terraform plan -out=tfplan
terraform apply tfplan
```

## Run deployed DB migrations

When the dev stack is already deployed but the private RDS schema is missing, use the backend Lambda's internal migration event.

Build and deploy a fresh Lambda artifact first so the zip contains both `alembic.ini` and `migrations/`.

```bash
make build-lambda-artifact
```

Then invoke the migration path directly:

```bash
cd ~/leaseflow-preflight
cat > migration-payload.json <<'JSON'
{"source":"leaseflow.internal","detail-type":"run_db_migrations","detail":{}}
JSON

export AWS_PROFILE=terraform
aws lambda invoke \
  --region eu-north-1 \
  --function-name leaseflow-dev-backend \
  --cli-binary-format raw-in-base64-out \
  --payload fileb://migration-payload.json \
  migration-response.json

cat migration-response.json
aws logs tail /aws/lambda/leaseflow-dev-backend --since 10m --region eu-north-1 --format short
```

Expected result:

- `statusCode` is `200`
- response body includes `target_revision`, `previous_revision`, and `current_revision`
- after a successful migration run, protected API smoke tests should no longer fail with missing table errors such as `relation "properties" does not exist`

For the full deployed dev smoke path, use `docs/runbooks/deployed-dev-smoke-test.md`.

For a shorter portfolio or interview walkthrough of the same deployed MVP path,
use `docs/portfolio-demo-flow.md`.
