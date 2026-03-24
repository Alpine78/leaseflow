# Contributing to LeaseFlow

Thanks for contributing. LeaseFlow is a focused AWS and backend portfolio project, so the best contributions are small, explicit, and aligned with the documented MVP.

## Before you start

- Read [README.md](README.md) for the current project status.
- Review [docs/mvp-scope.md](docs/mvp-scope.md), [docs/architecture-v0.2.md](docs/architecture-v0.2.md), and [docs/security-baseline.md](docs/security-baseline.md) before proposing architecture-shaping changes.
- Prefer one focused improvement per pull request.

## Project guardrails

- Keep tenant isolation and security first.
- Do not trust `tenant_id` from client input. Tenant context must come from validated JWT claims.
- Every tenant-scoped query must explicitly filter by `tenant_id`.
- Use parameterized SQL only.
- Keep AWS choices cost-aware and operationally simple.
- Avoid large scope jumps such as containers, Kubernetes, or broad framework rewrites.

## Local setup

### Backend

```bash
cd backend
python -m venv .venv
. .venv/Scripts/activate
pip install -e ".[dev]"
```

### Useful commands

```bash
make format
make lint
make test
make tf-fmt
```

## Pull requests

- Explain the problem first, then the chosen change.
- Keep PRs reviewable. Smaller is usually better.
- Add or update tests when practical.
- Update docs when architecture, security posture, or MVP scope changes materially.
- Call out migrations, IAM changes, and AWS cost impact in the PR description.

## Issues

- Use the bug report template for reproducible defects.
- Use the feature request template for small, concrete proposals.
- Do not open public issues for security vulnerabilities. Follow [SECURITY.md](SECURITY.md) instead.
