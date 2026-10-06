# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

# Captures the initial deployment timestamp once and keeps it stable across
# subsequent applies, for the "metadata.deployed_at" output.
resource "terraform_data" "deployed_at" {
  input = timestamp()

  lifecycle {
    ignore_changes = [input]
  }
}

module "gateway_api_integrator" {
  source = "../modules/gateway-api-integrator"

  app_name   = var.gateway_api_integrator.app_name
  channel    = local.gateway_api_integrator_channel
  config     = var.gateway_api_integrator.config
  model_uuid = var.model_uuid
  revision   = var.gateway_api_integrator.revision
  base       = var.gateway_api_integrator.base
  units      = var.gateway_api_integrator.units
}

module "ingress_configurator" {
  source = "git::https://github.com/canonical/ingress-configurator-operator//terraform?ref=tf-2.0.0&depth=1"

  app_name   = var.ingress_configurator.app_name
  channel    = local.ingress_configurator_channel
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
    name     = module.ingress_configurator.application.name
    endpoint = "gateway-route"
  }
}

# Create integration between gateway-api-integrator and an external TLS
# certificates provider, when one is supplied.
resource "juju_integration" "gateway_api_integrator_certificates" {
  count      = var.certificates_integration == null ? 0 : 1
  model_uuid = var.model_uuid

  application {
    name     = module.gateway_api_integrator.app_name
    endpoint = "certificates"
  }

  application {
    offer_url = var.certificates_integration.offer_url
    name      = var.certificates_integration.name
    endpoint  = var.certificates_integration.endpoint
  }
}

# Create integration between gateway-api-integrator and an external DNS
# record provider, when one is supplied.
resource "juju_integration" "gateway_api_integrator_dns_record" {
  count      = var.dns_record_integration == null ? 0 : 1
  model_uuid = var.model_uuid

  application {
    name     = module.gateway_api_integrator.app_name
    endpoint = "dns-record"
  }

  application {
    offer_url = var.dns_record_integration.offer_url
    name      = var.dns_record_integration.name
    endpoint  = var.dns_record_integration.endpoint
  }
}
