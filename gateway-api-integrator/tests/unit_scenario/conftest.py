# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for gateway-api-integrator charm unit tests."""

from unittest.mock import MagicMock

import pytest
import scenario  # pylint: disable=import-error
from state.config import CharmConfig

TEST_EXTERNAL_HOSTNAME_CONFIG = "www.gateway.internal"
GATEWAY_CLASS_CONFIG = "cilium"


@pytest.fixture(scope="function", name="base_state")
def base_state_fixture(monkeypatch: pytest.MonkeyPatch):
    """Mock the base state for the charm."""
    monkeypatch.setattr("client.KubeConfig", MagicMock())
    monkeypatch.setattr("client.Client", MagicMock())
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

    dns_relation = scenario.Relation(
        endpoint="dns-record",
        interface="dns_record",
    )

    certificates_relation = scenario.Relation(
        endpoint="certificates",
        interface="certificates",
    )

    ingress_relation = scenario.Relation(
        endpoint="gateway",
        interface="ingress",
        remote_app_data={
            "model": '"testing-model"',
            "name": '"testing-ingress-app"',
            "port": "8080",
        },
        remote_units_data={
            0: {"host": '"testing-host.example.com"'},
        },
    )

    gateway_route_relation = testing.Relation(
        endpoint="gateway-route",
        interface="gateway_route",
        remote_app_data={
            "model": '"testing-model"',
            "name": '"testing-gateway-route-app"',
            "port": "8080",
            "hostname": '"testing-gateway.example.com"',
            "paths": "[]",
        },
    )

    yield {
        "leader": True,
        "relations": [
            dns_relation,
            certificates_relation,
            ingress_relation,
            gateway_route_relation,
        ],
        "model": testing.Model(
            name="testmodel",
        ),
    }
