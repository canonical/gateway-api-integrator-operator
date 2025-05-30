# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for gateway-api-integrator charm unit tests."""

from unittest.mock import MagicMock

import pytest
from ops import testing

from state.config import CharmConfig

TEST_EXTERNAL_HOSTNAME_CONFIG = "www.gateway.internal"
GATEWAY_CLASS_CONFIG = "cilium"


@pytest.fixture(scope="function", name="base_state")
def base_state_fixture(monkeypatch: pytest.MonkeyPatch):
    """Mock the base state for the charm."""
    monkeypatch.setattr("charm.KubeConfig", MagicMock())
    monkeypatch.setattr("charm.Client", MagicMock())
    monkeypatch.setattr(
        "charm.CharmConfig.from_charm",
        MagicMock(return_value=CharmConfig(GATEWAY_CLASS_CONFIG, TEST_EXTERNAL_HOSTNAME_CONFIG)),
    )
    monkeypatch.setattr("charm.GatewayAPICharm._define_secret_resources", MagicMock())
    monkeypatch.setattr(
        "charm.GatewayAPICharm._define_ingress_resources_and_publish_url", MagicMock()
    )
    monkeypatch.setattr("charm.GatewayAPICharm._set_status_gateway_address", MagicMock())
    monkeypatch.setattr("charm.GatewayResourceManager.current_gateway_resource", MagicMock())

    def mock_gateway_address(self, gateway_name):  # pylint: disable=unused-argument
        # Disabling the unused-argument because the method signature is required by the mock.
        """Mock the gateway address to return a fixed IP.

        Args:
            gateway_name: The name of the gateway resource.

        Returns:
            A fixed IP address as a string.
        """
        return "1.2.3.4"

    monkeypatch.setattr("charm.GatewayResourceManager.gateway_address", mock_gateway_address)

    dns_relation = testing.Relation(
        endpoint="dns-record",
        interface="dns-record",
    )

    certificates_relation = testing.Relation(
        endpoint="certificates",
        interface="certificates",
    )

    ingress_relation = testing.Relation(
        endpoint="gateway",
        interface="ingress",
    )
    yield {
        "leader": True,
        "relations": [dns_relation, certificates_relation, ingress_relation],
    }
