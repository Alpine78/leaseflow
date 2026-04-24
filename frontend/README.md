# LeaseFlow Frontend

This is the first real browser frontend slice for LeaseFlow.

It is local-first and targets the deployed dev API directly from the browser.
It is separate from `demo-client`, which remains a local portfolio/operator
tool.

## What it includes

- Cognito Hosted UI sign in and sign out
- OAuth authorization code flow with PKCE
- protected browser routes
- properties list and create
- leases list and create

This slice does not include hosted deployment, dashboard, reminders, or
notifications UI yet.

## Prerequisites

- Node.js 20+
- npm
- a deployed dev stack with Hosted UI and browser CORS configured

## Environment

Copy `.env.example` to `.env.local` and fill the values from Terraform outputs.

What it does: reads the deployed API and Cognito values for the browser frontend.
Target filename/service: `infra/environments/dev` / Terraform outputs.

```bash
cd /mnt/c/Repos/LeaseFlow/infra/environments/dev
terraform output -raw api_stage_invoke_url
terraform output -raw cognito_hosted_ui_base_url
terraform output -raw cognito_user_pool_client_id
```

Required env vars:

- `VITE_API_BASE_URL`
- `VITE_COGNITO_HOSTED_UI_BASE_URL`
- `VITE_COGNITO_CLIENT_ID`

## Run

What it does: installs frontend dependencies.
Target filename/service: `frontend/package.json`.

```bash
cd frontend
npm install
```

What it does: starts the local Vite dev server.
Target filename/service: `frontend/` browser app.

```bash
npm run dev
```

Then open `http://localhost:5173`.

## Checks

What it does: runs the frontend linter.
Target filename/service: `frontend/`.

```bash
npm run lint
```

What it does: runs the frontend test suite.
Target filename/service: `frontend/`.

```bash
npm run test
```

What it does: builds the frontend production bundle.
Target filename/service: `frontend/`.

```bash
npm run build
```

## Security notes

- Browser auth uses Cognito Hosted UI, not admin auth APIs.
- Protected API calls use the Cognito `id_token` because the backend depends on
  `custom:tenant_id`.
- Hosted UI requests `openid email profile` so readable custom attributes can
  be included in the ID token.
- Session state is stored in `sessionStorage`.
- Do not commit `.env.local`, tokens, tenant IDs, or any real user data.
