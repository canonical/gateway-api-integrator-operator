# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "gateway_api_integrator_app_name" {
  description = "Name of the deployed gateway-api-integrator application."
  value       = module.gateway_api_integrator.app_name
}

output "ingress_configurator_app_name" {
  description = "Name of the deployed ingress-configurator application."
  value       = module.ingress_configurator.app_name
}

output "gateway_api_integrator_requires" {
  description = "List of required relation endpoints for gateway-api-integrator."
  value       = module.gateway_api_integrator.requires
}

output "gateway_api_integrator_provides" {
  description = "List of provided relation endpoints for gateway-api-integrator."
  value       = module.gateway_api_integrator.provides
}

output "ingress_configurator_requires" {
  description = "List of required relation endpoints for ingress-configurator."
  value       = module.ingress_configurator.requires
}

output "ingress_configurator_provides" {
  description = "List of provided relation endpoints for ingress-configurator."
  value       = module.ingress_configurator.provides
}
