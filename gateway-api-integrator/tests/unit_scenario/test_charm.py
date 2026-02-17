# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the charm."""

import pytest
from ops import testing

from charm import GatewayAPICharm


def test_dns_record(
    base_state: dict, gateway_relation: testing.Relation, certificates_relation: testing.Relation
) -> None:
    """
    arrange: Charm is initialized with a mock state.
    act: Run reconcile via the start event.
    assert: The charm updates the dns-record relation with the expected DNS entries.
    """
    ctx = testing.Context(GatewayAPICharm)
    base_state["relations"].append(gateway_relation)
    base_state["relations"].append(certificates_relation)
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
    # Find the dns-record relation and check its dns_entries
    dns_relation = [rel for rel in state.relations if rel.endpoint == "dns-record"][0]
    assert dns_relation.local_app_data["dns_entries"] == mock_dns_entry_str


def test_dns_record_no_gateway_resource(
    base_state: dict,
    monkeypatch: pytest.MonkeyPatch,
    gateway_relation: testing.Relation,
    certificates_relation: testing.Relation,
) -> None:
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
    base_state["relations"].append(gateway_relation)
    base_state["relations"].append(certificates_relation)
    state = testing.State(**base_state)
    state = ctx.run(ctx.on.start(), state)
    assert "dns_entries" not in list(state.relations)[0].local_app_data


def test_dns_record_no_gateway_address(
    base_state: dict,
    monkeypatch: pytest.MonkeyPatch,
    gateway_relation: testing.Relation,
    certificates_relation: testing.Relation,
) -> None:
    """
    arrange: Charm is initialized with a mock state without a gateway address.
    act: Run reconcile via the start event.
    assert: The charm does not update the dns-record relation.
    """
    monkeypatch.setattr("charm.GatewayResourceManager.gateway_address", lambda self, name: None)
    ctx = testing.Context(GatewayAPICharm)
    base_state["relations"].append(gateway_relation)
    base_state["relations"].append(certificates_relation)
    state = testing.State(**base_state)
    state = ctx.run(ctx.on.start(), state)
    assert "dns_entries" not in list(state.relations)[0].local_app_data


def test_gateway_route(
    base_state: dict,
    gateway_route_relation: testing.Relation,
    certificates_relation: testing.Relation,
) -> None:
    """
    arrange: Charm is initialized with a mock state.
    act: Run reconcile via the start event.
    assert: The charm updates the dns-record relation with the expected DNS entries.
    """
    ctx = testing.Context(GatewayAPICharm)
    base_state["relations"].append(gateway_route_relation)
    base_state["relations"].append(certificates_relation)
    state = testing.State(**base_state)
    gateway_route_relation = [rel for rel in state.relations if rel.endpoint == "gateway-route"][0]
    state = ctx.run(ctx.on.relation_changed(gateway_route_relation), state)
    mock_dns_entry_str = (
        '[{"domain": "www.gateway.internal", '
        '"host_label": "@", '
        '"ttl": 600, '
        '"record_class": "IN", '
        '"record_type": "A", '
        '"record_data": "1.2.3.4", '
        '"uuid": "5e7b1cba-450c-5238-b811-4ace6d6fdbbf"}]'
    )
    # Find the dns-record relation and check its dns_entries
    dns_relation = [rel for rel in state.relations if rel.endpoint == "dns-record"][0]
    assert dns_relation.local_app_data["dns_entries"] == mock_dns_entry_str
