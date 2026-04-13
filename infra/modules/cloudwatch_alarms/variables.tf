variable "name_prefix" {
  description = "Prefix used in alarm names."
  type        = string
}

variable "lambda_function_name" {
  description = "Backend Lambda function name."
  type        = string
}

variable "api_id" {
  description = "HTTP API ID."
  type        = string
}

variable "api_stage_name" {
  description = "HTTP API stage name."
  type        = string
}

variable "scheduler_group_name" {
  description = "EventBridge Scheduler schedule group name."
  type        = string
}

variable "scheduler_enabled" {
  description = "Whether the reminder scheduler alarm should be created."
  type        = bool
}

variable "alarm_action_arns" {
  description = "Alarm action ARNs for baseline CloudWatch alarms."
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Tags applied to alarm resources."
  type        = map(string)
  default     = {}
}
