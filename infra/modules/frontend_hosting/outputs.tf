output "bucket_name" {
  description = "S3 bucket name for frontend assets."
  value       = aws_s3_bucket.frontend.bucket
}

output "bucket_arn" {
  description = "S3 bucket ARN for frontend assets."
  value       = aws_s3_bucket.frontend.arn
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID for the hosted frontend."
  value       = aws_cloudfront_distribution.frontend.id
}

output "cloudfront_distribution_arn" {
  description = "CloudFront distribution ARN for the hosted frontend."
  value       = aws_cloudfront_distribution.frontend.arn
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name."
  value       = aws_cloudfront_distribution.frontend.domain_name
}

output "cloudfront_url" {
  description = "CloudFront HTTPS URL for the hosted frontend."
  value       = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}
