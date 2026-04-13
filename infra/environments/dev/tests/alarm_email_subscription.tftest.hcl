mock_provider "aws" {
  mock_resource "aws_sns_topic" {
    defaults = {
      arn = "arn:aws:sns:eu-north-1:123456789012:leaseflow-dev-baseline-alarm-notifications"
    }
  }

  mock_data "aws_availability_zones" {
    defaults = {
      names = ["eu-north-1a", "eu-north-1b"]
    }
  }

  mock_data "aws_caller_identity" {
    defaults = {
      account_id = "123456789012"
    }
  }

  mock_data "aws_kms_alias" {
    defaults = {
      arn            = "arn:aws:kms:eu-north-1:123456789012:alias/aws/ssm"
      name           = "alias/aws/ssm"
      target_key_arn = "arn:aws:kms:eu-north-1:123456789012:key/11111111-2222-3333-4444-555555555555"
    }
  }

  mock_data "aws_region" {
    defaults = {
      region = "eu-north-1"
    }
  }
}

variables {
  lambda_package_file = "../../modules/lambda_backend/main.tf"
}

run "omits_email_subscription_by_default" {
  command = plan

  assert {
    condition     = length(aws_sns_topic_subscription.baseline_alarm_email) == 0
    error_message = "Dev alarm email subscription should be omitted by default."
  }

  assert {
    condition     = output.baseline_alarm_email_subscription_configured == false
    error_message = "Dev output should report no configured email subscription by default."
  }
}

run "creates_email_subscription_when_address_supplied" {
  command = plan

  variables {
    baseline_alarm_notification_email = "ops@example.com"
  }

  override_resource {
    target          = aws_sns_topic.baseline_alarm_notifications
    override_during = plan

    values = {
      arn = "arn:aws:sns:eu-north-1:123456789012:leaseflow-dev-baseline-alarm-notifications"
    }
  }

  assert {
    condition     = length(aws_sns_topic_subscription.baseline_alarm_email) == 1
    error_message = "Dev alarm email subscription should be created when an email is supplied."
  }

  assert {
    condition     = aws_sns_topic_subscription.baseline_alarm_email[0].protocol == "email"
    error_message = "Dev alarm subscription should use the SNS email protocol."
  }

  assert {
    condition     = aws_sns_topic_subscription.baseline_alarm_email[0].endpoint == "ops@example.com"
    error_message = "Dev alarm subscription should target the supplied email address."
  }

  assert {
    condition     = aws_sns_topic_subscription.baseline_alarm_email[0].topic_arn == aws_sns_topic.baseline_alarm_notifications.arn
    error_message = "Dev alarm subscription should attach to the baseline alarm notification topic."
  }

  assert {
    condition     = output.baseline_alarm_email_subscription_configured == true
    error_message = "Dev output should report configured email subscription when an email is supplied."
  }
}
