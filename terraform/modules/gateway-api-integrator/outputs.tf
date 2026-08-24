# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "app_name" {
  description = "Name of the deployed application."
  value       = juju_application.gateway_api_integrator.name
}

output "application" {
  description = "The deployed gateway-api-integrator application."
  value       = juju_application.gateway_api_integrator
}

output "provides" {
  description = "Map of the provided integration endpoints."
  value = {
    gateway = {
      kind     = "endpoint"
      name     = juju_application.gateway_api_integrator.name
      endpoint = "gateway"
    }
    gateway_route = {
      kind     = "endpoint"
      name     = juju_application.gateway_api_integrator.name
      endpoint = "gateway-route"
    }
  }
}

output "requires" {
  description = "Map of the required integration endpoints."
  value = {
    certificates = {
      kind     = "endpoint"
      name     = juju_application.gateway_api_integrator.name
      endpoint = "certificates"
    }
    dns_record = {
      kind     = "endpoint"
      name     = juju_application.gateway_api_integrator.name
      endpoint = "dns-record"
    }
  }
}
