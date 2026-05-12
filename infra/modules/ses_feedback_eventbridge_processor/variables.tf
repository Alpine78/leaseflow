variable "name_prefix" {
  type        = string
  description = "Prefix for SES feedback EventBridge processor resources."
}

variable "lambda_function_name" {
  type        = string
  description = "Backend Lambda function name targeted by SES feedback events."
}

variable "lambda_function_arn" {
  type        = string
  description = "Backend Lambda function ARN targeted by SES feedback events."
}

variable "enabled" {
  type        = bool
  description = "Whether to create EventBridge routing for SES bounce and complaint processor events."
  default     = false
}

variable "tags" {
  type        = map(string)
  description = "Common tags."
  default     = {}
}
