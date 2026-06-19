# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the charm."""

from unittest.mock import MagicMock

import ops
import pytest
from ops import testing

from charm import GatewayAPICharm
from charmlibs.interfaces.tls_certificates import CertificateRequestAttributes
from charms.gateway_api_integrator.v1.gateway_route import HttpsMode
from state.charm_state import CharmState, ProxyMode
from state.tls import TLSInformationNotReadyError

from .conftest import GATEWAY_CLASS_CONFIG

ORIGINAL_FROM_CHARM_AND_PROVIDERS = CharmState.from_charm_and_providers


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
        '[{"domain": "example.com", '
        '"host_label": "@", '
        '"ttl": 600, '
        '"record_class": "IN", '
        '"record_type": "A", '
        '"record_data": "1.2.3.4", '
        '"uuid": "f6cb0ca1-3d64-5afc-9690-af437ff74415"}]'
    )
    # Find the dns-record relation and check its dns_entries
    dns_relation = next(rel for rel in state.relations if rel.endpoint == "dns-record")
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
    assert "dns_entries" not in next(iter(state.relations)).local_app_data


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
    assert "dns_entries" not in next(iter(state.relations)).local_app_data


def test_gateway_route(
    base_state: dict,
    monkeypatch: pytest.MonkeyPatch,
    gateway_route_relation: testing.Relation,
    certificates_relation: testing.Relation,
) -> None:
    """
    arrange: Charm is initialized with a mock state.
    act: Run reconcile via the relation_changed event.
    assert: The charm updates the dns-record relation with the expected DNS entries
        and publishes provider data to gateway-route relation.
    """
    # base_state fixture mocks CharmState derivation with ingress state.
    # Restore the real config path (and gateway class lookup) so this test can
    # exercise real gateway-route mode behavior from relations/config.
    monkeypatch.setattr(
        "charm.CharmState.from_charm_and_providers",
        ORIGINAL_FROM_CHARM_AND_PROVIDERS,
    )
    monkeypatch.setattr(
        "charm.GatewayAPICharm.available_gateway_classes",
        lambda self: [GATEWAY_CLASS_CONFIG],
    )

    # external-hostname is ingress-only; clear it for gateway-route mode.
    base_state["config"]["external-hostname"] = ""
    ctx = testing.Context(GatewayAPICharm)
    base_state["relations"].append(gateway_route_relation)
    base_state["relations"].append(certificates_relation)
    state = testing.State(**base_state)
    gateway_route_relation = next(
        rel for rel in state.relations if rel.endpoint == "gateway-route"
    )
    state = ctx.run(ctx.on.relation_changed(gateway_route_relation), state)
    mock_dns_entry_str = (
        '[{"domain": "example.com", '
        '"host_label": "@", '
        '"ttl": 600, '
        '"record_class": "IN", '
        '"record_type": "A", '
        '"record_data": "1.2.3.4", '
        '"uuid": "f6cb0ca1-3d64-5afc-9690-af437ff74415"}]'
    )
    # Find the dns-record relation and check its dns_entries
    dns_relation = next(rel for rel in state.relations if rel.endpoint == "dns-record")
    assert dns_relation.local_app_data["dns_entries"] == mock_dns_entry_str

    # Verify provider data is published to gateway-route relation
    gw_route_rel = next(rel for rel in state.relations if rel.endpoint == "gateway-route")
    assert "gateway_name" in gw_route_rel.local_app_data
    assert "gateway_model" in gw_route_rel.local_app_data
    assert "https_mode" in gw_route_rel.local_app_data


def test_blocked_when_relation_integrated_without_hostname(
    base_state: dict,
    monkeypatch: pytest.MonkeyPatch,
    gateway_relation: testing.Relation,
    certificates_relation: testing.Relation,
) -> None:
    """Charm should block when ingress is integrated but no hostname can be derived."""
    monkeypatch.setattr(
        "charm.CharmState.from_charm_and_providers",
        ORIGINAL_FROM_CHARM_AND_PROVIDERS,
    )
    monkeypatch.setattr(
        "charm.GatewayAPICharm.available_gateway_classes",
        lambda self: [GATEWAY_CLASS_CONFIG],
    )

    ctx = testing.Context(GatewayAPICharm)
    base_state["config"]["external-hostname"] = ""
    base_state["relations"].append(gateway_relation)
    base_state["relations"].append(certificates_relation)
    state = testing.State(**base_state)
    state = ctx.run(ctx.on.start(), state)

    assert state.unit_status.name == ops.BlockedStatus.name
    assert "external-hostname must be set" in state.unit_status.message


