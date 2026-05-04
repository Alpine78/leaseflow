locals {
  name_prefix            = "${var.project_name}-${var.environment}"
  frontend_hosted_origin = module.frontend_hosting.cloudfront_url
  frontend_local_origin  = trimsuffix(trimspace(var.frontend_local_origin), "/")
  frontend_allowed_origins = compact([
    local.frontend_local_origin,
    local.frontend_hosted_origin,
  ])
  frontend_callback_urls = concat(
    ["${local.frontend_local_origin}/auth/callback"],
    local.frontend_hosted_origin == "" ? [] : ["${local.frontend_hosted_origin}/auth/callback"]
  )
  frontend_logout_urls = concat(
    ["${local.frontend_local_origin}/"],
    local.frontend_hosted_origin == "" ? [] : ["${local.frontend_hosted_origin}/"]
  )
  common_tags = merge(
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    },
    var.tags
  )
}

module "network" {
  source = "../../modules/network"

  name_prefix          = local.name_prefix
  vpc_cidr             = var.vpc_cidr
  private_subnet_cidrs = var.private_subnet_cidrs
  tags                 = local.common_tags
}

module "frontend_hosting" {
  source = "../../modules/frontend_hosting"

  name_prefix = local.name_prefix
  tags        = local.common_tags
}

resource "random_password" "db_master" {
  length  = 32
  special = false
}

resource "aws_ssm_parameter" "db_password" {
  name        = var.db_password_ssm_param
  description = "Runtime DB password for ${local.name_prefix}."
  type        = "SecureString"
  value       = random_password.db_master.result

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-db-password" })
}

module "rds_postgres" {
  source = "../../modules/rds_postgres"

  name_prefix           = local.name_prefix
  private_subnet_ids    = module.network.private_subnet_ids
  rds_security_group_id = module.network.rds_security_group_id
  db_name               = var.db_name
  db_username           = var.db_username
  db_password           = random_password.db_master.result
  instance_class        = var.db_instance_class
  allocated_storage     = var.db_allocated_storage
  engine_version        = var.db_engine_version
  tags                  = local.common_tags
}

module "cognito" {
  source = "../../modules/cognito"

  aws_region              = var.aws_region
  callback_urls           = local.frontend_callback_urls
  default_redirect_uri    = local.frontend_callback_urls[0]
  hosted_ui_domain_prefix = var.cognito_hosted_ui_domain_prefix
  logout_urls             = local.frontend_logout_urls
  name_prefix             = local.name_prefix
  tags                    = local.common_tags
}

module "lambda_backend" {
  source = "../../modules/lambda_backend"

  name_prefix                                = local.name_prefix
  function_name                              = "${local.name_prefix}-backend"
  package_file                               = var.lambda_package_file
  private_subnet_ids                         = module.network.private_subnet_ids
  lambda_security_group_id                   = module.network.lambda_security_group_id
  environment                                = var.environment
  db_host                                    = module.rds_postgres.endpoint
  db_port                                    = module.rds_postgres.port
  db_name                                    = var.db_name
  db_user                                    = var.db_username
  db_password_ssm_param                      = var.db_password_ssm_param
  notification_email_delivery_enabled        = var.notification_email_delivery_enabled
  notification_email_sender                  = var.notification_email_sender
  notification_email_smtp_host               = var.notification_email_smtp_host
  notification_email_smtp_port               = var.notification_email_smtp_port
  notification_email_smtp_username_ssm_param = var.notification_email_smtp_username_ssm_param
  notification_email_smtp_password_ssm_param = var.notification_email_smtp_password_ssm_param
  notification_email_batch_size              = var.notification_email_batch_size
  notification_email_max_attempts            = var.notification_email_max_attempts
  tags                                       = local.common_tags
}

module "ses_email_foundation" {
  source = "../../modules/ses_email_foundation"

  name_prefix               = local.name_prefix
  aws_region                = var.aws_region
  sender_email              = var.ses_sender_email
  smtp_vpc_endpoint_enabled = var.ses_smtp_vpc_endpoint_enabled
  vpc_id                    = module.network.vpc_id
  private_subnet_ids        = module.network.private_subnet_ids
  lambda_security_group_id  = module.network.lambda_security_group_id
  tags                      = local.common_tags
}

module "reminder_scheduler" {
  source = "../../modules/reminder_scheduler"

  name_prefix          = local.name_prefix
  lambda_function_name = module.lambda_backend.function_name
  lambda_function_arn  = module.lambda_backend.function_arn
  schedule_expression  = var.reminder_scan_schedule_expression
  schedule_timezone    = var.reminder_scan_schedule_timezone
  scan_window_days     = var.reminder_scan_window_days
  enabled              = var.reminder_scan_enabled
  tags                 = local.common_tags
}

resource "aws_sns_topic" "baseline_alarm_notifications" {
  name = "${local.name_prefix}-baseline-alarm-notifications"

  tags = local.common_tags
}

resource "aws_sns_topic_subscription" "baseline_alarm_email" {
  count = trimspace(var.baseline_alarm_notification_email) == "" ? 0 : 1

  topic_arn = aws_sns_topic.baseline_alarm_notifications.arn
  protocol  = "email"
  endpoint  = trimspace(var.baseline_alarm_notification_email)
}

module "cloudwatch_alarms" {
  source = "../../modules/cloudwatch_alarms"

  name_prefix          = local.name_prefix
  lambda_function_name = module.lambda_backend.function_name
  api_id               = module.api_http.api_id
  api_stage_name       = var.environment
  scheduler_group_name = "default"
  scheduler_enabled    = var.reminder_scan_enabled
  alarm_action_arns    = [aws_sns_topic.baseline_alarm_notifications.arn]
  tags                 = local.common_tags
}

module "api_http" {
  source = "../../modules/api_http"

  name_prefix                 = local.name_prefix
  aws_region                  = var.aws_region
  cors_allowed_origins        = local.frontend_allowed_origins
  cors_allow_credentials      = false
  cors_allow_headers          = ["Authorization", "Content-Type"]
  cors_allow_methods          = ["GET", "OPTIONS", "PATCH", "POST"]
  stage_name                  = var.environment
  lambda_invoke_arn           = module.lambda_backend.invoke_arn
  lambda_function_name        = module.lambda_backend.function_name
  cognito_user_pool_id        = module.cognito.user_pool_id
  cognito_user_pool_client_id = module.cognito.user_pool_client_id
  tags                        = local.common_tags
}
