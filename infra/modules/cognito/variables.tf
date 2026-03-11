variable "name_prefix" {
  type        = string
  description = "Prefix for Cognito resources."
}

variable "tags" {
  type        = map(string)
  description = "Common tags."
  default     = {}
}
