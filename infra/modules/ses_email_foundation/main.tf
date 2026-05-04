locals {
  sender_email = trimspace(var.sender_email)
}

resource "aws_sesv2_email_identity" "sender" {
  count = local.sender_email == "" ? 0 : 1

  email_identity = local.sender_email

  tags = var.tags
}

resource "aws_security_group" "ses_smtp_vpce" {
  count = var.smtp_vpc_endpoint_enabled ? 1 : 0

  name        = "${var.name_prefix}-ses-smtp-vpce-sg"
  description = "LeaseFlow SES SMTP VPC endpoint security group"
  vpc_id      = var.vpc_id

  ingress {
    description     = "SMTP submission from Lambda SG"
    from_port       = 587
    to_port         = 587
    protocol        = "tcp"
    security_groups = [var.lambda_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "${var.name_prefix}-ses-smtp-vpce-sg" })
}

resource "aws_vpc_endpoint" "ses_smtp" {
  count = var.smtp_vpc_endpoint_enabled ? 1 : 0

  vpc_id              = var.vpc_id
  service_name        = "com.amazonaws.${var.aws_region}.email-smtp"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = var.private_subnet_ids
  security_group_ids  = [aws_security_group.ses_smtp_vpce[0].id]

  tags = merge(var.tags, { Name = "${var.name_prefix}-ses-smtp-vpce" })
}
