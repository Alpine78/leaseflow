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

variable "backup_retention_period" {
  type        = number
  description = "Automated backup retention period in days."
  default     = 1
}

variable "deletion_protection" {
  type        = bool
  description = "Whether RDS deletion protection is enabled."
  default     = false
}

variable "skip_final_snapshot" {
  type        = bool
  description = "Whether to skip the final DB snapshot when destroying the instance."
  default     = true
}

variable "final_snapshot_identifier" {
  type        = string
  description = "Final DB snapshot identifier required when skip_final_snapshot is false."
  default     = null
  nullable    = true
}

variable "tags" {
  type        = map(string)
  description = "Common tags."
  default     = {}
}
