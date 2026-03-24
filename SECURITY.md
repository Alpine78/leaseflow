# Security Policy

LeaseFlow is a learning and portfolio project, but security issues are still taken seriously.

## Supported version

Security fixes are applied to the latest state of the default branch only.

## Reporting a vulnerability

Please do not open a public GitHub issue for suspected vulnerabilities, credential exposure, or cross-tenant data access risks.

Preferred reporting path:

1. Use GitHub's private vulnerability reporting for this repository if it is enabled.
2. If private reporting is not available, contact the maintainer via GitHub: https://github.com/Alpine78

When reporting, include:

- a short description of the issue
- affected area (`backend`, `infra`, `ci/github`, or docs)
- reproduction steps or proof of concept
- potential impact, especially for tenant isolation or secret exposure

## Response expectations

- Initial acknowledgement: best effort
- Status updates: best effort
- Fixes: prioritized by impact, with tenant-isolation and credential exposure issues treated as highest priority

## Scope notes

Please report:

- authentication or authorization bypass
- cross-tenant data exposure
- secret leakage
- overly broad IAM or public infrastructure exposure
- injection flaws or unsafe input handling

For general hardening ideas that are not sensitive, a normal issue or pull request is fine.
