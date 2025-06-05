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
    monkeypatch.setattr(
        "charm.GatewayResourceManager.gateway_address", lambda self, name: "1.2.3.4"
    )

    dns_relation = testing.Relation(
        endpoint="dns-record",
        interface="dns_record",
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
        "model": testing.Model(
            name="testmodel",
        ),
    }
