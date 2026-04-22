mock_provider "aws" {}

variables {
  aws_region              = "eu-north-1"
  callback_urls           = ["http://localhost:5173/auth/callback"]
  default_redirect_uri    = "http://localhost:5173/auth/callback"
  hosted_ui_domain_prefix = "leaseflow-dev-example"
  logout_urls             = ["http://localhost:5173/"]
  name_prefix             = "leaseflow-dev"
  tags = {
    Project = "leaseflow"
  }
}

run "exposes_tenant_id_claim_for_api_auth" {
  command = apply

  assert {
    condition = length([
      for attribute in aws_cognito_user_pool.this.schema : attribute
      if attribute.name == "tenant_id"
      && attribute.attribute_data_type == "String"
      && attribute.mutable == true
      && attribute.required == false
      && attribute.string_attribute_constraints[0].min_length == "1"
      && attribute.string_attribute_constraints[0].max_length == "64"
    ]) == 1
    error_message = "User pool should define tenant_id as an optional mutable string custom attribute."
  }

  assert {
    condition     = try(contains(aws_cognito_user_pool_client.this.explicit_auth_flows, "ALLOW_ADMIN_USER_PASSWORD_AUTH"), false)
    error_message = "App client should allow ADMIN_USER_PASSWORD_AUTH for deployed smoke testing."
  }

  assert {
    condition     = aws_cognito_user_pool_client.this.allowed_oauth_flows_user_pool_client == true
    error_message = "App client should enable OAuth flows for Hosted UI browser login."
  }

  assert {
    condition     = try(contains(aws_cognito_user_pool_client.this.allowed_oauth_flows, "code"), false)
    error_message = "App client should allow the OAuth authorization code flow."
  }

  assert {
    condition     = try(contains(aws_cognito_user_pool_client.this.allowed_oauth_scopes, "openid"), false)
    error_message = "App client should allow the openid OAuth scope."
  }

  assert {
    condition     = try(contains(aws_cognito_user_pool_client.this.allowed_oauth_scopes, "email"), false)
    error_message = "App client should allow the email OAuth scope."
  }

  assert {
    condition     = try(contains(aws_cognito_user_pool_client.this.supported_identity_providers, "COGNITO"), false)
    error_message = "App client should use Cognito as the supported identity provider."
  }

  assert {
    condition     = try(contains(aws_cognito_user_pool_client.this.callback_urls, "http://localhost:5173/auth/callback"), false)
    error_message = "App client should include the local frontend callback URL."
  }

  assert {
    condition     = try(contains(aws_cognito_user_pool_client.this.logout_urls, "http://localhost:5173/"), false)
    error_message = "App client should include the local frontend logout URL."
  }

  assert {
    condition     = aws_cognito_user_pool_client.this.default_redirect_uri == "http://localhost:5173/auth/callback"
    error_message = "App client should use the local callback URL as the default redirect URI."
  }

  assert {
    condition     = try(contains(aws_cognito_user_pool_client.this.read_attributes, "custom:tenant_id"), false)
    error_message = "App client should expose custom:tenant_id as a readable attribute."
  }

  assert {
    condition     = try(contains(aws_cognito_user_pool_client.this.read_attributes, "email"), false)
    error_message = "App client should expose email as a readable attribute."
  }

  assert {
    condition     = try(contains(aws_cognito_user_pool_client.this.write_attributes, "custom:tenant_id"), false) == false
    error_message = "App client should not allow writing custom:tenant_id."
  }

  assert {
    condition     = aws_cognito_user_pool_domain.this.domain == "leaseflow-dev-example"
    error_message = "Cognito should create the managed Hosted UI domain from the configured prefix."
  }
}
