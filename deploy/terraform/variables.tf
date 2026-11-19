variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "image" {
  type        = string
  description = "Container image built from this repo's Dockerfile."
}

variable "network" {
  type        = string
  default     = ""
  description = "VPC network that can reach a private Gateway. Leave empty for a Gateway with a public address."
}

variable "subnet" {
  type        = string
  default     = ""
  description = "Subnet used for Direct VPC egress. Required when network is set."

  validation {
    condition     = (var.network == "") == (var.subnet == "")
    error_message = "Set both network and subnet, or neither."
  }
}

variable "akeyless_gateway_url" {
  type        = string
  description = "Private Gateway URL with ARA enabled, e.g. https://10.0.0.5:8000. Not api.akeyless.io."

  validation {
    condition     = !can(regex("api\\.akeyless\\.io", lower(var.akeyless_gateway_url)))
    error_message = "ARA needs a customer Gateway; the public SaaS API (api.akeyless.io) is not supported."
  }
}

variable "akeyless_access_id" {
  type        = string
  description = "Access ID of the Akeyless GCP auth method bound to the service account."
}

variable "akeyless_gcp_audience" {
  type    = string
  default = "akeyless.io"
}

variable "akeyless_default_secret_name" {
  type    = string
  default = ""
}

variable "invoker_members" {
  type        = list(string)
  description = "IAM members allowed to call the service (serviceAccount:..., user:..., group:...)."

  validation {
    condition = alltrue([
      for m in var.invoker_members : !contains(["allUsers", "allAuthenticatedUsers"], m)
    ])
    error_message = "Public invokers are not allowed: anyone who can call the service acts with its Akeyless role."
  }
}

variable "service_name" {
  type    = string
  default = "akeyless-rta"
}

variable "service_account_name" {
  type    = string
  default = "akeyless-rta"
}

variable "ingress" {
  type    = string
  default = "INGRESS_TRAFFIC_INTERNAL_ONLY"
}
