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
      channel = "latest/edge"
      # renovate: depName="gateway-api-integrator"
      revision = 149
    }
    gateway_route_configurator = {
      channel = "latest/edge"
      # renovate: depName="gateway-route-configurator"
      revision = 13
    }
  }

  assert {
    condition     = output.gateway_api_integrator_app_name == "gateway-api-integrator"
    error_message = "gateway-api-integrator app_name did not match expected"
  }

  assert {
    condition     = output.gateway_route_configurator_app_name == "gateway-route-configurator"
    error_message = "gateway-route-configurator app_name did not match expected"
  }
}
