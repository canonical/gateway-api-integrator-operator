# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

variable "certificates_integration" {
  description = "Endpoint or offer to integrate the gateway-api-integrator 'certificates' relation with (a TLS certificates provider). Leave null to skip the integration."
  type = object({
    offer_url = optional(string)
    name      = optional(string)
    endpoint  = optional(string)
  })
  default = null
}

variable "dns_record_integration" {
  description = "Endpoint or offer to integrate the gateway-api-integrator 'dns-record' relation with. Leave null to skip the integration."
  type = object({
    offer_url = optional(string)
    name      = optional(string)
    endpoint  = optional(string)
  })
  default = null
}

variable "gateway_api_integrator" {
  type = object({
    app_name    = optional(string, "gateway-api-integrator")
    config      = optional(map(string), {})
    constraints = optional(string, "arch=amd64")
    revision    = optional(number)
    base        = optional(string, "ubuntu@24.04")
    units       = optional(number, 1)
  })
  default = {}
}

variable "ingress_configurator" {
  type = object({
    app_name    = optional(string, "ingress-configurator")
    config      = optional(map(string), {})
    constraints = optional(string, "arch=amd64")
    revision    = optional(number)
    base        = optional(string, "ubuntu@24.04")
    units       = optional(number, 1)
  })
  default = {}
}

variable "metadata_version" {
  description = "Version string reported in the product module 'metadata' output."
  type        = string
  default     = "1.0.0"
}

variable "model_uuid" {
  description = "Reference to a juju model's uuid."
  type        = string
  nullable    = false
}

variable "risk" {
  description = "Risk level controlling the channel risk of the charms in the solution."
  type        = string
  default     = "stable"

  validation {
    condition     = contains(["stable", "edge"], var.risk)
    error_message = "risk must be one of: stable, edge."
  }
}
