variable "name_prefix" {
  type        = string
  description = "Prefix for naming resources."
}

variable "aws_region" {
  type        = string
  description = "AWS region for JWT issuer."
}

variable "stage_name" {
  type        = string
  description = "API stage name."
}

variable "lambda_invoke_arn" {
  type        = string
  description = "Lambda invoke ARN for API integration."
}

variable "lambda_function_name" {
  type        = string
  description = "Lambda function name for invoke permissions."
}

variable "cognito_user_pool_id" {
  type        = string
  description = "Cognito user pool ID."
}

variable "cognito_user_pool_client_id" {
  type        = string
  description = "Cognito app client ID."
}

variable "cors_allowed_origins" {
  type        = list(string)
  description = "Browser origins allowed to call the HTTP API."
}

variable "cors_allow_headers" {
  type        = list(string)
  description = "Headers allowed by the HTTP API CORS configuration."
}

variable "cors_allow_methods" {
  type        = list(string)
  description = "Methods allowed by the HTTP API CORS configuration."
}

variable "cors_allow_credentials" {
  type        = bool
  description = "Whether the HTTP API CORS configuration allows browser credentials."
}

variable "tags" {
  type        = map(string)
  description = "Common tags."
  default     = {}
}
