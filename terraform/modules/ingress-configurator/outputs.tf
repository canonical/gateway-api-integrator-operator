# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

output "app_name" {
  description = "Name of the deployed application."
  value       = juju_application.ingress_configurator.name
}

output "requires" {
  value = {
    gateway_route = "gateway-route"
  }
}

output "provides" {
  value = {
    ingress = "ingress"
  }
}
