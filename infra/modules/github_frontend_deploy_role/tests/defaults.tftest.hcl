mock_provider "aws" {}

variables {
  name_prefix                 = "leaseflow-dev"
  github_repository           = "Alpine78/leaseflow"
  github_environment          = "dev"
  frontend_bucket_arn         = "arn:aws:s3:::leaseflow-dev-frontend-123456789012-eu-north-1"
  cloudfront_distribution_arn = "arn:aws:cloudfront::123456789012:distribution/E1234567890ABC"
  tags = {
    Project = "leaseflow"
  }
}

run "creates_github_oidc_provider_and_scoped_deploy_role" {
  command = apply

  assert {
    condition     = aws_iam_openid_connect_provider.github.url == "https://token.actions.githubusercontent.com"
    error_message = "OIDC provider URL should be GitHub Actions."
  }

  assert {
    condition     = contains(aws_iam_openid_connect_provider.github.client_id_list, "sts.amazonaws.com")
    error_message = "OIDC provider should allow the AWS STS audience."
  }

  assert {
    condition     = jsondecode(aws_iam_role.frontend_deploy.assume_role_policy).Statement[0].Action == "sts:AssumeRoleWithWebIdentity"
    error_message = "Deploy role trust policy should allow web identity role assumption."
  }

  assert {
    condition     = jsondecode(aws_iam_role.frontend_deploy.assume_role_policy).Statement[0].Principal.Federated == aws_iam_openid_connect_provider.github.arn
    error_message = "Deploy role should trust only the Terraform-managed GitHub OIDC provider."
  }

  assert {
    condition     = jsondecode(aws_iam_role.frontend_deploy.assume_role_policy).Statement[0].Condition.StringEquals["token.actions.githubusercontent.com:aud"] == "sts.amazonaws.com"
    error_message = "Deploy role trust policy should require the AWS STS audience."
  }

  assert {
    condition     = jsondecode(aws_iam_role.frontend_deploy.assume_role_policy).Statement[0].Condition.StringEquals["token.actions.githubusercontent.com:sub"] == "repo:Alpine78/leaseflow:environment:dev"
    error_message = "Deploy role trust policy should be scoped to the repo and dev GitHub Environment."
  }
}

run "grants_only_frontend_bucket_and_cloudfront_invalidation_permissions" {
  command = apply

  assert {
    condition     = contains(jsondecode(aws_iam_role_policy.frontend_deploy.policy).Statement[0].Action, "s3:ListBucket")
    error_message = "Deploy policy should allow listing only the frontend bucket."
  }

  assert {
    condition     = jsondecode(aws_iam_role_policy.frontend_deploy.policy).Statement[0].Resource == "arn:aws:s3:::leaseflow-dev-frontend-123456789012-eu-north-1"
    error_message = "Bucket list permission should be scoped to the frontend bucket ARN."
  }

  assert {
    condition = alltrue([
      for action in ["s3:PutObject", "s3:DeleteObject"] :
      contains(jsondecode(aws_iam_role_policy.frontend_deploy.policy).Statement[1].Action, action)
    ])
    error_message = "Deploy policy should allow writing and deleting frontend bucket objects."
  }

  assert {
    condition     = jsondecode(aws_iam_role_policy.frontend_deploy.policy).Statement[1].Resource == "arn:aws:s3:::leaseflow-dev-frontend-123456789012-eu-north-1/*"
    error_message = "Object permissions should be scoped to frontend bucket objects."
  }

  assert {
    condition     = contains(jsondecode(aws_iam_role_policy.frontend_deploy.policy).Statement[2].Action, "cloudfront:CreateInvalidation")
    error_message = "Deploy policy should allow creating CloudFront invalidations."
  }

  assert {
    condition     = jsondecode(aws_iam_role_policy.frontend_deploy.policy).Statement[2].Resource == "arn:aws:cloudfront::123456789012:distribution/E1234567890ABC"
    error_message = "CloudFront invalidation permission should be scoped to the hosted frontend distribution."
  }

  assert {
    condition = !contains(flatten([
      for statement in jsondecode(aws_iam_role_policy.frontend_deploy.policy).Statement : statement.Action
    ]), "*")
    error_message = "Deploy policy must not grant wildcard actions."
  }

  assert {
    condition = alltrue([
      for action in flatten([
        for statement in jsondecode(aws_iam_role_policy.frontend_deploy.policy).Statement : statement.Action
      ]) : startswith(action, "s3:") || startswith(action, "cloudfront:")
    ])
    error_message = "Deploy policy should not grant Terraform, RDS, SSM, Cognito, Lambda, SES, or other service permissions."
  }
}
