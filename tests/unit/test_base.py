# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

# Learn more about testing at: https://juju.is/docs/sdk/testing

# pylint: disable=duplicate-code,missing-function-docstring
"""Unit tests."""

import unittest

import ops
import ops.testing

from charm import GatewayAPICharm


class TestCharm(unittest.TestCase):
    """Test class."""

    def setUp(self):
        """Set up the testing environment."""
        self.harness = ops.testing.Harness(GatewayAPICharm)
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()
