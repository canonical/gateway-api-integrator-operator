# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "gateway_api_integrator_app_name" {
  description = "Name of the deployed gateway-api-integrator application."
  value       = module.gateway_api_integrator.app_name
}

output "ingress_configurator_app_name" {
  description = "Name of the deployed ingress-configurator application."
  value       = module.ingress_configurator.application.name
}

output "metadata" {
  description = "Deployment metadata."
  value = {
    version     = var.metadata_version
    deployed_at = terraform_data.deployed_at.output
    updated_at  = timestamp()
  }
}

output "models" {
  description = "Map of model key to its model_uuid and deployed components."
  value = {
    gateway_api_integrator = {
      model_uuid = var.model_uuid
      components = {
        gateway_api_integrator = module.gateway_api_integrator.application
        ingress_configurator   = module.ingress_configurator.application
      }
    }
  }
}

output "offers" {
  description = "Map of the offers exposed by the solution."
  value = {
    gateway = juju_offer.gateway.url
    ingress = juju_offer.ingress.url
  }
}
