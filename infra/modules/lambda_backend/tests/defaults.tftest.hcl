mock_provider "aws" {
  mock_data "aws_caller_identity" {
    defaults = {
      account_id = "123456789012"
    }
  }

  mock_data "aws_region" {
    defaults = {
      region = "eu-north-1"
    }
  }

  mock_data "aws_kms_alias" {
    defaults = {
      arn            = "arn:aws:kms:eu-north-1:123456789012:alias/aws/ssm"
      name           = "alias/aws/ssm"
      target_key_arn = "arn:aws:kms:eu-north-1:123456789012:key/11111111-2222-3333-4444-555555555555"
    }
  }
}

variables {
  name_prefix              = "leaseflow-dev"
  function_name            = "leaseflow-dev-backend"
  package_file             = "main.tf"
  private_subnet_ids       = ["subnet-11111111", "subnet-22222222"]
  lambda_security_group_id = "sg-12345678"
  environment              = "dev"
  db_host                  = "leaseflow-dev-postgres.example.amazonaws.com"
  db_port                  = 5432
  db_name                  = "leaseflow"
  db_user                  = "leaseflow_admin"
  db_password_ssm_param    = "/leaseflow/dev/db/password"
  tags = {
    Project = "leaseflow"
  }
}

run "scopes_runtime_secret_permissions_to_the_db_password_parameter" {
  command = plan

  assert {
    condition     = local.lambda_policy.Statement[2].Action[0] == "ssm:GetParameter"
    error_message = "Lambda policy should allow reading the DB password parameter from SSM."
  }

  assert {
    condition     = local.lambda_policy.Statement[2].Resource == "arn:aws:ssm:eu-north-1:123456789012:parameter/leaseflow/dev/db/password"
    error_message = "SSM access should be scoped to the DB password parameter ARN."
  }

  assert {
    condition     = local.lambda_policy.Statement[3].Action[0] == "kms:Decrypt"
    error_message = "Lambda policy should allow KMS decrypt for SecureString resolution."
  }

  assert {
    condition     = local.lambda_policy.Statement[3].Resource == "arn:aws:kms:eu-north-1:123456789012:key/11111111-2222-3333-4444-555555555555"
    error_message = "KMS decrypt should be scoped to the AWS-managed key backing alias/aws/ssm."
  }

  assert {
    condition     = local.lambda_policy.Statement[3].Condition.StringEquals["kms:EncryptionContext:PARAMETER_ARN"] == "arn:aws:ssm:eu-north-1:123456789012:parameter/leaseflow/dev/db/password"
    error_message = "KMS decrypt should be limited to the DB password parameter encryption context."
  }
}
