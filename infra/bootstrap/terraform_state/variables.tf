variable "aws_region" {
  type        = string
  description = "AWS region for the Terraform state bucket."
  default     = "eu-north-1"
}

variable "project_name" {
  type        = string
  description = "Project name used in state bucket and key naming."
  default     = "leaseflow"
}

variable "environment" {
  type        = string
  description = "Environment name used for the dev state key."
  default     = "dev"
}

variable "state_bucket_name" {
  type        = string
  description = "Optional explicit Terraform state bucket name. Leave empty to derive one from project, account, and region."
  default     = ""
}

variable "tags" {
  type        = map(string)
  description = "Extra tags."
  default     = {}
}
