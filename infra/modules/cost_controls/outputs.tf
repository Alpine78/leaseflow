output "monthly_budget_configured" {
  description = "Whether the optional monthly cost budget is configured."
  value       = length(aws_budgets_budget.monthly_cost) > 0
}

output "monthly_budget_name" {
  description = "Optional monthly cost budget name."
  value       = try(aws_budgets_budget.monthly_cost[0].name, null)
}
