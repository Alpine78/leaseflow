variable "name_prefix" {
  description = "Prefix used in dashboard names."
  type        = string
}

variable "aws_region" {
  description = "AWS region used by dashboard metric widgets."
  type        = string
}

variable "environment" {
  description = "Deployment environment dimension used by LeaseFlow custom metrics."
  type        = string
}

variable "tags" {
  description = "Tags applied to dashboard resources."
  type        = map(string)
  default     = {}
}
