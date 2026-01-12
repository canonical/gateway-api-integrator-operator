# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

module "gateway_api_integrator" {
  source = "../modules/gateway-api-integrator"

  app_name   = var.gateway_api_integrator_app_name
  channel    = var.gateway_api_integrator_channel
  config     = var.gateway_api_integrator_config
  model_uuid = var.model_uuid
  revision   = var.gateway_api_integrator_revision
  base       = var.gateway_api_integrator_base
  units      = var.gateway_api_integrator_units
}

module "gateway_route_configurator" {
  source = "../modules/gateway-route-configurator"

  app_name   = var.gateway_route_configurator_app_name
  channel    = var.gateway_route_configurator_channel
  config     = var.gateway_route_configurator_config
  model_uuid = var.model_uuid
  revision   = var.gateway_route_configurator_revision
  base       = var.gateway_route_configurator_base
  units      = var.gateway_route_configurator_units
}

# Create relation between gateway-api-integrator and gateway-route-configurator
resource "juju_integration" "gateway_api_integrator_to_route_configurator" {
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
