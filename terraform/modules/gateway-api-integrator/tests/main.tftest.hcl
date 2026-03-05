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
    # renovate: depName="gateway-api-integrator"
    revision = 136
  }

  assert {
    condition     = output.app_name == "gateway-api-integrator"
    error_message = "gateway-api-integrator app_name did not match expected"
  }
}
