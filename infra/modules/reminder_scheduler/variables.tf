variable "name_prefix" {
  type        = string
  description = "Prefix for naming resources."
}

variable "lambda_function_name" {
  type        = string
  description = "Lambda function name."
}

variable "lambda_function_arn" {
  type        = string
  description = "Lambda function ARN."
}

variable "schedule_expression" {
  type        = string
  description = "Scheduler expression."
}

variable "schedule_timezone" {
  type        = string
  description = "Timezone for the schedule expression."
}

variable "scan_window_days" {
  type        = number
  description = "How many days ahead the reminder scan should check."
}

variable "enabled" {
  type        = bool
  description = "Whether the scheduler should be enabled."
}

variable "tags" {
  type        = map(string)
  description = "Common tags."
  default     = {}
}
