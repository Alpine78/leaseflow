# Hosted Frontend Smoke Test Evidence - 2026-04-28

## Summary

The hosted frontend smoke validation for issue `#108` was started but not
completed.

Result:

- Frontend production build passed.
- Terraform dev backend initialization succeeded in WSL after restoring the
  ignored local `backend.hcl` from the bootstrap output.
- Dev Terraform remote state did not contain the expected deployed stack
  resources or outputs.
- S3 upload, CloudFront invalidation, and hosted browser smoke validation were
  not run because the frontend hosting outputs could not be trusted.

## Context

- Date: 2026-04-28
- Operator: Codex-assisted run for Ilkka
- Region: `eu-north-1`
- Branch: `108-execute-hosted-frontend-deployment-and-browser-smoke-validation`
- Related issue: `#108 Execute hosted frontend deployment and browser smoke validation`

## Local Validation

Frontend build:

```text
cd frontend
npm run build: passed
```

Terraform initialization:

```text
cd infra/environments/dev
terraform init -reconfigure -backend-config=backend.hcl: passed
```

Terraform state/output check:

```text
terraform state list | wc -l: 0
terraform output: no usable dev stack outputs available from the configured remote state
```

## Hosted Deployment Validation

The following steps were intentionally not run:

```text
aws s3 sync dist/ s3://<frontend-bucket>/ --delete
aws cloudfront create-invalidation --distribution-id <distribution-id> --paths "/*"
```

Reason:

- The configured Terraform remote state did not expose the expected
  `frontend_bucket_name`, `frontend_cloudfront_distribution_id`, or
  `frontend_cloudfront_url` outputs.
- Uploading assets without trusted Terraform outputs would risk targeting the
  wrong bucket or distribution.

## Browser Smoke Results

Hosted browser validation was not completed.

```text
CloudFront root route:                  not run
CloudFront /properties deep link:        not run
Hosted UI sign-in from CloudFront:       not run
Hosted auth callback:                    not run
Hosted properties list/create:           not run
Hosted leases list/create:               not run
Hosted sign-out:                         not run
```

## Follow-Up

Before rerunning this smoke test, fix the dev Terraform state source of truth:

- confirm whether the deployed dev stack still exists in AWS
- confirm whether the remote S3 backend key is the intended dev state location
- migrate or re-apply dev state intentionally; do not infer resources from stale
  local files
- rerun this smoke validation only after `terraform output` returns the hosted
  frontend outputs from the configured dev backend

## Evidence Hygiene

This evidence intentionally does not include:

- JWTs or Cognito tokens
- authorization headers or session storage values
- Cognito user emails
- tenant IDs
- property names or addresses
- resident names or lease IDs
- notification titles or messages
- SSM values or DB connection strings
- Terraform state contents
- raw browser response payloads
