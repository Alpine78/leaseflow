variable "name_prefix" {
  type        = string
  description = "Prefix for naming resources."
}

variable "function_name" {
  type        = string
  description = "Lambda function name."
}

variable "handler" {
  type        = string
  description = "Lambda handler path."
  default     = "app.handler.lambda_handler"
}

variable "runtime" {
  type        = string
  description = "Lambda runtime."
  default     = "python3.12"
}

variable "timeout" {
  type        = number
  description = "Lambda timeout in seconds."
  default     = 15
}

variable "memory_size" {
  type        = number
  description = "Lambda memory size in MB."
  default     = 256
}

variable "package_file" {
  type        = string
  description = "Path to packaged Lambda zip artifact."
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "Private subnet IDs for Lambda ENIs."
}

variable "lambda_security_group_id" {
  type        = string
  description = "Security group ID for Lambda."
}

variable "environment" {
  type        = string
  description = "Environment name."
}

variable "log_level" {
  type        = string
  description = "Application log level."
  default     = "INFO"
}

variable "db_host" {
  type        = string
  description = "RDS hostname."
}

variable "db_port" {
  type        = number
  description = "RDS port."
  default     = 5432
}

variable "db_name" {
  type        = string
  description = "Database name."
}

variable "db_user" {
  type        = string
  description = "Database user."
}

variable "db_password_ssm_param" {
  type        = string
  description = "SSM parameter path for DB password. Example: /leaseflow/dev/db/password"
}

variable "tags" {
  type        = map(string)
  description = "Common tags."
  default     = {}
}
