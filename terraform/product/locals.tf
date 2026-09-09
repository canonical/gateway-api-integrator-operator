# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

locals {
  # Product owns each charm's track; `risk` selects the channel risk solution-wide.
  gateway_api_integrator_channel = "1/${var.risk}"
  ingress_configurator_channel   = "latest/${var.risk}"
}
