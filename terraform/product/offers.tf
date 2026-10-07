# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

resource "juju_offer" "gateway" {
  model_uuid       = var.model_uuid
  application_name = module.gateway_api_integrator.app_name
  endpoints        = ["gateway"]
}

resource "juju_offer" "ingress" {
  model_uuid       = var.model_uuid
  application_name = module.ingress_configurator.application.name
  endpoints        = ["ingress"]
}
