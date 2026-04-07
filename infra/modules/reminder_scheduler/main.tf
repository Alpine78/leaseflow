data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  schedule_name = "${var.name_prefix}-daily-reminder-scan"
  schedule_arn  = "arn:aws:scheduler:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:schedule/default/${local.schedule_name}"
}

resource "aws_iam_role" "this" {
  name = "${var.name_prefix}-reminder-scheduler-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "scheduler.amazonaws.com"
        }
        Action = "sts:AssumeRole"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
          ArnEquals = {
            "aws:SourceArn" = local.schedule_arn
          }
        }
      }
    ]
  })

  tags = merge(var.tags, { Name = "${var.name_prefix}-reminder-scheduler-role" })
}

resource "aws_iam_role_policy" "this" {
  name = "${var.name_prefix}-reminder-scheduler-policy"
  role = aws_iam_role.this.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "InvokeReminderScanLambda"
        Effect   = "Allow"
        Action   = ["lambda:InvokeFunction"]
        Resource = var.lambda_function_arn
      }
    ]
  })
}

resource "aws_scheduler_schedule" "this" {
  name                         = local.schedule_name
  description                  = "Runs the daily due reminder scan for LeaseFlow."
  schedule_expression          = var.schedule_expression
  schedule_expression_timezone = var.schedule_timezone
  state                        = var.enabled ? "ENABLED" : "DISABLED"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = var.lambda_function_arn
    role_arn = aws_iam_role.this.arn
    input = jsonencode({
      source        = "leaseflow.internal"
      "detail-type" = "scan_due_lease_reminders"
      detail = {
        days = var.scan_window_days
      }
    })
  }
}
