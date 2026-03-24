## Summary

Describe the change in a few sentences.

## Why

Explain the problem, risk, or goal behind this PR.

## Validation

- [ ] `make lint`
- [ ] `make test`
- [ ] `make tf-fmt` (if `infra/` changed)
- [ ] Other relevant checks were run when needed

## Review Notes

- [ ] Tenant-scoped queries explicitly filter by `tenant_id` where applicable
- [ ] `tenant_id` comes from validated JWT claims, not client input
- [ ] Write flows keep domain changes and audit records in one transaction where required
- [ ] Structured logging or audit logging was updated if the change affects important write flows
- [ ] Docs were updated if architecture, security, or MVP scope changed materially

## Deployment Notes

List migration, config, or rollout steps if this change needs them.
