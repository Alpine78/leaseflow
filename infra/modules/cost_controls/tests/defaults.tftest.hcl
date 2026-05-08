mock_provider "aws" {}

variables {
  name_prefix = "leaseflow-dev"
  tags = {
    Project = "leaseflow"
  }
}

run "defaults_create_no_cost_budget" {
  command = plan

  assert {
    condition     = length(aws_budgets_budget.monthly_cost) == 0
    error_message = "Monthly cost budget should be disabled by default."
  }

  assert {
    condition     = output.monthly_budget_configured == false
    error_message = "Monthly budget configured output should be false by default."
  }
}

run "creates_optional_monthly_cost_budget_with_email_alert" {
  command = plan

  variables {
    monthly_budget_enabled                    = true
    monthly_budget_limit_usd                  = 50
    monthly_budget_alert_threshold_percent    = 75
    monthly_budget_subscriber_email_addresses = ["operator@example.test"]
  }

  assert {
    condition     = length(aws_budgets_budget.monthly_cost) == 1
    error_message = "Monthly cost budget should be created when enabled."
  }

  assert {
    condition     = aws_budgets_budget.monthly_cost[0].name == "leaseflow-dev-monthly-cost"
    error_message = "Monthly cost budget should use the expected safe name."
  }

  assert {
    condition     = aws_budgets_budget.monthly_cost[0].budget_type == "COST"
    error_message = "Monthly budget should track cost."
  }

  assert {
    condition     = aws_budgets_budget.monthly_cost[0].time_unit == "MONTHLY"
    error_message = "Monthly budget should use a monthly time unit."
  }

  assert {
    condition     = aws_budgets_budget.monthly_cost[0].limit_amount == "50"
    error_message = "Monthly budget should use the configured USD amount."
  }

  assert {
    condition     = aws_budgets_budget.monthly_cost[0].limit_unit == "USD"
    error_message = "Monthly budget should use USD."
  }

  assert {
    condition     = length(aws_budgets_budget.monthly_cost[0].notification) == 1
    error_message = "Monthly budget should include a notification when subscribers are configured."
  }

  assert {
    condition = length([
      for notification in aws_budgets_budget.monthly_cost[0].notification : notification
      if notification.notification_type == "ACTUAL"
    ]) == 1
    error_message = "Monthly budget notification should track actual spend."
  }

  assert {
    condition = length([
      for notification in aws_budgets_budget.monthly_cost[0].notification : notification
      if notification.threshold == 75
    ]) == 1
    error_message = "Monthly budget notification should use the configured threshold."
  }

  assert {
    condition = length([
      for notification in aws_budgets_budget.monthly_cost[0].notification : notification
      if notification.threshold_type == "PERCENTAGE"
    ]) == 1
    error_message = "Monthly budget notification should use a percentage threshold."
  }

  assert {
    condition     = output.monthly_budget_configured == true
    error_message = "Monthly budget configured output should be true when enabled."
  }
}

run "budget_name_excludes_sensitive_identifiers" {
  command = plan

  variables {
    monthly_budget_enabled                    = true
    monthly_budget_subscriber_email_addresses = ["operator@example.test"]
  }

  assert {
    condition = alltrue([
      for forbidden_value in [
        "tenant",
        "recipient",
        "contact",
        "notification",
        "smtp",
        "ssm",
        "db",
        "credential"
      ] :
      !strcontains(lower(aws_budgets_budget.monthly_cost[0].name), forbidden_value)
    ])
    error_message = "Monthly budget name should not contain sensitive or tenant-specific identifiers."
  }
}

run "enabled_budget_requires_alert_subscriber" {
  command = plan

  variables {
    monthly_budget_enabled = true
  }

  expect_failures = [
    aws_budgets_budget.monthly_cost
  ]
}
