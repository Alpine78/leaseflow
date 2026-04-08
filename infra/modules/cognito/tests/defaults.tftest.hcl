mock_provider "aws" {}

variables {
  name_prefix = "leaseflow-dev"
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
}
