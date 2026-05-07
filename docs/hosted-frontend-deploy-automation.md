# Hosted Frontend Deploy Automation Plan

## Purpose

This document records the safe path from the current local operator upload to a
controlled GitHub Actions deployment for the hosted LeaseFlow frontend.

The current project already has a real browser frontend, private S3 +
CloudFront hosting infrastructure, and successful hosted smoke evidence. Hosted
asset upload still remains a local operator step through
`scripts/dev/upload-frontend.sh`.

This document does not define a custom domain or production deployment path.

## Current State

- Frontend CI runs on pull requests and `main` pushes.
- CI installs with `npm ci --ignore-scripts`.
- CI runs `npm audit --audit-level=high`, lint, tests, and build.
- Terraform creates the private frontend S3 bucket and CloudFront distribution.
- `scripts/dev/upload-frontend.sh` builds `frontend/`, syncs `frontend/dist/`
  to S3, and creates a CloudFront invalidation.
- Hosted browser smoke validation passed from the CloudFront origin with
  sanitized evidence in
  `docs/runbooks/evidence/hosted-frontend-smoke-test-2026-04-30.md`.
- Terraform now defines a GitHub OIDC provider and a least-privilege dev
  frontend deploy role for the future workflow.
- `.github/workflows/deploy-frontend-dev.yml` now defines a manual dev-only
  hosted frontend deploy workflow.

## Options

### Keep Manual Operator Upload

This remains the current path. It is simple, explicit, and avoids adding AWS
permissions to GitHub Actions.

Tradeoffs:

- Good for learning and short-lived dev validation.
- Harder to audit than a protected workflow.
- Depends on the operator's local AWS credentials and local environment.
- Easy to forget the exact build, sync, invalidation, and smoke evidence steps.

### Add Static AWS Access Keys To GitHub Secrets

This should not be used. Long-lived AWS access keys in GitHub secrets are a
larger credential-management risk than this project needs.

Tradeoffs:

- Simple to wire technically.
- Creates rotation and exposure risk.
- Weakens the current supply-chain and least-privilege direction.

### Add GitHub OIDC Deploy Role

This is the preferred future automation path. GitHub Actions obtains short-lived
AWS credentials through OpenID Connect and assumes a narrowly scoped IAM role.

Tradeoffs:

- More setup than manual upload.
- Avoids long-lived AWS keys in GitHub.
- Can be constrained to this repository, approved refs, and the `dev`
  deployment environment.
- Gives repeatable logs and a safer review point through GitHub environments.

## Chosen Direction

Keep manual upload supported. Use a separate `workflow_dispatch` GitHub Actions
deployment for dev only when repeatable hosted deploy logs are useful. The
workflow is backed by GitHub OIDC and a least-privilege AWS role.

The first automated path should not deploy from every `main` push. Manual
dispatch is safer for this portfolio/dev workflow because the AWS dev stack may
be destroyed for cost control.

## Workflow Shape

The workflow:

- Trigger only through `workflow_dispatch`.
- Target only the dev environment.
- Use GitHub OIDC through `aws-actions/configure-aws-credentials`.
- Use `permissions: contents: read` and `id-token: write` only where required.
- Install frontend dependencies with `npm ci --ignore-scripts`.
- Run `npm audit --audit-level=high`.
- Run `npm run lint`, `npm run test`, and `npm run build`.
- Upload only `frontend/dist/` to the Terraform-created frontend bucket.
- Use `aws s3 sync frontend/dist/ s3://<bucket>/ --delete --only-show-errors`.
- Create a CloudFront invalidation, defaulting to `/*`.
- Print only safe deployment metadata such as branch, commit SHA, environment,
  invalidation ID, and pass/fail statuses.

The workflow must not print or store JWTs, Cognito emails, tenant IDs, SSM
values, DB endpoints, AWS credentials, or frontend `.env.local` contents.

## Workflow Inputs

The `workflow_dispatch` inputs are intentionally small:

- `environment`: choice, initially only `dev`.
- `invalidation_path`: string, default `/*`.
- `confirm_dev_deploy`: required boolean.

The workflow should fail early if the selected environment is not `dev` or if
the confirmation input is missing.

## GitHub Environment Controls

Use a GitHub deployment environment named `dev`.

Recommended controls:

- Restrict deploys to approved refs, preferably `main` or explicitly selected
  release branches/tags.
- Add required reviewer protection if the repository plan supports it.
- Use a concurrency group such as `frontend-deploy-dev` so only one hosted
  frontend deploy runs at a time.
- Keep deployment history visible in GitHub.
- Do not store static AWS access keys as environment secrets.

## AWS IAM Boundaries

The future deploy role should have only the permissions needed for the hosted
frontend asset path.

Trust policy requirements:

- Trust GitHub's OIDC provider.
- Restrict `aud` to `sts.amazonaws.com`.
- Restrict `sub` to this repository and approved deployment refs or the GitHub
  environment subject.

Permission requirements:

- Allow `s3:ListBucket` only on the frontend hosting bucket.
- Allow `s3:PutObject`, `s3:DeleteObject`, and the minimum required object
  metadata/tagging actions only under the frontend bucket objects.
- Allow `cloudfront:CreateInvalidation` only for the configured CloudFront
  distribution.
- Allow read-only discovery only if required by the workflow design.

Explicitly out of scope for the frontend deploy role:

- Terraform state access.
- Terraform apply or destroy.
- RDS access.
- SSM Parameter Store access.
- Cognito admin access.
- Lambda update or invoke access.
- SES access.
- Broad `s3:*`, `cloudfront:*`, or account-wide admin permissions.

## Rollback Expectations

The first workflow can deploy the current build only, but rollback must be
defined before relying on automation for demos or releases.

Acceptable future rollback paths:

- Rerun the workflow for a known-good commit SHA.
- Store a build artifact for a limited time and redeploy that artifact.
- Keep a short runbook for restoring the previous S3 object set if artifact
  retention is added.

Rollback evidence must stay sanitized and should not include bucket names,
distribution IDs, tenant data, tokens, or raw response bodies.

## Follow-Up Tickets

### Add GitHub OIDC Role For Hosted Frontend Deploy

Completed as a Terraform-managed OIDC provider and least-privilege dev frontend
deploy role. The role is scoped to the `dev` GitHub Environment subject and does
not grant Terraform, RDS, SSM, Cognito, Lambda, or SES permissions.

### Add Manual GitHub Actions Hosted Frontend Deploy Workflow

Completed as a `workflow_dispatch` deploy workflow that uses OIDC, GitHub
environment protection, npm install hardening, audit, lint, tests, build, S3
sync, and CloudFront invalidation.

### Add Hosted Frontend Deploy Rollback Runbook

Completed in `docs/runbooks/hosted-frontend-deploy-rollback.md`. The current
rollback path is redeploying a known-good Git ref through the manual dev
workflow, with local operator upload documented as a fallback. Artifact rollback
remains future-only until a workflow stores deploy artifacts.

### Capture Sanitized Hosted Frontend CI Deploy Evidence

After the workflow exists, run it once against dev and record safe evidence:
date, branch/ref, issue number, high-level command statuses, invalidation
status, and browser smoke pass/fail results.

## References

- [GitHub Actions OpenID Connect for AWS](https://docs.github.com/actions/security-for-github-actions/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services)
- [GitHub Actions deployment environments](https://docs.github.com/en/actions/reference/deployments-and-environments)
- [GitHub Actions workflow syntax for `workflow_dispatch`](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)
- [aws-actions/configure-aws-credentials](https://github.com/aws-actions/configure-aws-credentials)
