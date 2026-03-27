# LeaseFlow Infrastructure

Terraform code is split into reusable modules and environment composition.

## Layout

- `modules/network`: VPC, private subnets, Lambda/RDS security groups.
- `modules/rds_postgres`: private PostgreSQL instance and subnet group.
- `modules/cognito`: user pool and app client.
- `modules/lambda_backend`: backend Lambda function, IAM role, log group.
- `modules/api_http`: HTTP API, JWT authorizer, route wiring.
- `environments/dev`: MVP dev environment composition.

## Why this shape

- Keeps module interfaces clear.
- Makes dev/prod split straightforward later.
- Preserves low-cost defaults and avoids NAT Gateway.

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
find dist/lambda-build -type d -name "__pycache__" -prune -exec rm -rf {} +
(cd dist/lambda-build && zip -r ../leaseflow-backend.zip .)
```

Terraform expects the Lambda artifact at `dist/leaseflow-backend.zip`, which matches the current dev variable default.

### 3. Sanity-check the artifact

Before running Terraform, verify that the zip exists and contains the backend package plus vendored dependencies:

```bash
cd ~/leaseflow-preflight
test -f dist/leaseflow-backend.zip
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

## Commands

```bash
cd infra
terraform fmt -recursive
cd environments/dev
terraform init
terraform plan
```
