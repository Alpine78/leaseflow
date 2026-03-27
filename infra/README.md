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
