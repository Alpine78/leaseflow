variable "aws_region" {
  type        = string
  description = "AWS region."
  default     = "eu-north-1"
}

variable "project_name" {
  type        = string
  description = "Project name."
  default     = "leaseflow"
}

variable "environment" {
  type        = string
  description = "Environment name."
  default     = "dev"
}

variable "vpc_cidr" {
  type        = string
  description = "VPC CIDR."
  default     = "10.20.0.0/16"
}

variable "private_subnet_cidrs" {
  type        = list(string)
  description = "Two private subnets."
  default     = ["10.20.1.0/24", "10.20.2.0/24"]
}

variable "db_name" {
  type        = string
  description = "RDS database name."
  default     = "leaseflow"
}

variable "db_username" {
  type        = string
  description = "RDS admin username."
  default     = "leaseflow_admin"
}

variable "db_instance_class" {
  type        = string
  description = "RDS instance class."
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  type        = number
  description = "RDS storage in GB."
  default     = 20
}

variable "db_engine_version" {
  type        = string
  description = "PostgreSQL version."
  default     = "15.17"
}

variable "lambda_package_file" {
  type        = string
  description = "Path to Lambda deployment zip."
  default     = "../../../dist/leaseflow-backend.zip"
}

variable "db_password_ssm_param" {
  type        = string
  description = "SSM parameter path for generated runtime DB password."
  default     = "/leaseflow/dev/db/password"
}

variable "tags" {
  type        = map(string)
  description = "Extra tags."
  default     = {}
}