def test_get_certificate_requests_includes_gateway_ip_when_required(
    base_state: dict,
    monkeypatch: pytest.MonkeyPatch,
    gateway_route_relation: testing.Relation,
) -> None:
    """
    arrange: Charm state requires an IP certificate and gateway address is known.
    act: Run start event.
    assert: Certificate requests include an IP SAN CSR for the gateway address.
    """
    monkeypatch.setattr(
        "charm.CharmState.from_charm_and_providers",
        MagicMock(
            return_value=CharmState(
                gateway_class_name=GATEWAY_CLASS_CONFIG,
                enforce_https=True,
                proxy_mode=ProxyMode.GATEWAY_ROUTE,
                requires_ip_certificate=True,
                hostnames=set(),
            )
        ),
    )
    monkeypatch.setattr(
        "charm.GatewayAPICharm._current_gateway_address",
        lambda self: "1.2.3.4",
    )
    ctx = testing.Context(GatewayAPICharm)
    base_state["config"]["external-hostname"] = ""
    base_state["relations"].append(gateway_route_relation)
    state = testing.State(**base_state)
    state = ctx.run(ctx.on.start(), state)

    assert ctx.requested_certificates
    ip_csrs = [
        c for c in ctx.requested_certificates
        if isinstance(c, CertificateRequestAttributes) and c.sans_ip
    ]
    assert len(ip_csrs) == 1
    assert ip_csrs[0].common_name == "1.2.3.4"
    assert "1.2.3.4" in ip_csrs[0].sans_ip


def test_gateway_route_with_invalid_data_not_blocked(
    base_state: dict,
    monkeypatch: pytest.MonkeyPatch,
    certificates_relation: testing.Relation,
) -> None:
    """Charm should not block when all gateway-route relations provide invalid data."""
    monkeypatch.setattr(
        "charm.CharmState.from_charm_and_providers",
        ORIGINAL_FROM_CHARM_AND_PROVIDERS,
    )
    monkeypatch.setattr(
        "charm.GatewayAPICharm.available_gateway_classes",
        lambda self: [GATEWAY_CLASS_CONFIG],
    )

    invalid_gateway_route_relation = testing.Relation(
        endpoint="gateway-route",
        interface="gateway-route",
        remote_app_data={},
    )

    ctx = testing.Context(GatewayAPICharm)
    base_state["config"]["external-hostname"] = ""
    base_state["relations"].append(invalid_gateway_route_relation)
    base_state["relations"].append(certificates_relation)
    state = testing.State(**base_state)
    state = ctx.run(ctx.on.start(), state)

    assert state.unit_status.name != ops.BlockedStatus.name


def test_waiting_when_tls_information_not_ready_still_runs_gateway_definition(
    base_state: dict,
    monkeypatch: pytest.MonkeyPatch,
    certificates_relation: testing.Relation,
) -> None:
    """When TLS is pending, reconcile should still define gateway and end in waiting status."""
    define_gateway_resource_mock = MagicMock()
    monkeypatch.setattr(
        "charm.GatewayAPICharm._define_gateway_resource", define_gateway_resource_mock
    )
    monkeypatch.setattr(
        "state.tls.TLSInformation.from_charm",
        MagicMock(
            side_effect=TLSInformationNotReadyError("Waiting for TLS certificates to be issued.")
        ),
    )

    ctx = testing.Context(GatewayAPICharm)
    base_state["relations"].append(certificates_relation)
    state = testing.State(**base_state)
    state = ctx.run(ctx.on.start(), state)

    define_gateway_resource_mock.assert_called_once()
    assert state.unit_status.name == ops.WaitingStatus.name
    assert state.unit_status.message == "Waiting for TLS certificates to be issued."


def test_waiting_when_ip_san_certificate_missing(
    base_state: dict,
    monkeypatch: pytest.MonkeyPatch,
    certificates_relation: testing.Relation,
) -> None:
    """Reconcile should wait when hostname cert exists but required IP SAN cert is missing."""
    monkeypatch.setattr(
        "charm.CharmState.from_charm_and_providers",
        MagicMock(
            return_value=CharmState(
                gateway_class_name=GATEWAY_CLASS_CONFIG,
                enforce_https=True,
                proxy_mode=ProxyMode.INGRESS,
                requires_ip_certificate=True,
                hostnames={"example.com"},
            )
        ),
    )

    ctx = testing.Context(GatewayAPICharm)
    base_state["relations"].append(certificates_relation)
    state = testing.State(**base_state)
    state = ctx.run(ctx.on.start(), state)

    assert state.unit_status.name == ops.WaitingStatus.name
    assert state.unit_status.message == "Waiting for TLS certificates to be issued."
