# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for gateway-api-integrator charm unit tests."""

from typing import Dict

import pytest
from ops.testing import Harness

from charm import GatewayAPICharm


@pytest.fixture(scope="function", name="harness")
def harness_fixture():
    """Enable ops test framework harness."""
    harness = Harness(GatewayAPICharm)
    yield harness
    harness.cleanup()


@pytest.fixture(scope="function", name="certificates_relation_data")
def certificates_relation_data_fixture() -> Dict[str, str]:
    """Mock tls_certificates relation data."""
    return {
        "csr-example.com": "whatever",
        "certificate-example.com": "whatever",
        "ca-example.com": "whatever",
        "chain-example.com": "whatever",
    }


@pytest.fixture(scope="function", name="patch_load_incluster_config")
def patch_load_incluster_config_fixture(monkeypatch: pytest.MonkeyPatch):
    """Patch kubernetes.config.load_incluster_config."""
    monkeypatch.setattr("kubernetes.config.load_incluster_config", lambda: None)
