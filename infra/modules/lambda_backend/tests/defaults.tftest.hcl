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
  db_password_secret_arn   = "arn:aws:secretsmanager:eu-north-1:123456789012:secret:leaseflow-dev-rds-master"
  tags = {
    Project = "leaseflow"
  }
}

run "scopes_runtime_secret_permissions_to_the_db_password_secret" {
  command = plan

  assert {
    condition     = local.lambda_policy.Statement[2].Action[0] == "secretsmanager:GetSecretValue"
    error_message = "Lambda policy should allow reading the DB password secret from Secrets Manager."
  }

  assert {
    condition     = local.lambda_policy.Statement[2].Resource == "arn:aws:secretsmanager:eu-north-1:123456789012:secret:leaseflow-dev-rds-master"
    error_message = "Secrets Manager access should be scoped to the RDS master user secret ARN."
  }
}

run "configures_notification_email_delivery_environment_without_secret_values" {
  command = plan

  variables {
    notification_email_delivery_enabled        = true
    notification_email_sender                  = "sender@example.test"
    notification_email_smtp_host               = "email-smtp.eu-north-1.amazonaws.com"
    notification_email_smtp_port               = 587
    notification_email_smtp_username_ssm_param = "/leaseflow/dev/notification-email/smtp/username"
    notification_email_smtp_password_ssm_param = "/leaseflow/dev/notification-email/smtp/password"
    notification_email_configuration_set       = "leaseflow-dev-events"
    notification_email_batch_size              = 10
    notification_email_max_attempts            = 5
  }

  assert {
    condition     = aws_lambda_function.this.environment[0].variables.NOTIFICATION_EMAIL_DELIVERY_ENABLED == "true"
    error_message = "Lambda should receive the notification email delivery enablement flag."
  }

  assert {
    condition     = aws_lambda_function.this.environment[0].variables.NOTIFICATION_EMAIL_SENDER == "sender@example.test"
    error_message = "Lambda should receive the configured sender address."
  }

  assert {
    condition     = aws_lambda_function.this.environment[0].variables.NOTIFICATION_EMAIL_SMTP_HOST == "email-smtp.eu-north-1.amazonaws.com"
    error_message = "Lambda should receive the configured SMTP host."
  }

  assert {
    condition     = aws_lambda_function.this.environment[0].variables.NOTIFICATION_EMAIL_SMTP_USERNAME_SSM_PARAM == "/leaseflow/dev/notification-email/smtp/username"
    error_message = "Lambda should receive the SMTP username parameter name, not the secret value."
  }

  assert {
    condition     = aws_lambda_function.this.environment[0].variables.NOTIFICATION_EMAIL_SMTP_PASSWORD_SSM_PARAM == "/leaseflow/dev/notification-email/smtp/password"
    error_message = "Lambda should receive the SMTP password parameter name, not the secret value."
  }

  assert {
    condition     = aws_lambda_function.this.environment[0].variables.NOTIFICATION_EMAIL_CONFIGURATION_SET == "leaseflow-dev-events"
    error_message = "Lambda should receive the optional SES configuration set name."
  }
}

run "scopes_notification_email_smtp_secret_permissions_to_configured_parameters" {
  command = plan

  variables {
    notification_email_smtp_username_ssm_param = "/leaseflow/dev/notification-email/smtp/username"
    notification_email_smtp_password_ssm_param = "/leaseflow/dev/notification-email/smtp/password"
  }

  assert {
    condition = contains(
      local.lambda_policy.Statement[3].Action,
      "ssm:GetParameter",
    )
    error_message = "Lambda policy should allow reading configured SMTP credential parameters."
  }

  assert {
    condition = alltrue([
      for arn in [
        "arn:aws:ssm:eu-north-1:123456789012:parameter/leaseflow/dev/notification-email/smtp/username",
        "arn:aws:ssm:eu-north-1:123456789012:parameter/leaseflow/dev/notification-email/smtp/password",
      ] : contains(local.lambda_policy.Statement[3].Resource, arn)
    ])
    error_message = "SMTP SSM access should be scoped to the configured credential parameter ARNs."
  }

  assert {
    condition     = local.lambda_policy.Statement[4].Action[0] == "kms:Decrypt"
    error_message = "Lambda policy should allow KMS decrypt for SMTP SecureString resolution."
  }

  assert {
    condition = alltrue([
      for arn in [
        "arn:aws:ssm:eu-north-1:123456789012:parameter/leaseflow/dev/notification-email/smtp/username",
        "arn:aws:ssm:eu-north-1:123456789012:parameter/leaseflow/dev/notification-email/smtp/password",
        ] : contains(
        local.lambda_policy.Statement[4].Condition["ForAnyValue:StringEquals"]["kms:EncryptionContext:PARAMETER_ARN"],
        arn,
      )
    ])
    error_message = "KMS decrypt should be limited to configured SMTP SSM parameter encryption contexts."
  }
}
