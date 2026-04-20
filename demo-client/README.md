# LeaseFlow Demo Client

This is a local portfolio/demo client for the deployed LeaseFlow dev API.

It is not a production frontend.

## Run

```bash
make demo-client
```

Then open:

```text
http://127.0.0.1:8765
```

## Inputs

The UI asks for:

- deployed API base URL
- temporary Cognito ID token
- AWS region, default `eu-north-1`
- backend Lambda function name, default `leaseflow-dev-backend`

The ID token is kept in browser memory and sent only to the local demo server.
Do not paste production tokens.

## Safety

- Use synthetic demo data only.
- Do not screenshot JWTs, passwords, emails, tenant IDs, SSM values, or real tenant data.
- Keep RDS private.
- Destroy the dev stack after demo use when it is not needed.

## Why There Is A Local Server

The deployed HTTP API is not configured as a browser product API with CORS.
The local server lets the browser talk to `localhost` while the server proxies
only the allowlisted demo API calls to the deployed API Gateway.
