# LeaseFlow Infrastructure

Terraform code is split into reusable modules and environment composition.

## Layout

- `modules/network`: VPC, private subnets, Lambda/RDS security groups.
- `modules/rds_postgres`: private PostgreSQL instance and subnet group.
- `modules/cognito`: user pool and app client.
- `modules/lambda_backend`: backend Lambda function, IAM role, log group.
- `modules/reminder_scheduler`: EventBridge Scheduler + IAM role for daily reminder scans.
- `modules/api_http`: HTTP API, JWT authorizer, route wiring.
- `environments/dev`: MVP dev environment composition.

## Why this shape

- Keeps module interfaces clear.
- Makes dev/prod split straightforward later.
- Preserves low-cost defaults and avoids NAT Gateway.
- The Terraform RDS environment is for deployed AWS verification, not for everyday backend development.
- Normal backend development can use local PostgreSQL in WSL to avoid leaving billable AWS resources running.

## DB password handling

- The dev environment now generates the RDS master password in Terraform.
- Terraform stores the generated password in AWS Systems Manager Parameter Store as a `SecureString`.
- Lambda reads the password from `DB_PASSWORD_SSM_PARAM` at runtime instead of receiving a plaintext password environment variable.
- The password still exists in Terraform state because both `aws_db_instance.password` and `aws_ssm_parameter.value` are stored there by the current Terraform/provider model.

## First Dev Preflight

Use this manual preflight before the first dev `terraform apply`.

The goal is to:

- build a Linux-compatible Lambda zip in WSL
- verify AWS credentials work inside WSL
- run a real `terraform init` / `validate` / `plan` without creating resources yet

This preflight intentionally keeps:

- local artifact packaging
- local Terraform state
- no automation script or Make target
- no `terraform apply`

### Prerequisites

- WSL is available on the Windows machine.
- Python `3.12` is available in WSL to match the Lambda runtime.
- `python3.12-full`, `python3.12-venv`, and `rsync` are installed in WSL.
- Terraform is installed in WSL.
- AWS credentials already work in WSL via environment variables or a configured profile.

### 1. Prepare a Linux-side working copy

If the repository lives under `/mnt/c/...`, create a working copy inside the Linux filesystem before building. This avoids `venv` and packaging permission problems on the mounted Windows drive.

```bash
sudo apt update
sudo apt install -y python3.12-full python3.12-venv rsync
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
rm -rf dist/lambda-build dist/leaseflow-backend.zip .venv
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install ./backend -t dist/lambda-build
cp backend/alembic.ini dist/lambda-build/alembic.ini
rsync -a backend/migrations/ dist/lambda-build/migrations/
find dist/lambda-build -type d -name "__pycache__" -prune -exec rm -rf {} +
(cd dist/lambda-build && zip -r ../leaseflow-backend.zip .)
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
export AWS_PROFILE=terraform
aws sts get-caller-identity
terraform init
terraform validate
terraform plan
```

### Notes

- Do not run `terraform apply` as part of this preflight.
- Remote state is intentionally deferred to a later hardening step.
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

- Use the same working copy and the same Terraform state that created the resources.
- Use the same AWS profile and region that were used during `apply`.
- Do not delete the local Terraform state before destroying the environment.
- The current dev RDS config uses `skip_final_snapshot = true`, so destroying the stack will permanently delete the dev database contents.

```bash
cd infra/environments/dev
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
terraform init
terraform plan
```

For a real dev deployment, prefer saving the plan first:

```bash
terraform plan -out=tfplan
terraform apply tfplan
```

## Run deployed DB migrations

When the dev stack is already deployed but the private RDS schema is missing, use the backend Lambda's internal migration event.

Build and deploy a fresh Lambda artifact first so the zip contains both `alembic.ini` and `migrations/`.

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
