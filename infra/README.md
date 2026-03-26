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

## Commands

```bash
cd infra
terraform fmt -recursive
cd environments/dev
terraform init
terraform plan
```
