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
- A real browser frontend is still not implemented yet; only the auth/CORS
  foundation exists.

## Chosen Frontend Direction

- Real frontend target: `React + Vite + TypeScript`
- Real frontend location: future `frontend/` directory
- Local development mode: Vite dev server on `http://localhost:5173`
- Later hosting target: static SPA assets in S3 behind CloudFront
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
- Planned local origin: `http://localhost:5173`
- Planned hosted origin: one HTTPS CloudFront-backed SPA origin
- Planned browser methods: `GET`, `POST`, `PATCH`, `OPTIONS`
- Planned browser headers: `Authorization`, `Content-Type`
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

First implementation milestone only:

- sign in / sign out
- app shell and navigation
- properties list and create flow
- leases list and create flow
- properties and leases structure should remain update-ready for later PATCH
  route support

Later frontend follow-ups:

- dashboard summary UI
- due reminders UI
- notifications list and mark-read UI
- S3 + CloudFront hosting path

## Follow-Up Tickets

- `#92` Build the React + Vite + TypeScript frontend shell with auth,
  properties, and leases flows.
- `#93` Add the later S3 + CloudFront hosting path for the frontend.

## Guardrails

- Keep RDS private.
- Do not send or trust `tenant_id` from browser request bodies.
- Do not use admin auth flows in the browser.
- Do not store JWTs, passwords, Cognito emails, tenant IDs, SSM values, or DB
  connection strings in committed files.
- Do not treat the existing `demo-client` as the future frontend codebase.
