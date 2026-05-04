mock_provider "aws" {}

variables {
  name_prefix              = "leaseflow-dev"
  aws_region               = "eu-north-1"
  vpc_id                   = "vpc-12345678"
  private_subnet_ids       = ["subnet-private-1", "subnet-private-2"]
  lambda_security_group_id = "sg-lambda"
  tags = {
    Project = "leaseflow"
  }
}

run "defaults_create_no_ses_identity_or_smtp_endpoint" {
  command = plan

  assert {
    condition     = length(aws_sesv2_email_identity.sender) == 0
    error_message = "SES sender identity should not be created by default."
  }

  assert {
    condition     = length(aws_security_group.ses_smtp_vpce) == 0
    error_message = "SES SMTP endpoint security group should not be created by default."
  }

  assert {
    condition     = length(aws_vpc_endpoint.ses_smtp) == 0
    error_message = "SES SMTP VPC endpoint should not be created by default."
  }

  assert {
    condition     = output.sender_identity_configured == false
    error_message = "Sender identity output should be false by default."
  }

  assert {
    condition     = output.smtp_vpc_endpoint_enabled == false
    error_message = "SMTP VPC endpoint output should be false by default."
  }
}

run "creates_sender_identity_when_email_configured" {
  command = plan

  variables {
    sender_email = "sender@example.test"
  }

  assert {
    condition     = length(aws_sesv2_email_identity.sender) == 1
    error_message = "SES sender identity should be created when sender_email is configured."
  }

  assert {
    condition     = aws_sesv2_email_identity.sender[0].email_identity == "sender@example.test"
    error_message = "SES sender identity should use the configured email."
  }

  assert {
    condition     = length(aws_vpc_endpoint.ses_smtp) == 0
    error_message = "Configuring sender_email should not enable the SMTP VPC endpoint."
  }

  assert {
    condition     = output.sender_identity_configured == true
    error_message = "Sender identity output should be true when sender_email is configured."
  }
}

run "creates_opt_in_smtp_private_endpoint" {
  command = plan

  variables {
    smtp_vpc_endpoint_enabled = true
  }

  assert {
    condition     = length(aws_security_group.ses_smtp_vpce) == 1
    error_message = "SES SMTP endpoint security group should be created when endpoint is enabled."
  }

  assert {
    condition = length([
      for rule in aws_security_group.ses_smtp_vpce[0].ingress : rule
      if rule.description == "SMTP submission from Lambda SG"
      && rule.from_port == 587
      && rule.to_port == 587
      && rule.protocol == "tcp"
      && contains(rule.security_groups, var.lambda_security_group_id)
    ]) == 1
    error_message = "SES SMTP endpoint security group should allow TCP 587 from the Lambda security group only."
  }

  assert {
    condition     = length(aws_vpc_endpoint.ses_smtp) == 1
    error_message = "SES SMTP VPC endpoint should be created when enabled."
  }

  assert {
    condition     = aws_vpc_endpoint.ses_smtp[0].vpc_endpoint_type == "Interface"
    error_message = "SES SMTP VPC endpoint should be an interface endpoint."
  }

  assert {
    condition     = aws_vpc_endpoint.ses_smtp[0].service_name == "com.amazonaws.eu-north-1.email-smtp"
    error_message = "SES SMTP VPC endpoint should target the regional email-smtp service."
  }

  assert {
    condition     = aws_vpc_endpoint.ses_smtp[0].private_dns_enabled == true
    error_message = "SES SMTP VPC endpoint should enable private DNS."
  }

  assert {
    condition = alltrue([
      for subnet_id in var.private_subnet_ids :
      contains(aws_vpc_endpoint.ses_smtp[0].subnet_ids, subnet_id)
    ])
    error_message = "SES SMTP VPC endpoint should use the configured private subnets."
  }

  assert {
    condition     = output.smtp_vpc_endpoint_enabled == true
    error_message = "SMTP VPC endpoint output should be true when endpoint is enabled."
  }
}
