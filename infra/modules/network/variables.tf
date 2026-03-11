variable "name_prefix" {
  type        = string
  description = "Prefix for network resource names."
}

variable "vpc_cidr" {
  type        = string
  description = "VPC CIDR block."
}

variable "private_subnet_cidrs" {
  type        = list(string)
  description = "Two private subnet CIDRs for dev."

  validation {
    condition     = length(var.private_subnet_cidrs) == 2
    error_message = "Provide exactly two private subnet CIDRs."
  }
}

variable "tags" {
  type        = map(string)
  description = "Common tags."
  default     = {}
}
