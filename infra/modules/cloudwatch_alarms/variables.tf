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

variable "environment" {
  description = "Deployment environment dimension used by LeaseFlow custom metric alarms."
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
  description = "Alarm action ARNs for CloudWatch alarms."
  type        = list(string)
  default     = []
}

variable "notification_email_delivery_alarms_enabled" {
  description = "Whether notification email delivery custom metric alarms should be created."
  type        = bool
  default     = true
}

variable "notification_email_delivery_attempted_count_alarm_threshold" {
  description = "Hourly attempted_count threshold for the notification email delivery send-volume alarm."
  type        = number
  default     = 100

  validation {
    condition     = var.notification_email_delivery_attempted_count_alarm_threshold > 0
    error_message = "notification_email_delivery_attempted_count_alarm_threshold must be greater than zero."
  }
}

variable "tags" {
  description = "Tags applied to alarm resources."
  type        = map(string)
  default     = {}
}
