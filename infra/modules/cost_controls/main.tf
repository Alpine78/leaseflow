resource "aws_budgets_budget" "monthly_cost" {
  count = var.monthly_budget_enabled ? 1 : 0

  name         = "${var.name_prefix}-monthly-cost"
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_budget_limit_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  dynamic "notification" {
    for_each = length(var.monthly_budget_subscriber_email_addresses) > 0 ? [1] : []

    content {
      comparison_operator        = "GREATER_THAN"
      notification_type          = "ACTUAL"
      threshold                  = var.monthly_budget_alert_threshold_percent
      threshold_type             = "PERCENTAGE"
      subscriber_email_addresses = var.monthly_budget_subscriber_email_addresses
    }
  }

  tags = var.tags

  lifecycle {
    precondition {
      condition     = length(var.monthly_budget_subscriber_email_addresses) > 0
      error_message = "monthly_budget_subscriber_email_addresses must contain at least one operator email address when monthly_budget_enabled is true."
    }
  }
}
