# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

module "gateway_api_integrator" {
  source = "../modules/gateway-api-integrator"

  app_name   = var.gateway_api_integrator.app_name
  channel    = var.gateway_api_integrator.channel
  config     = var.gateway_api_integrator.config
  model_uuid = var.model_uuid
  revision   = var.gateway_api_integrator.revision
  base       = var.gateway_api_integrator.base
  units      = var.gateway_api_integrator.units
}

module "gateway_route_configurator" {
  source = "../modules/gateway-route-configurator"

  app_name   = var.gateway_route_configurator.app_name
  channel    = var.gateway_route_configurator.channel
  config     = var.gateway_route_configurator.config
  model_uuid = var.model_uuid
  revision   = var.gateway_route_configurator.revision
  base       = var.gateway_route_configurator.base
  units      = var.gateway_route_configurator.units
}

# Create relation between gateway-api-integrator and gateway-route-configurator
resource "juju_integration" "gateway_api_integrator_route_configurator" {
  model_uuid = var.model_uuid

  application {
    name     = module.gateway_api_integrator.app_name
    endpoint = "gateway-route"
  }

  application {
    name     = module.gateway_route_configurator.app_name
    endpoint = "gateway-route"
  }
}
