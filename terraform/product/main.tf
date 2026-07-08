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

module "ingress_configurator" {
  source = "git::https://github.com/canonical/ingress-configurator-operator//terraform?depth=1"

  app_name   = var.ingress_configurator.app_name
  channel    = var.ingress_configurator.channel
  config     = var.ingress_configurator.config
  model_uuid = var.model_uuid
  revision   = var.ingress_configurator.revision
  base       = var.ingress_configurator.base
  units      = var.ingress_configurator.units
  trust      = true
}

# Create integration between gateway-api-integrator and ingress-configurator
resource "juju_integration" "gateway_api_integrator_ingress_configurator" {
  model_uuid = var.model_uuid

  application {
    name     = module.gateway_api_integrator.app_name
    endpoint = "gateway-route"
  }

  application {
    name     = module.ingress_configurator.app_name
    endpoint = "gateway-route"
  }
}
