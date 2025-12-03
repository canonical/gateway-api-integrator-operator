# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the charm."""

import pytest
from ops import testing

from charm import GatewayAPICharm
from charms.gateway_api_integrator.v0.gateway_route import GatewayRouteProvider


def test_dns_record(base_state: dict) -> None:
    """
    arrange: Charm is initialized with a mock state.
    act: Run reconcile via the start event.
    assert: The charm updates the dns-record relation with the expected DNS entries.
    """
    ctx = testing.Context(GatewayAPICharm)
    state = testing.State(**base_state)
    state = ctx.run(ctx.on.start(), state)
    mock_dns_entry_str = (
        '[{"domain": "www.gateway.internal", '
        '"host_label": "@", '
        '"ttl": 600, '
        '"record_class": "IN", '
        '"record_type": "A", '
        '"record_data": "1.2.3.4", '
        '"uuid": "5e7b1cba-450c-5238-b811-4ace6d6fdbbf"}]'
    )
    assert list(state.relations)[0].local_app_data["dns_entries"] == mock_dns_entry_str


def test_dns_record_no_gateway_resource(base_state: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    arrange: Charm is initialized with a mock state without a gateway resource.
    act: Run reconcile via the start event.
    assert: The charm does not update the dns-record relation.
    """
    monkeypatch.setattr(
        "charm.GatewayResourceManager.current_gateway_resource",
        lambda self: None,
    )
    ctx = testing.Context(GatewayAPICharm)
    state = testing.State(**base_state)
    state = ctx.run(ctx.on.start(), state)
    assert "dns_entries" not in list(state.relations)[0].local_app_data


def test_dns_record_no_gateway_address(base_state: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    arrange: Charm is initialized with a mock state without a gateway address.
    act: Run reconcile via the start event.
    assert: The charm does not update the dns-record relation.
    """
    monkeypatch.setattr("charm.GatewayResourceManager.gateway_address", lambda self, name: None)
    ctx = testing.Context(GatewayAPICharm)
    state = testing.State(**base_state)
    state = ctx.run(ctx.on.start(), state)
    assert "dns_entries" not in list(state.relations)[0].local_app_data


def test_gateway_route(base_state: dict) -> None:
    """
    arrange: Charm is initialized with a mock state.
    act: Run reconcile via the start event.
    assert: The charm updates the dns-record relation with the expected DNS entries.
    """
    ctx = testing.Context(GatewayAPICharm)
    state = testing.State(**base_state)
    gateway_route_relation = testing.Relation(
        endpoint="gateway-route",
        interface="gateway_route",
        remote_app_data={
            "model": "testing-model",
            "name": "testing-gateway-route-app",
            "port": "8080",
        },
    )
    state = ctx.run(ctx.on.custom(GatewayRouteProvider.on.data_provided), state)
    mock_dns_entry_str = (
        '[{"domain": "www.gateway.internal", '
        '"host_label": "@", '
        '"ttl": 600, '
        '"record_class": "IN", '
        '"record_type": "A", '
        '"record_data": "1.2.3.4", '
        '"uuid": "5e7b1cba-450c-5238-b811-4ace6d6fdbbf"}]'
    )
    assert list(state.relations)[0].local_app_data["dns_entries"] == mock_dns_entry_str
