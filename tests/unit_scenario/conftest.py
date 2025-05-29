# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for gateway-api-integrator charm unit tests."""

from unittest.mock import MagicMock

import pytest
from ops import testing

from state.config import CharmConfig

TEST_EXTERNAL_HOSTNAME_CONFIG = "www.gateway.internal"
GATEWAY_CLASS_CONFIG = "cilium"


@pytest.fixture(scope="function", name="patch_lightkube_client")
def patch_lightkube_client_fixture(
    monkeypatch: pytest.MonkeyPatch,
):
    """Patch lightkube cluster initialization."""
    monkeypatch.setattr("charm.KubeConfig", MagicMock())
    monkeypatch.setattr("charm.Client", MagicMock())


@pytest.fixture(scope="function", name="base_state")
def base_state_fixture(
    monkeypatch: pytest.MonkeyPatch,
    patch_lightkube_client: None,
):
    """Mock the base state for the charm."""
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

    def mock_gateway_address(self, gateway_name):
        return "1.2.3.4"

    monkeypatch.setattr("charm.GatewayResourceManager.gateway_address", mock_gateway_address)

    dnsRelation = testing.Relation(
        endpoint="dns-record",
        interface="dns-record",
    )

    certificatesRelation = testing.Relation(
        endpoint="certificates",
        interface="certificates",
    )

    ingressRelation = testing.Relation(
        endpoint="gateway",
        interface="ingress",
    )
    yield {
        "leader": True,
        # config={
        #     "gateway-class": GATEWAY_CLASS_CONFIG,
        #     "external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
        # },
        "relations": [dnsRelation, certificatesRelation, ingressRelation],
    }
