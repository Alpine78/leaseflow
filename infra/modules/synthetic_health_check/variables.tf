variable "name_prefix" {
  type        = string
  description = "Resource name prefix."
}

variable "user_pool_id" {
  type        = string
  description = "Cognito user pool ID."
}

variable "user_pool_client_id" {
  type        = string
  description = "Cognito app client ID."
}

variable "api_url" {
  type        = string
  description = "API stage invoke URL."
}

variable "environment" {
  type        = string
  description = "Environment name (used as a CloudWatch metric dimension)."
}

variable "alarm_action_arns" {
  type        = list(string)
  description = "SNS topic ARNs to notify when the health check alarm fires."
}

variable "schedule_enabled" {
  type        = bool
  default     = true
  description = "Whether the synthetic health check EventBridge Scheduler is enabled. When false, the Lambda and supporting resources remain but are not invoked automatically."
}

variable "schedule_expression" {
  type        = string
  default     = "rate(15 minutes)"
  description = "EventBridge Scheduler schedule expression."
}

variable "schedule_timezone" {
  type        = string
  default     = "UTC"
  description = "IANA timezone for the schedule expression."
}

variable "tags" {
  type        = map(string)
  default     = {}
  description = "Tags to apply to all resources."
}
