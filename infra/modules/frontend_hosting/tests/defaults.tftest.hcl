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
}

variables {
  name_prefix = "leaseflow-dev"
  tags = {
    Project = "leaseflow"
  }
}

run "creates_private_cloudfront_hosted_spa" {
  command = apply

  assert {
    condition     = aws_s3_bucket.frontend.bucket == "leaseflow-dev-frontend-123456789012-eu-north-1"
    error_message = "Frontend bucket should use a globally unique account and region scoped name."
  }

  assert {
    condition = (
      aws_s3_bucket_public_access_block.frontend.block_public_acls == true
      && aws_s3_bucket_public_access_block.frontend.block_public_policy == true
      && aws_s3_bucket_public_access_block.frontend.ignore_public_acls == true
      && aws_s3_bucket_public_access_block.frontend.restrict_public_buckets == true
    )
    error_message = "Frontend bucket should block all public access."
  }

  assert {
    condition = (
      aws_cloudfront_origin_access_control.frontend.origin_access_control_origin_type == "s3"
      && aws_cloudfront_origin_access_control.frontend.signing_behavior == "always"
      && aws_cloudfront_origin_access_control.frontend.signing_protocol == "sigv4"
    )
    error_message = "CloudFront should use signed Origin Access Control for the S3 origin."
  }

  assert {
    condition     = aws_cloudfront_distribution.frontend.enabled == true
    error_message = "CloudFront distribution should be enabled."
  }

  assert {
    condition     = aws_cloudfront_distribution.frontend.default_root_object == "index.html"
    error_message = "CloudFront should serve index.html at the root."
  }

  assert {
    condition = length([
      for response in aws_cloudfront_distribution.frontend.custom_error_response : response
      if response.error_code == 403
      && response.response_code == 200
      && response.response_page_path == "/index.html"
    ]) == 1
    error_message = "CloudFront should map S3 403 responses to index.html for SPA deep links."
  }

  assert {
    condition = length([
      for response in aws_cloudfront_distribution.frontend.custom_error_response : response
      if response.error_code == 404
      && response.response_code == 200
      && response.response_page_path == "/index.html"
    ]) == 1
    error_message = "CloudFront should map 404 responses to index.html for SPA deep links."
  }

  assert {
    condition = (
      jsondecode(aws_s3_bucket_policy.frontend.policy).Statement[0].Principal.Service == "cloudfront.amazonaws.com"
      && contains(jsondecode(aws_s3_bucket_policy.frontend.policy).Statement[0].Action, "s3:GetObject")
      && jsondecode(aws_s3_bucket_policy.frontend.policy).Statement[0].Condition.StringEquals["AWS:SourceArn"] == aws_cloudfront_distribution.frontend.arn
    )
    error_message = "Bucket policy should allow only the CloudFront distribution to read objects."
  }
}
