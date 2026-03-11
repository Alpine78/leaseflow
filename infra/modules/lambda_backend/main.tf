data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

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

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
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
        Resource = "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter${var.db_password_ssm_param}"
      }
    ]
  })
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

  # TODO: replace local file packaging with CI build artifact publishing.
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
      AWS_REGION            = data.aws_region.current.name
    }
  }

  tags = merge(var.tags, { Name = var.function_name })

  depends_on = [
    aws_cloudwatch_log_group.this
  ]
}
