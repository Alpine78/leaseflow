output "state_bucket_name" {
  description = "S3 bucket name for Terraform remote state."
  value       = aws_s3_bucket.terraform_state.bucket
}

output "state_bucket_arn" {
  description = "S3 bucket ARN for Terraform remote state."
  value       = aws_s3_bucket.terraform_state.arn
}

output "dev_state_key" {
  description = "S3 object key for the dev Terraform state."
  value       = local.dev_state_key
}

output "dev_backend_config" {
  description = "Copyable backend config for infra/environments/dev/backend.hcl."
  value       = <<-EOT
bucket       = "${aws_s3_bucket.terraform_state.bucket}"
key          = "${local.dev_state_key}"
region       = "${var.aws_region}"
encrypt      = true
use_lockfile = true
EOT
}
