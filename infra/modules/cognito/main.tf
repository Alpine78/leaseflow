locals {
  app_client_explicit_auth_flows = [
    "ALLOW_ADMIN_USER_PASSWORD_AUTH",
    "ALLOW_CUSTOM_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH",
  ]
  app_client_read_attributes = [
    "custom:tenant_id",
    "email",
    "email_verified",
  ]
  app_client_write_attributes = [
    "email",
  ]
}

resource "aws_cognito_user_pool" "this" {
  name = "${var.name_prefix}-user-pool"

  mfa_configuration = "OFF"

  password_policy {
    minimum_length    = 12
    require_lowercase = true
    require_numbers   = true
    require_symbols   = true
    require_uppercase = true
  }

  username_attributes = ["email"]
  tags                = merge(var.tags, { Name = "${var.name_prefix}-user-pool" })

  schema {
    name                = "tenant_id"
    attribute_data_type = "String"
    mutable             = true
    required            = false

    string_attribute_constraints {
      min_length = 1
      max_length = 64
    }
  }
}

resource "aws_cognito_user_pool_client" "this" {
  name         = "${var.name_prefix}-app-client"
  user_pool_id = aws_cognito_user_pool.this.id

  generate_secret                      = false
  prevent_user_existence_errors        = "ENABLED"
  enable_token_revocation              = true
  allowed_oauth_flows_user_pool_client = false
  explicit_auth_flows                  = local.app_client_explicit_auth_flows
  read_attributes                      = local.app_client_read_attributes
  write_attributes                     = local.app_client_write_attributes
}
