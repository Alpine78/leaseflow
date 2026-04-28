# LeaseFlow Frontend MVP Strategy

## Purpose

This document defines the real browser frontend direction for LeaseFlow.

It is intentionally separate from the existing `demo-client`, which remains a
local portfolio/demo tool and not the production-like frontend path.

## Current Repo Truth

- The backend and Terraform-managed dev infrastructure are already validated as
  a backend/infra MVP.
- The current `demo-client` is a localhost proxy-based demo helper, not a real
  browser product frontend.
- The dev Terraform stack now configures a Cognito Hosted UI foundation with a
  managed domain, OAuth authorization code flow, and callback/logout URLs for
  approved frontend origins.
- The dev Terraform stack now configures allowlisted browser CORS on the HTTP
  API for approved frontend origins.
- The first local browser frontend slice now exists under `frontend/` with
  sign-in plus properties and leases list/create/update flows.
- The dev Terraform stack now includes an S3 + CloudFront hosting path for the
  static SPA. Asset upload remains a local operator command.
- Hosted frontend smoke validation is still an operator-run release validation
  item, not an implemented CI deployment path.
- Dashboard, reminders, and notifications UI are still follow-up work.

## Chosen Frontend Direction

- Real frontend target: `React + Vite + TypeScript`
- Real frontend location: `frontend/` directory
- Local development mode: Vite dev server on `http://localhost:5173`
- Hosting target: static SPA assets in private S3 behind CloudFront
- This phase does not add SSR, Next.js, or a separate backend-for-frontend

## Auth Contract

- Browser authentication uses Cognito Hosted UI with OAuth Authorization Code
  flow and PKCE.
- The browser frontend must not use Cognito admin auth APIs or token-paste
  flows.
- Controlled smoke tests may continue to use
  `ADMIN_USER_PASSWORD_AUTH` outside the browser as an operator-only path.
- Protected API calls continue to use a Cognito ID token in the
  `Authorization` header because the backend reads tenant context from the
  Cognito claim `custom:tenant_id`.
- The current Terraform foundation already includes the OAuth flows,
  callback URLs, logout URLs, and managed Hosted UI domain required for the
  first browser frontend slice.

## CORS Contract

- API Gateway CORS is allowlist-based, not wildcard-based.
- Local origin: `http://localhost:5173`
- Hosted origin: HTTPS CloudFront-backed SPA origin from Terraform output
- Browser methods: `GET`, `POST`, `PATCH`, `OPTIONS`
- Browser headers: `Authorization`, `Content-Type`
- Browser API calls use bearer tokens in the `Authorization` header, not
  cookie-based cross-site credentials.
- Current Terraform uses `allow_credentials = false` for the browser path.
- CORS is browser access control only. It is not authentication or
  authorization.

## Frontend Scope

Broader frontend MVP screens:

- sign in / sign out
- dashboard
- properties
- leases
- due reminders
- notifications

Current implemented slice:

- sign in / sign out
- app shell and navigation
- properties list, create, and update flow
- leases list, create, and update flow

Later frontend follow-ups:

- dashboard summary UI
- due reminders UI
- notifications list and mark-read UI
- hosted asset upload and browser smoke validation before release

## Follow-Up Tickets

- Complete hosted frontend smoke validation after the dev Terraform state
  source of truth is restored.
- Add dashboard, due reminders, and notifications UI.

## Guardrails

- Keep RDS private.
- Do not send or trust `tenant_id` from browser request bodies.
- Do not use admin auth flows in the browser.
- Do not store JWTs, passwords, Cognito emails, tenant IDs, SSM values, or DB
  connection strings in committed files.
- Do not treat the existing `demo-client` as the future frontend codebase.
