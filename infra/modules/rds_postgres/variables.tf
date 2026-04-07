variable "name_prefix" {
  type        = string
  description = "Prefix for resource names."
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "Private subnet IDs for DB subnet group."
}

variable "rds_security_group_id" {
  type        = string
  description = "Security group allowed to protect RDS."
}

variable "db_name" {
  type        = string
  description = "Database name."
}

variable "db_username" {
  type        = string
  description = "Master username."
}

variable "db_password" {
  type        = string
  description = "Master password."
  sensitive   = true
}

variable "instance_class" {
  type        = string
  description = "RDS instance class."
  default     = "db.t3.micro"
}

variable "allocated_storage" {
  type        = number
  description = "Allocated storage in GB."
  default     = 20
}

variable "engine_version" {
  type        = string
  description = "PostgreSQL engine version."
  default     = "15.17"
}

variable "tags" {
  type        = map(string)
  description = "Common tags."
  default     = {}
}
