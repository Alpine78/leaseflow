variable "name_prefix" {
  type        = string
  description = "Prefix used for GitHub frontend deploy IAM resources."
}

variable "github_repository" {
  type        = string
  description = "GitHub repository allowed to assume the frontend deploy role, in owner/name format."

  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.github_repository))
    error_message = "github_repository must use owner/name format without wildcards."
  }
}

variable "github_environment" {
  type        = string
  description = "GitHub deployment environment allowed to assume the frontend deploy role."
  default     = "dev"

  validation {
    condition     = trimspace(var.github_environment) != "" && !strcontains(var.github_environment, "*")
    error_message = "github_environment must be non-empty and must not contain wildcards."
  }
}

variable "frontend_bucket_arn" {
  type        = string
  description = "S3 bucket ARN for hosted frontend assets."
}

variable "cloudfront_distribution_arn" {
  type        = string
  description = "CloudFront distribution ARN for the hosted frontend."
}

variable "tags" {
  type        = map(string)
  description = "Tags applied to GitHub frontend deploy IAM resources."
  default     = {}
}
