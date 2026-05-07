# Hosted Frontend CI Deploy Evidence - 2026-05-07

## Summary

The manual GitHub Actions hosted frontend deploy workflow passed against the
dev hosted frontend path, and the hosted browser smoke check passed from the
CloudFront origin.

Result:

- Manual workflow dispatch: passed
- Frontend install, audit, lint, tests, and build: passed
- Hosted frontend asset upload: passed
- CloudFront invalidation: created
- Hosted browser smoke validation: passed

## Context

- Date: 2026-05-07
- Region: `eu-north-1`
- Branch/ref: `main`
- Related issue: `#174 Capture sanitized hosted frontend CI deploy evidence`
- Workflow: `Deploy hosted frontend (dev)`
- Workflow event: `workflow_dispatch`
- Workflow run status: `success`
- Workflow run ID: `25491872166`
- Commit SHA: `fcb1af6179d086553cd71cfeb8168358fbee80c3`

## Workflow Results

GitHub Actions job result:

```text
Deploy hosted frontend to dev: passed
```

Workflow step results:

```text
Validate deployment inputs: passed
Check out selected ref:     passed
Set up Node.js:             passed
npm ci --ignore-scripts:    passed
npm audit --audit-level=high: passed
npm run lint:               passed
npm run test:               passed
npm run build:              passed
Configure AWS credentials:  passed
S3 sync:                    passed
CloudFront invalidation:    created
Safe deployment summary:    passed
```

## Browser Smoke Results

Manual hosted browser validation:

```text
CloudFront root route:                    passed
CloudFront /dashboard route:              passed
CloudFront /properties deep link:         passed
Hosted UI sign-in from CloudFront origin: passed
Authenticated dashboard load:             passed
Authenticated properties view:            passed
Authenticated leases view:                passed
Authenticated notifications view:         passed
Hosted sign-out:                          passed
```

Authenticated API-backed views loaded from the hosted frontend origin:

```text
Dashboard summary:     passed
Properties API view:   passed
Leases API view:       passed
Notifications API view: passed
```

## Evidence Hygiene

This evidence intentionally does not include:

- JWTs or Cognito tokens
- authorization headers or session storage values
- Cognito user emails
- tenant IDs
- CloudFront distribution IDs
- CloudFront domain names or URLs
- S3 bucket names
- property names or addresses
- resident names or lease IDs
- notification titles or messages
- SSM values or DB endpoints
- AWS credentials
- Terraform state contents
- frontend `.env.local` contents
- raw browser, API, AWS, or Terraform response payloads
- screenshots with sensitive values
