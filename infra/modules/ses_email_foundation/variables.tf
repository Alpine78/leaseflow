variable "name_prefix" {
  type        = string
  description = "Prefix for SES email foundation resources."
}

variable "aws_region" {
  type        = string
  description = "AWS region used to build the SES SMTP VPC endpoint service name."
}

variable "sender_email" {
  type        = string
  description = "Optional verified SES sender email identity for dev email delivery validation."
  default     = ""

  validation {
    condition     = trimspace(var.sender_email) == "" || can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", trimspace(var.sender_email)))
    error_message = "sender_email must be empty or a single email-like value."
  }
}

variable "smtp_vpc_endpoint_enabled" {
  type        = bool
  description = "Whether to create the SES SMTP interface VPC endpoint. Disabled by default to avoid idle dev cost."
  default     = false
}

variable "vpc_id" {
  type        = string
  description = "VPC ID for the optional SES SMTP interface endpoint."
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "Private subnet IDs for the optional SES SMTP interface endpoint."

  validation {
    condition     = length(var.private_subnet_ids) > 0
    error_message = "Provide at least one private subnet ID."
  }
}

variable "lambda_security_group_id" {
  type        = string
  description = "Lambda security group allowed to connect to the optional SES SMTP interface endpoint."
}

variable "tags" {
  type        = map(string)
  description = "Common tags."
  default     = {}
}
