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

variable "frontend_local_origin" {
  type        = string
  description = "Local browser frontend origin allowed by Cognito and API Gateway CORS."
  default     = "http://localhost:5173"
}

variable "frontend_hosted_origin" {
  type        = string
  description = "Deprecated. The hosted frontend origin is now derived from the dev CloudFront distribution."
  default     = ""

  validation {
    condition     = trimspace(var.frontend_hosted_origin) == "" || startswith(trimspace(var.frontend_hosted_origin), "https://")
    error_message = "frontend_hosted_origin must be empty or start with https://."
  }
}

variable "cognito_hosted_ui_domain_prefix" {
  type        = string
  description = "Globally unique Cognito managed Hosted UI domain prefix for the dev frontend auth flow."
}

variable "db_password_ssm_param" {
  type        = string
  description = "SSM parameter path for generated runtime DB password."
  default     = "/leaseflow/dev/db/password"
}

variable "reminder_scan_schedule_expression" {
  type        = string
  description = "EventBridge Scheduler expression for the daily reminder scan."
  default     = "cron(0 5 * * ? *)"
}

variable "reminder_scan_schedule_timezone" {
  type        = string
  description = "Timezone used by the reminder scan scheduler."
  default     = "UTC"
}

variable "reminder_scan_window_days" {
  type        = number
  description = "How many days ahead the reminder scan should look."
  default     = 7
}

variable "reminder_scan_enabled" {
  type        = bool
  description = "Whether the daily reminder scan schedule is enabled."
  default     = true
}

variable "baseline_alarm_notification_email" {
  type        = string
  description = "Optional email endpoint subscribed to dev baseline alarm SNS notifications."
  default     = ""
}

variable "ses_sender_email" {
  type        = string
  description = "Optional SES sender email identity for future dev notification email delivery validation."
  default     = ""

  validation {
    condition     = trimspace(var.ses_sender_email) == "" || can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", trimspace(var.ses_sender_email)))
    error_message = "ses_sender_email must be empty or a single email-like value."
  }
}

variable "ses_smtp_vpc_endpoint_enabled" {
  type        = bool
  description = "Whether to create the SES SMTP interface VPC endpoint for private-subnet email delivery validation."
  default     = false
}

variable "notification_email_delivery_enabled" {
  type        = bool
  description = "Whether internal notification email delivery is enabled for the dev Lambda."
  default     = false
}

variable "notification_email_sender" {
  type        = string
  description = "SES-verified sender email address used by internal notification email delivery."
  default     = ""

  validation {
    condition     = trimspace(var.notification_email_sender) == "" || can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", trimspace(var.notification_email_sender)))
    error_message = "notification_email_sender must be empty or a single email-like value."
  }
}

variable "notification_email_smtp_host" {
  type        = string
  description = "SES SMTP endpoint host used by internal notification email delivery. Empty uses the regional default."
  default     = ""
}

variable "notification_email_smtp_port" {
  type        = number
  description = "SES SMTP endpoint port used by internal notification email delivery."
  default     = 587
}

variable "notification_email_smtp_username_ssm_param" {
  type        = string
  description = "SSM SecureString parameter name containing the operator-created SES SMTP username."
  default     = ""
}

variable "notification_email_smtp_password_ssm_param" {
  type        = string
  description = "SSM SecureString parameter name containing the operator-created SES SMTP password."
  default     = ""
}

variable "notification_email_batch_size" {
  type        = number
  description = "Maximum notification email deliveries attempted per internal invocation."
  default     = 25
}

variable "notification_email_max_attempts" {
  type        = number
  description = "Maximum SMTP attempts per notification email delivery row."
  default     = 3
}

variable "tags" {
  type        = map(string)
  description = "Extra tags."
  default     = {}
}
