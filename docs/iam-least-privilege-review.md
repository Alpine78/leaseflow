# IAM Least-Privilege Review

**Status:** Initial audit — narrowing work tracked in issue #237
**Reviewed:** 2026-05-20
**Next review:** Before production release or quarterly, whichever comes first

---

## Scope

This document audits IAM roles and policies defined in the LeaseFlow Terraform
modules. It covers runtime roles (Lambda, EventBridge Scheduler), deployment
roles (GitHub Actions OIDC), and bucket-level policies (Terraform state).
CloudTrail-based actual-usage analysis is not yet available in the dev
environment; assessments are based on policy text and service documentation.

Out of scope per issue #237: Permissions Boundaries design, role-assumption
chain redesign.

---

## Roles and Policies

### 1. Lambda Backend Execution Role

**Module:** `infra/modules/lambda_backend/main.tf`
**Role name pattern:** `<name_prefix>-lambda-role`
**Trust principal:** `lambda.amazonaws.com`

| Sid | Actions | Resource | Condition | Assessment |
|-----|---------|----------|-----------|------------|
| `CloudWatchLogs` | `logs:CreateLogStream`, `logs:PutLogEvents` | `<log_group_arn>:*` | — | Well-scoped. Specific log group ARN, no wildcards. |
| `VpcNetworkingForLambda` | `ec2:CreateNetworkInterface`, `ec2:DescribeNetworkInterfaces`, `ec2:DeleteNetworkInterface`, `ec2:AssignPrivateIpAddresses`, `ec2:UnassignPrivateIpAddresses` | `*` | — | **Broadest statement.** AWS requires `Resource: "*"` for `Describe*` and for ENI create/delete at launch time. See note below. |
| `ReadDbPasswordParameter` | `ssm:GetParameter` | Specific parameter ARN | — | Well-scoped. Single named parameter. |
| `DecryptDbPasswordParameter` | `kms:Decrypt` | Specific KMS key ARN | `kms:EncryptionContext:PARAMETER_ARN` equals parameter ARN | Well-scoped. Encryption context condition prevents key reuse for other parameters. |
| `ReadNotificationEmailSmtpCredentialParameters` | `ssm:GetParameter` | Two specific parameter ARNs | — | Well-scoped. Only added when SMTP is configured (`length > 0`). |
| `DecryptNotificationEmailSmtpCredentialParameters` | `kms:Decrypt` | Specific KMS key ARN | `ForAnyValue:StringEquals kms:EncryptionContext:PARAMETER_ARN` over both parameter ARNs | Well-scoped. Same KMS key; context conditions prevent decrypt of other parameters. |

**Note on `VpcNetworkingForLambda` — required wildcard:**
AWS Lambda ENI management requires `Resource: "*"` for `ec2:DescribeNetworkInterfaces`
because the Lambda service creates the ENI before the ARN is known to the caller.
`ec2:CreateNetworkInterface` also cannot be pre-scoped to a specific ENI ARN for the
same reason. However, a `Condition` block using `ec2:SubnetID` and `ec2:VpcID` keys
**can** be added to `CreateNetworkInterface` to limit creation to the specific subnets
and VPC that Lambda uses. `DescribeNetworkInterfaces` does not support resource-level
conditions; the wildcard is unavoidable. See narrowing opportunity #1 below.

---

### 2. GitHub Actions OIDC Frontend Deploy Role

**Module:** `infra/modules/github_frontend_deploy_role/main.tf`
**Role name pattern:** `<name_prefix>-github-frontend-deploy`
**Trust principal:** `token.actions.githubusercontent.com` (federated OIDC)

**Trust conditions:**
- `aud` = `sts.amazonaws.com`
- `sub` = `repo:<github_repository>:environment:<github_environment>`

Variable validation rejects wildcards in `github_repository` and
`github_environment`, preventing accidental over-scoping of the trust.

| Sid | Actions | Resource | Assessment |
|-----|---------|----------|------------|
| `ListFrontendBucket` | `s3:ListBucket` | Frontend bucket ARN | Well-scoped. Bucket-level list only. |
| `WriteFrontendObjects` | `s3:PutObject`, `s3:DeleteObject` | `<frontend_bucket_arn>/*` | Well-scoped. Object-level writes only, scoped to this bucket. |
| `InvalidateFrontendDistribution` | `cloudfront:CreateInvalidation` | Specific CloudFront distribution ARN | Well-scoped. Single distribution ARN. |

