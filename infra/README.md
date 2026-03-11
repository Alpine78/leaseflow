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

## Commands

```bash
cd infra/environments/dev
terraform init
terraform fmt -recursive
terraform plan
```
