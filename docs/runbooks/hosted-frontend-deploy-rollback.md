# Hosted Frontend Deploy Rollback Runbook

## Purpose

Recover a bad hosted frontend deploy in the dev environment by redeploying a
known-good frontend commit to the existing S3 + CloudFront hosting path.

This is an operator-run dev rollback procedure. It is not production rollback
automation, artifact retention, monitoring, or a custom-domain procedure.

## Guardrails

- Run this only for the dev hosted frontend.
- Do not use static AWS access keys in GitHub.
- Do not run Terraform apply or destroy as part of frontend rollback.
- Do not edit GitHub Environment variables during rollback unless they are
  known to be stale after a dev stack rebuild.
- Do not capture bucket names, CloudFront distribution IDs, tenant IDs, Cognito
  emails, JWTs, auth headers, `.env.local` contents, SSM values, DB endpoints,
  raw response bodies, or screenshots containing sensitive values.

## Preconditions

- `.github/workflows/deploy-frontend-dev.yml` exists on the selected branch.
- GitHub Environment `dev` has the required non-secret deploy variables.
- The #171 GitHub OIDC deploy role exists in the dev AWS account.
- You know a good commit SHA, branch, tag, or release checkpoint to redeploy.
- The dev stack still has the frontend S3 bucket and CloudFront distribution.

## Primary Rollback: Redeploy A Known-Good Commit

What it does: rebuilds and redeploys static frontend assets from a known-good
GitHub ref.
Target service: GitHub Actions workflow `Deploy hosted frontend (dev)`.

1. Open GitHub Actions.
2. Select `Deploy hosted frontend (dev)`.
3. Select `Run workflow`.
4. Choose the known-good branch, tag, or commit ref from the workflow ref
   selector.
5. Set:
   - `environment`: `dev`
   - `confirm_dev_deploy`: `true`
   - `invalidation_path`: `/*`
6. Start the workflow.

Expected workflow result:

- Dependency install uses `npm ci --ignore-scripts`.
- `npm audit --audit-level=high` passes.
- Frontend lint, tests, and build pass.
- Only `frontend/dist/` is synced to the frontend bucket.
- CloudFront invalidation is created.
- Logs contain only safe deployment metadata and no secrets or tenant data.

## Browser Verification

What it does: confirms the known-good frontend is served from CloudFront after
rollback.
Target service: hosted frontend CloudFront URL.

After the invalidation has had time to propagate, check:

- `/` loads the SPA.
- `/dashboard` loads or redirects through the expected auth flow.
- `/properties` deep link returns the SPA instead of an S3 or CloudFront error.
- Sign-in starts from the hosted origin if auth validation is part of the
  rollback check.

Record only pass/fail statuses in evidence. Do not capture user emails, tokens,
tenant data, response bodies, or screenshots with sensitive values.

## Fallback Rollback: Local Operator Upload

Use this if GitHub Actions is unavailable but local AWS credentials are valid.

What it does: checks out the known-good commit locally, builds the frontend, and
uploads it through the existing operator script.
Target service: local repo, S3 frontend bucket, and CloudFront distribution.

```bash
cd /mnt/c/Repos/LeaseFlow
git fetch origin
git checkout <known-good-ref>
bash scripts/dev/write-frontend-env.sh
bash scripts/dev/upload-frontend.sh
```

Expected result:

- `frontend/.env.local` is regenerated from current dev Terraform outputs.
- Frontend build succeeds.
- S3 sync completes.
- CloudFront invalidation is created.
- Hosted browser route checks pass after invalidation propagation.

Return to the working branch after the fallback rollback if more development is
needed:

```bash
git checkout <working-branch>
```

## Future Artifact Rollback

Artifact-based rollback is not available unless a future deploy workflow stores
frontend build artifacts. If artifact retention is added later, the rollback
runbook can be extended to redeploy a retained artifact instead of rebuilding a
commit.

#173 does not add artifact upload, artifact retention, or artifact redeploy
logic.

## Sanitized Evidence Template

Use a short evidence note only when rollback validation is worth recording.

Allowed evidence:

- date
- issue number
- rollback source ref or commit SHA
- workflow run status
- invalidation created: pass/fail
- hosted route checks: pass/fail
- browser auth start: pass/fail, if checked
- local fallback used: yes/no

Forbidden evidence:

- bucket names
- CloudFront distribution IDs
- tenant IDs
- Cognito emails
- JWTs or auth headers
- `.env.local` contents
- SSM values
- DB endpoints
- raw API or provider response bodies
- screenshots containing sensitive values