**Overall assessment:** Minimal. No overly broad actions. OIDC trust is
properly locked to a specific repo + environment combination.

---

### 3. EventBridge Scheduler Invocation Role

**Module:** `infra/modules/reminder_scheduler/main.tf`
**Role name pattern:** `<name_prefix>-reminder-scheduler-role`
**Trust principal:** `scheduler.amazonaws.com`

**Trust conditions:**
- `aws:SourceAccount` = account ID (prevents cross-account scheduler confusion)
- `aws:SourceArn` = `arn:aws:scheduler:<region>:<account>:schedule-group/default`

| Sid | Actions | Resource | Assessment |
|-----|---------|----------|------------|
| `InvokeReminderScanLambda` | `lambda:InvokeFunction` | Specific Lambda function ARN | Well-scoped. Single function ARN, no wildcards. |

**Overall assessment:** Minimal. Trust conditions properly restrict which
scheduler resource can assume this role. No changes needed.

---

### 4. Terraform State Bucket Policy

**Module:** `infra/bootstrap/terraform_state/main.tf`
**Type:** S3 bucket resource policy (not an IAM role)

| Sid | Effect | Actions | Resource | Condition | Assessment |
|-----|--------|---------|----------|-----------|------------|
| `DenyInsecureTransport` | `Deny` | `s3:*` | Bucket + all objects | `aws:SecureTransport = false` | Appropriate. `s3:*` in a `Deny` statement is correct defence-in-depth; restricting the action set would weaken the control. |

**Note:** Terraform state access is controlled by AWS credentials held by the
developer/CI identity, not by an IAM role managed in this repo. A separate
access control review of who can access state is out of scope here.

---

## Narrowing Opportunities

### Opportunity 1 — VPC `CreateNetworkInterface` condition (Lambda role)

**Status: Investigated, not viable — documented as required wildcard.**

`ec2:Vpc` and `ec2:Subnet` are valid IAM condition keys for
`ec2:CreateNetworkInterface` in general, but they cannot be used with
VPC-attached Lambda functions. When Lambda creates a function, it validates the
execution role by evaluating the IAM policy without VPC/subnet request context.
A `StringEquals` condition on `ec2:Vpc` or `ec2:Subnet` evaluates to false when
those context keys are absent, causing Lambda's `CreateFunction` to fail with
`InvalidParameterValueException: The provided execution role does not have
permissions to call CreateNetworkInterface on EC2`.

This was confirmed by a failed apply attempt. The `VpcNetworkingForLambda`
statement remains `Resource: "*"` without conditions; see the documented
exceptions table below.

---

## Required Wildcards — Documented Exceptions

The following `Resource: "*"` entries are required by AWS service behaviour and
cannot be removed without breaking functionality:

**Lambda execution role — `VpcNetworkingForLambda`**

Actions: `ec2:CreateNetworkInterface`, `ec2:DescribeNetworkInterfaces`,
`ec2:DeleteNetworkInterface`, `ec2:AssignPrivateIpAddresses`,
`ec2:UnassignPrivateIpAddresses`

Reason: AWS Lambda validates the execution role during `CreateFunction` without
VPC/subnet request context. A `StringEquals` condition on `ec2:Vpc` or
`ec2:Subnet` evaluates to false when those context keys are absent, causing
`CreateFunction` to fail with `InvalidParameterValueException`. The remaining
four actions have no resource-level condition support at all. Confirmed by a
failed apply attempt (2026-05-20).

---

## Re-evaluation Cadence

- **Before production release:** Confirm no new overly broad actions have been
  added since this review.
- **Quarterly thereafter:** Re-run this review against the current Terraform
  state and update the table. Check for new roles added by new modules.
- **Trigger-based:** Any new AWS service added to the Lambda role or a new
  deployment role must be reviewed before merge.

---

## Related Documents

- [docs/production-readiness-hardening.md](production-readiness-hardening.md) — broader production hardening checklist; IAM section at "IAM Least-Privilege Review"
- [docs/security-baseline.md](security-baseline.md) — security requirements
- GitHub issue #237 — tracks implementation of opportunity #1
