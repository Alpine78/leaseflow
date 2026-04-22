variable "name_prefix" {
  type        = string
  description = "Prefix for Cognito resources."
}

variable "aws_region" {
  type        = string
  description = "AWS region used to build the Cognito Hosted UI URL."
}

variable "hosted_ui_domain_prefix" {
  type        = string
  description = "Globally unique Cognito managed Hosted UI domain prefix."
}

variable "callback_urls" {
  type        = list(string)
  description = "Allowed OAuth callback URLs for the browser frontend."
}

variable "logout_urls" {
  type        = list(string)
  description = "Allowed OAuth logout return URLs for the browser frontend."
}

variable "default_redirect_uri" {
  type        = string
  description = "Default redirect URI for the Cognito app client."
}

variable "tags" {
  type        = map(string)
  description = "Common tags."
  default     = {}
}
