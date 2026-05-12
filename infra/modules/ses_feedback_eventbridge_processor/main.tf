resource "aws_cloudwatch_event_rule" "ses_feedback" {
  count = var.enabled ? 1 : 0

  name        = "${var.name_prefix}-ses-feedback"
  description = "Routes SES bounce and complaint feedback events to the LeaseFlow backend."

  event_pattern = jsonencode({
    source        = ["aws.ses"]
    "detail-type" = ["Email Bounced", "Email Complaint Received"]
  })

  tags = merge(var.tags, { Name = "${var.name_prefix}-ses-feedback" })
}

resource "aws_cloudwatch_event_target" "lambda" {
  count = var.enabled ? 1 : 0

  rule = aws_cloudwatch_event_rule.ses_feedback[0].name
  arn  = var.lambda_function_arn
}

resource "aws_lambda_permission" "eventbridge" {
  count = var.enabled ? 1 : 0

  statement_id  = "AllowExecutionFromSesFeedbackEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ses_feedback[0].arn
}
