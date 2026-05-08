variable "name_prefix" {
  description = "Prefix used in cost-control resource names."
  type        = string
}

variable "monthly_budget_enabled" {
  description = "Whether to create the optional monthly AWS cost budget."
  type        = bool
  default     = false
}

variable "monthly_budget_limit_usd" {
  description = "Monthly AWS cost budget limit in USD for paid or long-lived environments."
  type        = number
  default     = 25

  validation {
    condition     = var.monthly_budget_limit_usd > 0
    error_message = "monthly_budget_limit_usd must be greater than zero."
  }
}

variable "monthly_budget_alert_threshold_percent" {
  description = "Actual spend percentage that triggers the monthly cost budget alert."
  type        = number
  default     = 80

  validation {
    condition     = var.monthly_budget_alert_threshold_percent > 0 && var.monthly_budget_alert_threshold_percent <= 100
    error_message = "monthly_budget_alert_threshold_percent must be greater than zero and less than or equal to 100."
  }
}

variable "monthly_budget_subscriber_email_addresses" {
  description = "Operator email addresses that receive AWS Budgets alerts when the optional budget is enabled."
  type        = set(string)
  default     = []
}

variable "tags" {
  description = "Tags applied to cost-control resources."
  type        = map(string)
  default     = {}
}
