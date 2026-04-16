# Deployed Dev Smoke Test Evidence - 2026-04-16

## Summary

The deployed dev smoke test runbook was executed successfully against the
Terraform-managed AWS dev environment.

Result:

- Lambda artifact build completed before deployment validation.
- Terraform dev environment initialized and validated successfully.
- Dev stack was available for smoke testing and Lambda code was refreshed.
- Database migration event returned `200`.
- Public health route returned `200`.
- Temporary Cognito smoke user authenticated and was deleted after the test.
- Protected property, lease, reminder, notification, and read-acknowledgement
  paths succeeded.
- Tenant override check passed: client-supplied `tenant_id` was ignored in
  favor of the Cognito JWT tenant claim.
- Dev stack was destroyed after validation to avoid ongoing cost.

## Context

- Date: 2026-04-16
- Operator: Codex-assisted run for Ilkka
- AWS account: `132805564800`
- Region: `eu-north-1`
- Branch: `68-execute-deployed-dev-smoke-test-and-capture-evidence`
- Commit before evidence: `730bdd9`
- Related issue: `#68 Execute deployed dev smoke test and capture evidence`
- Runbook: `docs/runbooks/deployed-dev-smoke-test.md`

## Deployment Validation

Pre-smoke checks:

```text
make build-lambda-artifact: passed
terraform init:             passed
terraform validate:         passed
```

Terraform apply result:

```text
Apply complete! Resources: 0 added, 1 changed, 0 destroyed.
```

The dev stack already existed in Terraform state. The apply refreshed the
deployed Lambda package before the smoke test.

## Smoke Test Results

Sanitized smoke summary:

```text
migration_status:                    200
GET /health:                         200
POST /properties:                    201
tenant override check:               passed
POST /leases:                        201
GET /properties:                     200
GET /leases:                         200
GET /lease-reminders/due-soon?days=7: 200
reminder candidate check:            passed
reminder scan status:                200
reminder scan candidate_count:       1
reminder scan created_count:         1
reminder scan duplicate_count:       0
GET /notifications:                  200
PATCH /notifications/{id}/read:      200
notification read check:             passed
Cognito cleanup:                     success
local smoke temp cleanup:            success
```

Tenant isolation validation:

- The property create request intentionally included a client-supplied
  `tenant_id`.
- The response was verified against the authenticated Cognito
  `custom:tenant_id` claim.
- The raw tenant value was not captured in this evidence.

Reminder validation:

- A synthetic lease due today was created.
- The due-soon candidate query returned the created lease.
- The internal reminder scan created one persisted `rent_due_soon`
  notification.
- The notification read path set `read_at`.

## Cleanup

Temporary Cognito user cleanup:

```text
admin-delete-user: success
```

Terraform destroy result:

```text
Destroy complete! Resources: 44 destroyed.
```

The synthetic database rows were removed as part of stack destroy. No API-level
delete endpoint was used or assumed.

## Evidence Hygiene

This evidence intentionally does not include:

- JWTs or Cognito tokens
- passwords or SSM values
- Cognito test user email
- tenant IDs
- property names or addresses
- resident names
- notification titles or messages
- full DB connection strings
- tenant row contents

## Notes

The WSL environment did not have `jq` installed, so the smoke flow was executed
with equivalent `python3` JSON parsing in a temporary local script. No repo code
or Terraform behavior was changed for that workaround.
