# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for gateway-route-configurator charm unit tests."""

import json

import pytest
from ops import testing


@pytest.fixture(scope="function", name="ingress_relation")
def ingress_relation_fixture():
    """Mock ingress relation data."""
    return testing.Relation(
        endpoint="ingress",
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


@pytest.fixture(scope="function", name="gateway_route_relation")
def gateway_route_relation_fixture():
    """Mock gateway-route relation data."""
    return testing.Relation(
        endpoint="gateway-route",
        interface="gateway_route",
        remote_app_data={
            "endpoints": json.dumps(["https://testing-gateway.example.com/app1"]),
        },
    )


@pytest.fixture(scope="function", name="base_state")
def base_state_fixture(ingress_relation, gateway_route_relation):
    """Mock the base state for the charm."""
    yield {
        "leader": True,
        "relations": [
            ingress_relation,
            gateway_route_relation,
        ],
        "config": {
            "hostname": "testing-gateway.example.com",
            "paths": '["/app1", "/app2"]',
        },
        "model": testing.Model(
            name="testmodel",
        ),
    }
