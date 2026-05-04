data "aws_caller_identity" "current" {}
data "aws_kms_alias" "ssm" {
  name = "alias/aws/ssm"
}
data "aws_region" "current" {}

locals {
  db_password_parameter_arn = "arn:aws:ssm:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:parameter${var.db_password_ssm_param}"
  notification_email_smtp_parameter_names = compact([
    var.notification_email_smtp_username_ssm_param,
    var.notification_email_smtp_password_ssm_param
  ])
  notification_email_smtp_parameter_arns = [
    for name in local.notification_email_smtp_parameter_names :
    "arn:aws:ssm:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:parameter${name}"
  ]
  notification_email_smtp_host = (
    trimspace(var.notification_email_smtp_host) == ""
    ? "email-smtp.${data.aws_region.current.region}.amazonaws.com"
    : trimspace(var.notification_email_smtp_host)
  )
  notification_email_smtp_policy_statements = [
    for statement in [
      {
        Sid      = "ReadNotificationEmailSmtpCredentialParameters"
        Effect   = "Allow"
        Action   = ["ssm:GetParameter"]
        Resource = local.notification_email_smtp_parameter_arns
      },
      {
        Sid      = "DecryptNotificationEmailSmtpCredentialParameters"
        Effect   = "Allow"
        Action   = ["kms:Decrypt"]
        Resource = data.aws_kms_alias.ssm.target_key_arn
        Condition = {
          "ForAnyValue:StringEquals" = {
            "kms:EncryptionContext:PARAMETER_ARN" = local.notification_email_smtp_parameter_arns
          }
        }
      }
    ] : statement if length(local.notification_email_smtp_parameter_arns) > 0
  ]
  lambda_policy = {
    Version = "2012-10-17"
    Statement = concat(
      [
        {
          Sid      = "CloudWatchLogs"
          Effect   = "Allow"
          Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
          Resource = "${aws_cloudwatch_log_group.this.arn}:*"
        },
        {
          Sid    = "VpcNetworkingForLambda"
          Effect = "Allow"
          Action = [
            "ec2:CreateNetworkInterface",
            "ec2:DescribeNetworkInterfaces",
            "ec2:DeleteNetworkInterface",
            "ec2:AssignPrivateIpAddresses",
            "ec2:UnassignPrivateIpAddresses"
          ]
          Resource = "*"
        },
        {
          Sid      = "ReadDbPasswordParameter"
          Effect   = "Allow"
          Action   = ["ssm:GetParameter"]
          Resource = local.db_password_parameter_arn
        },
        {
          Sid      = "DecryptDbPasswordParameter"
          Effect   = "Allow"
          Action   = ["kms:Decrypt"]
          Resource = data.aws_kms_alias.ssm.target_key_arn
          Condition = {
            StringEquals = {
              "kms:EncryptionContext:PARAMETER_ARN" = local.db_password_parameter_arn
            }
          }
        }
      ],
      local.notification_email_smtp_policy_statements
    )
  }
}

resource "aws_iam_role" "this" {
  name = "${var.name_prefix}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = merge(var.tags, { Name = "${var.name_prefix}-lambda-role" })
}

resource "aws_iam_role_policy" "this" {
  name = "${var.name_prefix}-lambda-policy"
  role = aws_iam_role.this.id

  policy = jsonencode(local.lambda_policy)
}

resource "aws_cloudwatch_log_group" "this" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = 14
  tags              = var.tags
}

resource "aws_lambda_function" "this" {
  function_name = var.function_name
  role          = aws_iam_role.this.arn
  handler       = var.handler
  runtime       = var.runtime
  timeout       = var.timeout
  memory_size   = var.memory_size

  # Build this zip with `make build-lambda-artifact` before planning or applying.
  filename         = var.package_file
  source_code_hash = filebase64sha256(var.package_file)

  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [var.lambda_security_group_id]
  }

  environment {
    variables = {
      APP_ENV               = var.environment
      LOG_LEVEL             = var.log_level
      DB_HOST               = var.db_host
      DB_PORT               = tostring(var.db_port)
      DB_NAME               = var.db_name
      DB_USER               = var.db_user
      DB_PASSWORD_SSM_PARAM = var.db_password_ssm_param

      NOTIFICATION_EMAIL_DELIVERY_ENABLED        = tostring(var.notification_email_delivery_enabled)
      NOTIFICATION_EMAIL_SENDER                  = var.notification_email_sender
      NOTIFICATION_EMAIL_SMTP_HOST               = local.notification_email_smtp_host
      NOTIFICATION_EMAIL_SMTP_PORT               = tostring(var.notification_email_smtp_port)
      NOTIFICATION_EMAIL_SMTP_USERNAME_SSM_PARAM = var.notification_email_smtp_username_ssm_param
      NOTIFICATION_EMAIL_SMTP_PASSWORD_SSM_PARAM = var.notification_email_smtp_password_ssm_param
      NOTIFICATION_EMAIL_BATCH_SIZE              = tostring(var.notification_email_batch_size)
      NOTIFICATION_EMAIL_MAX_ATTEMPTS            = tostring(var.notification_email_max_attempts)
    }
  }

  tags = merge(var.tags, { Name = var.function_name })

  depends_on = [
    aws_cloudwatch_log_group.this
  ]
}
