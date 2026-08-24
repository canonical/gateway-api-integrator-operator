# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

variable "gateway_api_integrator" {
  type = object({
    app_name    = optional(string, "gateway-api-integrator")
    channel     = optional(string, "1/stable")
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
    channel     = optional(string, "latest/stable")
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
