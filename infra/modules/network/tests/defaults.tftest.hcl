mock_provider "aws" {
  mock_data "aws_region" {
    defaults = {
      region = "eu-north-1"
    }
  }

  mock_data "aws_availability_zones" {
    defaults = {
      names = ["eu-north-1a", "eu-north-1b"]
    }
  }
}

variables {
  name_prefix          = "leaseflow-dev"
  vpc_cidr             = "10.20.0.0/16"
  private_subnet_cidrs = ["10.20.1.0/24", "10.20.2.0/24"]
  tags = {
    Project = "leaseflow"
  }
}

run "creates_private_interface_endpoints_for_runtime_secrets" {
  command = plan

  assert {
    condition     = aws_vpc_endpoint.ssm.vpc_endpoint_type == "Interface"
    error_message = "SSM should use an interface VPC endpoint."
  }

  assert {
    condition     = aws_vpc_endpoint.ssm.service_name == "com.amazonaws.eu-north-1.ssm"
    error_message = "SSM endpoint should target the regional Systems Manager service."
  }

  assert {
    condition     = aws_vpc_endpoint.ssm.private_dns_enabled == true
    error_message = "SSM endpoint should enable private DNS."
  }

  assert {
    condition     = length(aws_subnet.private) == 2
    error_message = "Network module should create exactly two private subnets for interface endpoints."
  }

  assert {
    condition     = aws_vpc_endpoint.kms.vpc_endpoint_type == "Interface"
    error_message = "KMS should use an interface VPC endpoint."
  }

  assert {
    condition     = aws_vpc_endpoint.kms.service_name == "com.amazonaws.eu-north-1.kms"
    error_message = "KMS endpoint should target the regional KMS service."
  }

  assert {
    condition     = aws_vpc_endpoint.kms.private_dns_enabled == true
    error_message = "KMS endpoint should enable private DNS."
  }

  assert {
    condition     = length(aws_subnet.private) == 2
    error_message = "Network module should create exactly two private subnets for interface endpoints."
  }

  assert {
    condition = length([
      for rule in aws_security_group.private_service_endpoints.ingress : rule
      if rule.description == "HTTPS from Lambda SG"
      && rule.from_port == 443
      && rule.to_port == 443
      && rule.protocol == "tcp"
      && length(rule.security_groups) == 1
    ]) == 1
    error_message = "Endpoint security group should allow one HTTPS ingress rule from the Lambda security group."
  }
}
