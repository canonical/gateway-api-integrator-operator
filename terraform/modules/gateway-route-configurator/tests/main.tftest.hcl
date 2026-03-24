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
    channel    = "latest/edge"
    # renovate: depName="gateway-route-configurator"
    revision = 12
  }

  assert {
    condition     = output.app_name == "gateway-route-configurator"
    error_message = "gateway-route-configurator app_name did not match expected"
  }
}
