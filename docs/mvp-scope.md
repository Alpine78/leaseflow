# LeaseFlow MVP Scope

## In Scope

- Multi-tenant backend with strict application-layer tenant isolation.
- API endpoints for:
  - `GET /health`
  - `POST /properties`
  - `GET /properties`
  - `POST /leases`
  - `GET /leases`
  - `GET /notifications`
- Cognito JWT-based authentication and tenant claim extraction.
- PostgreSQL persistence for domain data and audit logs.
- Internal reminder scan flow for creating due-soon notification records.
- Infrastructure provisioning with Terraform modules.
- Dev-focused deployment architecture on AWS Lambda + API Gateway.

## Data Scope (Initial)

- `properties` table for tenant-owned rental units.
- `leases` table for tenant-owned rental agreements linked to properties.
- lease contract data includes explicit `rent_due_day_of_month` for future reminder workflows.
- `notifications` table for tenant-owned reminder records.
- `audit_logs` table for basic traceability of critical actions.
- `tenant_id` enforced in all tenant-owned rows.

## Security and Operations Scope

- RDS stays private in VPC subnets.
- Lambda runs in VPC and connects to RDS via security groups.
- Secrets/config use SSM Parameter Store SecureString design.
- Structured logs in CloudWatch.
- Least-privilege baseline IAM.

## Out of Scope (Current Phase)

- Complex role hierarchy beyond one landlord user per tenant.
- Email delivery and external notification integrations.
- PostgreSQL Row-Level Security (future hardening).
- NAT Gateway and non-essential managed services.
- Frontend implementation.
