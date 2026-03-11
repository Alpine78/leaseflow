output "api_id" {
  value       = aws_apigatewayv2_api.this.id
  description = "HTTP API ID."
}

output "api_endpoint" {
  value       = aws_apigatewayv2_api.this.api_endpoint
  description = "Base API endpoint URL."
}

output "stage_invoke_url" {
  value       = aws_apigatewayv2_stage.this.invoke_url
  description = "Stage invoke URL."
}
