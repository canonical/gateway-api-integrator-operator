# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

variable "model_uuid" {
  description = "Reference to a juju model's uuid."
  type        = string
}

# Gateway API Integrator variables
variable "gateway_api_integrator_app_name" {
  description = "Name of the gateway-api-integrator application in the Juju model."
  type        = string
  default     = "gateway-api-integrator"
}

variable "gateway_api_integrator_channel" {
  description = "The channel to use when deploying the gateway-api-integrator charm."
  type        = string
  default     = "latest/edge"
}

variable "gateway_api_integrator_config" {
  description = "Application config for gateway-api-integrator."
  type        = map(string)
  default     = {}
}

variable "gateway_api_integrator_revision" {
  description = "Revision number of the gateway-api-integrator charm"
  type        = number
  default     = null
}

variable "gateway_api_integrator_base" {
  description = "The operating system on which to deploy gateway-api-integrator"
  type        = string
  default     = "ubuntu@22.04"
}

variable "gateway_api_integrator_units" {
  description = "Number of gateway-api-integrator units to deploy"
  type        = number
  default     = 1
}

# Gateway Route Configurator variables
variable "gateway_route_configurator_app_name" {
  description = "Name of the gateway-route-configurator application in the Juju model."
  type        = string
  default     = "gateway-route-configurator"
}

variable "gateway_route_configurator_channel" {
  description = "The channel to use when deploying the gateway-route-configurator charm."
  type        = string
  default     = "latest/edge"
}

variable "gateway_route_configurator_config" {
  description = "Application config for gateway-route-configurator."
  type        = map(string)
  default     = {}
}

variable "gateway_route_configurator_revision" {
  description = "Revision number of the gateway-route-configurator charm"
  type        = number
  default     = null
}

variable "gateway_route_configurator_base" {
  description = "The operating system on which to deploy gateway-route-configurator"
  type        = string
  default     = "ubuntu@22.04"
}

variable "gateway_route_configurator_units" {
  description = "Number of gateway-route-configurator units to deploy"
  type        = number
  default     = 1
}

# Optional integration variables
variable "tls_certificates_app_name" {
  description = "Name of the TLS certificates provider application to integrate with (optional)"
  type        = string
  default     = null
}

variable "ingress_app_name" {
  description = "Name of the ingress provider application to integrate with (optional)"
  type        = string
  default     = null
}
