# LeaseFlow MVP Scope

## In Scope

- Multi-tenant backend with strict application-layer tenant isolation.
- API endpoints for:
  - `GET /health`
  - `GET /properties`
  - `POST /properties`
  - `PATCH /properties/{property_id}`
  - `GET /leases`
  - `POST /leases`
  - `PATCH /leases/{lease_id}`
  - `GET /lease-reminders/due-soon`
  - `GET /notifications`
  - `PATCH /notifications/{notification_id}/read`
  - `GET /notification-contacts`
  - `POST /notification-contacts`
  - `PATCH /notification-contacts/{contact_id}`
- Cognito JWT-based authentication and tenant claim extraction.
- PostgreSQL persistence for domain data and audit logs.
- Internal reminder scan flow for creating due-soon notification records.
- Disabled-by-default internal notification email delivery worker for persisted
  due reminder notifications.
- EventBridge Scheduler for daily invocation of the internal reminder scan.
- Infrastructure provisioning with Terraform modules.
- Dev-focused deployment architecture on AWS Lambda + API Gateway.
- Real browser frontend slice under `frontend/` with Cognito Hosted UI
  sign-in/sign-out, protected routes, dashboard summaries,
  properties/leases list/create/update flows, due-soon reminder display, and
  notifications list/mark-read plus notification contact management UI.
- Terraform-managed static SPA hosting path with private S3 and CloudFront.
  Hosted asset upload and browser smoke validation remain operator-run release
  validation, not a CI deploy pipeline.

## Data Scope (Current MVP)

- `properties` table for tenant-owned rental units.
- `leases` table for tenant-owned rental agreements linked to properties.
- lease contract data includes explicit `rent_due_day_of_month` for future reminder workflows.
- `notifications` table for tenant-owned reminder records, including nullable `read_at` for read acknowledgment.
- `notification_contacts` table for tenant-owned email recipients.
- `notification_email_deliveries` table for tenant-scoped delivery status,
  retry attempts, sanitized failure codes, and sent timestamps.
- Notification API responses expose safe aggregate delivery summaries without
  recipient addresses, contact IDs, tenant IDs, or raw provider responses.
- `audit_logs` table for basic traceability of critical actions.
- `tenant_id` enforced in all tenant-owned rows.

## Security and Operations Scope

- RDS stays private in VPC subnets.
- Lambda runs in VPC and connects to RDS via security groups.
- Secrets/config use SSM Parameter Store SecureString design.
- Structured logs in CloudWatch.
- Least-privilege baseline IAM.
- Scheduled reminder jobs invoke Lambda through an internal event payload, not a public endpoint.
- Notification email delivery is triggered only by an internal Lambda event and
  remains disabled until SES identity, SMTP credentials, and smoke validation
  are ready.

## Out of Scope (Current Phase)

- Complex role hierarchy beyond one landlord user per tenant.
- Production email readiness and external notification integrations.
- PostgreSQL Row-Level Security implementation. The future hardening path is
  planned in `docs/postgresql-rls-tenant-isolation-hardening.md`.
- NAT Gateway and non-essential managed services.
- Notification creation from the browser.
- Browser-triggered reminder scans or email delivery.
- Recipient-level delivery details in browser responses.
- Custom domain, CI-based frontend deployment, and production readiness.

## Planned Next Notification Phase

- SES-backed email delivery internals are documented in
  `docs/notification-email-delivery-mvp.md`.
- Remaining follow-up work is production-access readiness and future delivery
  operations hardening.
