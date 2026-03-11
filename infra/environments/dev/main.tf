locals {
  name_prefix = "${var.project_name}-${var.environment}"
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

module "rds_postgres" {
  source = "../../modules/rds_postgres"

  name_prefix           = local.name_prefix
  private_subnet_ids    = module.network.private_subnet_ids
  rds_security_group_id = module.network.rds_security_group_id
  db_name               = var.db_name
  db_username           = var.db_username
  db_password           = var.db_password
  instance_class        = var.db_instance_class
  allocated_storage     = var.db_allocated_storage
  engine_version        = var.db_engine_version
  tags                  = local.common_tags
}

module "cognito" {
  source = "../../modules/cognito"

  name_prefix = local.name_prefix
  tags        = local.common_tags
}

module "lambda_backend" {
  source = "../../modules/lambda_backend"

  name_prefix              = local.name_prefix
  function_name            = "${local.name_prefix}-backend"
  package_file             = var.lambda_package_file
  private_subnet_ids       = module.network.private_subnet_ids
  lambda_security_group_id = module.network.lambda_security_group_id
  environment              = var.environment
  db_host                  = module.rds_postgres.endpoint
  db_port                  = module.rds_postgres.port
  db_name                  = var.db_name
  db_user                  = var.db_username
  db_password_ssm_param    = var.db_password_ssm_param
  tags                     = local.common_tags
}

module "api_http" {
  source = "../../modules/api_http"

  name_prefix                 = local.name_prefix
  aws_region                  = var.aws_region
  stage_name                  = var.environment
  lambda_invoke_arn           = module.lambda_backend.invoke_arn
  lambda_function_name        = module.lambda_backend.function_name
  cognito_user_pool_id        = module.cognito.user_pool_id
  cognito_user_pool_client_id = module.cognito.user_pool_client_id
  tags                        = local.common_tags
}
