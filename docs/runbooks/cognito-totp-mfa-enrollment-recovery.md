# Cognito TOTP MFA Enrollment And Recovery

## Purpose

This runbook documents the dev validation path for Cognito software-token TOTP
MFA and the safe operator recovery path for an MFA-locked account.

LeaseFlow uses Cognito Hosted UI for browser sign-in. This runbook does not add
a custom LeaseFlow TOTP enrollment screen, direct browser Cognito admin APIs,
SMS MFA, WebAuthn, passkeys, or privileged role enforcement.

## Current Scope

- The dev Cognito user pool enables software-token TOTP MFA.
- MFA mode is optional because LeaseFlow does not yet have admin/operator user
  groups.
- Browser authentication continues to use Cognito Hosted UI and OAuth code flow
  with PKCE.
- If a future admin/operator group is added, requiring MFA for that group needs
  a separate design and test path.

## Enrollment Validation

Run this only against disposable dev users. Do not capture or share QR codes,
TOTP shared secrets, one-time codes, passwords, JWTs, Cognito emails, tenant
IDs, session storage, or raw AWS responses.

What it does: loads the deployed dev Cognito and frontend values used for
Hosted UI validation.
Target service: Terraform-managed dev Cognito user pool and frontend outputs.

```bash
cd /mnt/c/Repos/LeaseFlow/infra/environments/dev
export AWS_PROFILE=terraform
export AWS_REGION=eu-north-1

export USER_POOL_ID=$(terraform output -raw cognito_user_pool_id)
export FRONTEND_URL=$(terraform output -raw frontend_cloudfront_url)
```

What it does: creates a disposable Hosted UI test user with a tenant claim.
Target service: Amazon Cognito user pool.

```bash
cd /mnt/c/Repos/LeaseFlow
bash scripts/dev/create-demo-user.sh
```

Then sign in through the local or hosted frontend and follow the Cognito Hosted
UI / managed login MFA prompts if Cognito presents enrollment or challenge
steps. Use a real authenticator app for the TOTP code. If optional MFA does not
present an enrollment prompt for the selected test user, do not claim end-to-end
enrollment evidence from #241; create a follow-up ticket for custom in-app
enrollment or role-required MFA design.

Safe evidence may include:

- date
- issue number
- environment name
- Hosted UI sign-in reached MFA setup/challenge: pass/fail
- authenticator app TOTP challenge completed: pass/fail
- frontend returned to the expected origin after sign-in: pass/fail

## Recovery For MFA-Locked Dev Accounts

Use recovery only after verifying the requester is allowed to recover the
account. In dev, prefer deleting and recreating disposable users. For any
non-disposable account, record only sanitized evidence.

What it does: disables software-token MFA preference for one known Cognito user.
Target service: Amazon Cognito user pool.

```bash
aws cognito-idp admin-set-user-mfa-preference \
  --user-pool-id "$USER_POOL_ID" \
  --username "<cognito-username>" \
  --software-token-mfa-settings Enabled=false,PreferredMfa=false
```

What it does: sets a new operator-known password for a dev user when password
recovery is also required.
Target service: Amazon Cognito user pool.

```bash
aws cognito-idp admin-set-user-password \
  --user-pool-id "$USER_POOL_ID" \
  --username "<cognito-username>" \
  --password "<new-temporary-password>" \
  --permanent
```

Do not paste real usernames, passwords, TOTP codes, QR codes, tenant values,
JWTs, or raw AWS output into tickets or evidence. After recovery, the user
should sign in through Hosted UI and re-enroll MFA if required by the operator
process.
