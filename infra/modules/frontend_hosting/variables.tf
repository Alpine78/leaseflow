variable "name_prefix" {
  description = "Prefix used for frontend hosting resources."
  type        = string
}

variable "price_class" {
  description = "CloudFront price class for the hosted frontend."
  type        = string
  default     = "PriceClass_100"
}

variable "tags" {
  description = "Tags applied to frontend hosting resources."
  type        = map(string)
  default     = {}
}
