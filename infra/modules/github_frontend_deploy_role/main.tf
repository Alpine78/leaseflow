locals {
  github_oidc_url = "https://token.actions.githubusercontent.com"
  github_oidc_sub = "repo:${var.github_repository}:environment:${var.github_environment}"

  deploy_policy = {
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ListFrontendBucket"
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = var.frontend_bucket_arn
      },
      {
        Sid    = "WriteFrontendObjects"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:DeleteObject",
        ]
        Resource = "${var.frontend_bucket_arn}/*"
      },
      {
        Sid      = "InvalidateFrontendDistribution"
        Effect   = "Allow"
        Action   = ["cloudfront:CreateInvalidation"]
        Resource = var.cloudfront_distribution_arn
      },
    ]
  }
}

resource "aws_iam_openid_connect_provider" "github" {
  url             = local.github_oidc_url
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = []

  tags = merge(var.tags, { Name = "${var.name_prefix}-github-oidc" })
}

resource "aws_iam_role" "frontend_deploy" {
  name = "${var.name_prefix}-github-frontend-deploy"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.github.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
            "token.actions.githubusercontent.com:sub" = local.github_oidc_sub
          }
        }
      },
    ]
  })

  tags = merge(var.tags, { Name = "${var.name_prefix}-github-frontend-deploy" })
}

resource "aws_iam_role_policy" "frontend_deploy" {
  name   = "${var.name_prefix}-github-frontend-deploy"
  role   = aws_iam_role.frontend_deploy.id
  policy = jsonencode(local.deploy_policy)
}
