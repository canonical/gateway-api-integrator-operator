# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for gateway-api-integrator charm unit tests."""

from typing import Dict
from unittest.mock import MagicMock

import pytest
from ops.testing import Harness

from charm import GatewayAPICharm

TEST_EXTERNAL_HOSTNAME_CONFIG = "gateway.internal"
GATEWAY_CLASS_CONFIG = "cilium"


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


@pytest.fixture(scope="function", name="patch_lightkube_client")
def patch_lightkube_client_fixture(
    monkeypatch: pytest.MonkeyPatch,
):
    """Patch lightkube cluster initialization."""
    monkeypatch.setattr("charm.KubeConfig", MagicMock())
    monkeypatch.setattr("charm.Client", MagicMock())
