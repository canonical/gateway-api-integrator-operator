# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "app_name" {
  description = "Name of the deployed application."
  value       = juju_application.gateway_api_integrator.name
}

output "requires" {
  value = {
    certificates = "certificates"
  }
}

output "provides" {
  value = {
    gateway_route = "gateway-route"
    gateway       = "gateway"
  }
}
