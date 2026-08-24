# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

run "setup_tests" {
  module {
    source = "./tests/setup"
  }
}

run "basic_deploy" {
  variables {
    model_uuid = run.setup_tests.model_uuid
    gateway_api_integrator = {
      channel = "1/stable"
      # renovate: charm="gateway-api-integrator" track="1" risk="stable" base="24.04" arch="amd64"
      revision = 165
    }
    ingress_configurator = {
      channel = "latest/stable"
      # renovate: charm="ingress-configurator" track="latest" risk="stable" base="24.04" arch="amd64"
      revision = 99
    }
  }

  assert {
    condition     = output.gateway_api_integrator_app_name == "gateway-api-integrator"
    error_message = "gateway-api-integrator app_name did not match expected"
  }

  assert {
    condition     = output.ingress_configurator_app_name == "ingress-configurator"
    error_message = "ingress-configurator app_name did not match expected"
  }
}
