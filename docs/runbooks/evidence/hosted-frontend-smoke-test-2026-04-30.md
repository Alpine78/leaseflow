# Hosted Frontend Smoke Test Evidence - 2026-04-30

## Summary

The hosted frontend smoke validation passed against the Terraform-managed dev
frontend hosting path.

Result:

- Frontend production build passed.
- Frontend assets uploaded to the Terraform-managed private S3 frontend bucket.
- CloudFront invalidation was created successfully.
- Hosted browser validation passed from the CloudFront origin.
- Cognito Hosted UI sign-in and sign-out worked from the hosted origin.
- Authenticated browser API calls worked from the hosted origin.

## Context

- Date: 2026-04-30
- Operator: Ilkka with Codex-assisted validation
- Region: `eu-north-1`
- Branch: `main`
- Related issue: `#108 Execute hosted frontend deployment and browser smoke validation`
- Release context: `v0.3.0` frontend MVP checkpoint validation

## Local Build And Upload

Frontend dependency reinstall:

```text
cd frontend
npm ci --ignore-scripts: passed
```

Frontend build:

```text
cd frontend
npm run build: passed
```

Hosted upload:

```text
bash scripts/dev/upload-frontend.sh: passed
```

Upload and invalidation summary:

```text
S3 sync: passed
CloudFront invalidation: created
CloudFront invalidation status at creation: InProgress
```

## Browser Smoke Results

Manual hosted browser validation:

```text
CloudFront root route:                  passed
CloudFront /properties deep link:        passed
Hosted UI sign-in from CloudFront:       passed
Hosted auth callback:                    passed
Dashboard load:                          passed
Hosted properties list/create:           passed
Hosted leases list/create:               passed
Hosted notifications route:              passed
Hosted sign-out:                         passed
```

Authenticated dashboard validation:

```text
Dashboard summary loaded from protected tenant-scoped APIs: passed
Properties summary count rendered:                         passed
Leases summary count rendered:                             passed
Due-soon reminder count rendered:                          passed
Unread notification count rendered:                        passed
```

## Evidence Hygiene

This evidence intentionally does not include:

- JWTs or Cognito tokens
- authorization headers or session storage values
- Cognito user emails
- tenant IDs
- CloudFront distribution IDs
- S3 bucket names
- property names or addresses
- resident names or lease IDs
- notification titles or messages
- SSM values or DB connection strings
- Terraform state contents
- raw browser response payloads
- screenshots with sensitive values
