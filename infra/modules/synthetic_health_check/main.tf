data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  schedule_group_name = "default"
  schedule_group_arn  = "arn:aws:scheduler:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:schedule-group/${local.schedule_group_name}"
  metric_namespace    = "LeaseFlow/SyntheticChecks"
}

resource "random_password" "synthetic_user" {
  length           = 20
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
  min_upper        = 1
  min_lower        = 1
  min_numeric      = 1
  min_special      = 1
}

resource "random_uuid" "synthetic_tenant_id" {}

resource "aws_cognito_user" "synthetic" {
  user_pool_id = var.user_pool_id
  username     = "synthetic-health-check@leaseflow.internal"

  attributes = {
    email              = "synthetic-health-check@leaseflow.internal"
    email_verified     = "true"
    "custom:tenant_id" = random_uuid.synthetic_tenant_id.result
  }

  password       = random_password.synthetic_user.result
  message_action = "SUPPRESS"
}

resource "aws_secretsmanager_secret" "synthetic_credentials" {
  name                    = "${var.name_prefix}-synthetic-health-check-credentials"
  description             = "Synthetic health check Cognito credentials. No real tenant data."
  recovery_window_in_days = 0

  tags = merge(var.tags, { Name = "${var.name_prefix}-synthetic-health-check-credentials" })
}

resource "aws_secretsmanager_secret_version" "synthetic_credentials" {
  secret_id = aws_secretsmanager_secret.synthetic_credentials.id

  secret_string = jsonencode({
    username     = aws_cognito_user.synthetic.username
    password     = random_password.synthetic_user.result
    user_pool_id = var.user_pool_id
    client_id    = var.user_pool_client_id
  })
}

resource "aws_cloudwatch_log_group" "synthetic_hc" {
  name              = "/aws/lambda/${var.name_prefix}-synthetic-health-check"
  retention_in_days = 14

  tags = var.tags
}

resource "aws_iam_role" "lambda" {
  name = "${var.name_prefix}-synthetic-hc-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = merge(var.tags, { Name = "${var.name_prefix}-synthetic-hc-lambda-role" })
}

resource "aws_iam_role_policy" "lambda" {
  name = "${var.name_prefix}-synthetic-hc-lambda-policy"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Logs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "${aws_cloudwatch_log_group.synthetic_hc.arn}:*"
      },
      {
        Sid      = "PublishMetric"
        Effect   = "Allow"
        Action   = ["cloudwatch:PutMetricData"]
        Resource = "*"
        Condition = {
          StringEquals = {
            "cloudwatch:namespace" = local.metric_namespace
          }
        }
      },
      {
        Sid      = "GetCredentials"
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = aws_secretsmanager_secret.synthetic_credentials.arn
      },
      {
        Sid      = "AdminAuth"
        Effect   = "Allow"
        Action   = ["cognito-idp:AdminInitiateAuth"]
        Resource = "arn:aws:cognito-idp:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:userpool/${var.user_pool_id}"
      },
    ]
  })
}

data "archive_file" "lambda_code" {
  type        = "zip"
  source_file = "${path.module}/lambda_handler.py"
  output_path = "${path.module}/lambda_handler.zip"
}

resource "aws_lambda_function" "synthetic_hc" {
  function_name    = "${var.name_prefix}-synthetic-health-check"
  description      = "Periodic synthetic API health check for LeaseFlow."
  role             = aws_iam_role.lambda.arn
  filename         = data.archive_file.lambda_code.output_path
  source_code_hash = data.archive_file.lambda_code.output_base64sha256
  handler          = "lambda_handler.handler"
  runtime          = "python3.12"
  timeout          = 30

  environment {
    variables = {
      SYNTHETIC_CREDENTIALS_SECRET_ARN = aws_secretsmanager_secret.synthetic_credentials.arn
      API_URL                          = var.api_url
      ENVIRONMENT                      = var.environment
    }
  }

  depends_on = [aws_cloudwatch_log_group.synthetic_hc]

  tags = merge(var.tags, { Name = "${var.name_prefix}-synthetic-health-check" })
}

resource "aws_iam_role" "scheduler" {
  name = "${var.name_prefix}-synthetic-hc-scheduler-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "scheduler.amazonaws.com" }
      Action    = "sts:AssumeRole"
      Condition = {
        StringEquals = {
          "aws:SourceAccount" = data.aws_caller_identity.current.account_id
        }
        ArnEquals = {
          "aws:SourceArn" = local.schedule_group_arn
        }
      }
    }]
  })

  tags = merge(var.tags, { Name = "${var.name_prefix}-synthetic-hc-scheduler-role" })
}

resource "aws_iam_role_policy" "scheduler" {
  name = "${var.name_prefix}-synthetic-hc-scheduler-policy"
  role = aws_iam_role.scheduler.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "InvokeSyntheticHcLambda"
      Effect   = "Allow"
      Action   = ["lambda:InvokeFunction"]
      Resource = aws_lambda_function.synthetic_hc.arn
    }]
  })
}

resource "aws_scheduler_schedule" "synthetic_hc" {
  name                         = "${var.name_prefix}-synthetic-health-check"
  group_name                   = local.schedule_group_name
  description                  = "Runs the LeaseFlow synthetic API health check."
  schedule_expression          = var.schedule_expression
  schedule_expression_timezone = var.schedule_timezone
  state                        = var.schedule_enabled ? "ENABLED" : "DISABLED"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.synthetic_hc.arn
    role_arn = aws_iam_role.scheduler.arn
  }
}

resource "aws_cloudwatch_metric_alarm" "synthetic_hc_failure" {
  alarm_name          = "${var.name_prefix}-synthetic-health-check-failure"
  alarm_description   = "Synthetic API health check failed or stopped reporting."
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  threshold           = 1
  period              = 900
  namespace           = local.metric_namespace
  metric_name         = "HealthCheckSuccess"
  statistic           = "Minimum"
  treat_missing_data  = "breaching"
  alarm_actions       = var.alarm_action_arns

  dimensions = {
    Environment = var.environment
  }

  tags = var.tags
}
