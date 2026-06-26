# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

# Disable protected access rules due to the need to test charm._labels
# pylint: disable=protected-access
"""Unit tests for gateway resource."""

from unittest.mock import MagicMock

import ops
import pytest
from httpx import Response
from lightkube.core.client import Client
from lightkube.core.exceptions import ApiError
from lightkube.generic_resource import GenericNamespacedResource
from lightkube.models.meta_v1 import ObjectMeta, Status
from ops.testing import Harness

from resource_manager.gateway import (
    GatewayResourceDefinition,
    GatewayResourceManager,
    https_listener_name,
)
from state.charm_state import CharmState
from state.gateway import GatewayResourceInformation
from state.tls import TLSInformation

from .conftest import GATEWAY_CLASS_CONFIG


@pytest.mark.usefixtures("client_with_mock_external")
def test_create_gateway(  # pylint: disable=too-many-arguments, too-many-positional-arguments
    harness: Harness,
    certificates_relation_data: dict[str, str],
    gateway_relation: dict[str, dict[str, str]],
    config: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
):
    """
    arrange: Given a charm with mocked lightkube client, juju secret, relations and gateway ip.
    act: update the charm's config with the correct values.
    assert: the charm goes into active status.
    """
    monkeypatch.setattr(
        "resource_manager.gateway.GatewayResourceManager.current_gateway_resource",
        MagicMock(return_value=None),
    )
    harness.add_relation(
        "gateway",
        "requirer-charm",
        app_data=gateway_relation["app_data"],
        unit_data=gateway_relation["unit_data"],
    )
    relation_id = harness.add_relation("certificates", "self-signed-certificates")
    harness.update_relation_data(relation_id, harness.model.app.name, certificates_relation_data)
    harness.set_leader()
    harness.begin()

    harness.update_config(config)

    assert harness.charm.unit.status.name == ops.ActiveStatus.name


def test_gateway_resource_definition_insufficient_permission(
    harness: Harness,
    certificates_relation_data: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    config: dict[str, str],
):
    """
    arrange: given a charm with mocked lightkube client that returns 403.
    act: when agent reconciliation triggers.
    assert: The exception is handled and charm is set to blocked state.
    """
    harness.add_relation(
        "certificates", "self-signed-certificates", app_data=certificates_relation_data
    )
    monkeypatch.setattr(
        "lightkube.models.meta_v1.Status.from_dict", MagicMock(return_value=Status(code=403))
    )
    lightkube_client_mock = MagicMock(spec=Client)
    lightkube_client_mock.return_value.list = MagicMock(
        side_effect=ApiError(response=MagicMock(spec=Response))
    )
    monkeypatch.setattr(
        "charm.get_client",
        lightkube_client_mock,
    )
    harness.begin()
    harness.update_config(config)

    assert harness.charm.unit.status.name == ops.BlockedStatus.name


def test_gateway_gen_resource(
    harness: Harness,
    config: dict[str, str],
    certificates_relation_data: dict[str, str],
    client_with_mock_external: MagicMock,
):
    """
    arrange: Given a charm with valid config and mocked client.
    act: Call _gen_resource from the required state components.
    assert: The k8s resource is correctly generated.
    """
    relation_id = harness.add_relation("certificates", "self-signed-certificates")
    harness.update_relation_data(relation_id, harness.model.app.name, certificates_relation_data)
    harness.update_config(config)
    harness.begin()

    gateway_resource_information = GatewayResourceInformation.from_charm(harness.charm)
    gateway_resource_manager = GatewayResourceManager(
        labels=harness.charm._labels,
        client=client_with_mock_external,
    )
    charm_state = CharmState.from_charm_and_providers(
        harness.charm,
        [GATEWAY_CLASS_CONFIG],
        harness.charm._ingress_provider,
        harness.charm._gateway_route_provider,
    )
    tls_information = TLSInformation.from_charm(
        harness.charm,
        set(),
        harness.charm.certificates,
    )
    gateway_resource = gateway_resource_manager._gen_resource(
        GatewayResourceDefinition(gateway_resource_information, charm_state, tls_information)
    )

    assert gateway_resource.spec["gatewayClassName"] == GATEWAY_CLASS_CONFIG
    assert len(gateway_resource.spec["listeners"])


def test_get_current_gateway_no_resource(mock_lightkube_client: MagicMock):
    """
    arrange: Given an GatewayResourceManager with mocked lightkube client
    list method returning an empty list.
    act: Call current_gateway_resource.
    assert: The method returns None.
    """
    mock_lightkube_client.list = MagicMock(return_value=[])
    gateway_resource_manager = GatewayResourceManager(
        labels={},
        client=mock_lightkube_client,
    )
    assert gateway_resource_manager.current_gateway_resource() is None


def test_get_current_gateway(mock_lightkube_client: MagicMock):
    """
    arrange: Given an GatewayResourceManager with mocked lightkube client
    list method returning an a list of one gateway resource.
    act: Call current_gateway_resource.
    assert: The method returns the correct gateway resource.
    """
    mock_lightkube_client.list = MagicMock(
        return_value=[GenericNamespacedResource(metadata=ObjectMeta(name="gateway"))]
    )
    gateway_resource_manager = GatewayResourceManager(
        labels={},
        client=mock_lightkube_client,
    )
    gateway = gateway_resource_manager.current_gateway_resource()
    assert gateway is not None, "Gateway resource should not be None"
    assert gateway.metadata is not None, "Gateway metadata should not be None"
    assert gateway.metadata.name == "gateway"


def test_gateway_address(mock_lightkube_client: MagicMock):
    """
    arrange: Given an GatewayResourceManager with mocked lightkube client
    returning a gateway with 10.0.0.0 as LB ip address.
    act: Call gateway_address.
    assert: The return value of the called method is the LB ip address.
    """
    mock_lightkube_client.get = MagicMock(
        return_value=GenericNamespacedResource(status={"addresses": [{"value": "10.0.0.0"}]})
    )
    gateway_resource_manager = GatewayResourceManager(
        labels={},
        client=mock_lightkube_client,
    )
    assert gateway_resource_manager.gateway_address(name="") == "10.0.0.0"


def test_gateway_address_not_available(
    mock_lightkube_client: MagicMock, monkeypatch: pytest.MonkeyPatch
):
    """
    arrange: Given an GatewayResourceManager with mocked lightkube client
    returning a gateway with no LB ip available.
    act: Call gateway_address.
    assert: The return value of the called method is None.
    """
    monkeypatch.setattr("time.time", MagicMock(side_effect=[0, 5, 61, 62]))
    monkeypatch.setattr("time.sleep", MagicMock())

    mock_lightkube_client.get = MagicMock(
        return_value=GenericNamespacedResource(status={"addresses": []})
    )
    gateway_resource_manager = GatewayResourceManager(
        labels={},
        client=mock_lightkube_client,
    )
    assert gateway_resource_manager.gateway_address(name="") is None


# ---------------------------------------------------------------------------
# gateway_resource_spec — per-hostname HTTPS listener tests
# ---------------------------------------------------------------------------


def _make_gw_def(
    gateway_name: str,
    tls_pairs: list[tuple[str, str]],
    gateway_class: str = "cilium",
) -> GatewayResourceDefinition:
    """Construct a minimal GatewayResourceDefinition for spec-level unit tests.

    Bypasses the full constructor so tests do not need a running charm harness.
    """
    obj = object.__new__(GatewayResourceDefinition)
    obj.gateway_name = gateway_name
    obj.gateway_class_name = gateway_class
    obj.tls_hostname_secrets = tls_pairs
    return obj


def test_gateway_resource_spec_no_tls():
    """
    arrange: GatewayResourceDefinition with no TLS hostnames.
    act: access gateway_resource_spec.
    assert: only the single HTTP listener is present.
    """
    gw_def = _make_gw_def("my-gateway", [])
    spec = gw_def.gateway_resource_spec

    assert len(spec["listeners"]) == 1
    assert spec["listeners"][0]["protocol"] == "HTTP"


def test_gateway_resource_spec_single_https_listener():
    """
    arrange: GatewayResourceDefinition with one TLS hostname.
    act: access gateway_resource_spec.
    assert: 2 listeners (HTTP + HTTPS); the HTTPS listener has the correct hostname,
        name, and a single certificateRef.
    """
    hostname = "example.com"
    secret_name = "my-app-secret-example.com"
    gw_def = _make_gw_def("my-gateway", [(hostname, secret_name)])
    spec = gw_def.gateway_resource_spec

    assert len(spec["listeners"]) == 2

    https_listener = spec["listeners"][1]
    assert https_listener["protocol"] == "HTTPS"
    assert https_listener["hostname"] == hostname
    assert https_listener["name"] == https_listener_name("my-gateway", hostname)
    assert https_listener["tls"]["certificateRefs"] == [{"kind": "Secret", "name": secret_name}]


def test_gateway_resource_spec_multiple_https_listeners():
    """
    arrange: GatewayResourceDefinition with two TLS hostnames.
    act: access gateway_resource_spec.
    assert: 3 listeners (HTTP + 2 HTTPS); each HTTPS listener has a distinct hostname,
        name, and certificateRef — no two HTTPS listeners share the same match.
    """
    pairs = [
        ("alpha.example.com", "secret-alpha"),
        ("beta.example.com", "secret-beta"),
    ]
    gw_def = _make_gw_def("my-gateway", pairs)
    spec = gw_def.gateway_resource_spec

    assert len(spec["listeners"]) == 3

    https_listeners = [li for li in spec["listeners"] if li["protocol"] == "HTTPS"]
    assert len(https_listeners) == 2

    names = [li["name"] for li in https_listeners]
    hostnames = [li["hostname"] for li in https_listeners]
    cert_refs = [li["tls"]["certificateRefs"][0]["name"] for li in https_listeners]

    # All values must be distinct so Envoy can distinguish filter chains by SNI.
    assert len(set(names)) == 2
    assert len(set(hostnames)) == 2
    assert len(set(cert_refs)) == 2
    assert "alpha.example.com" in hostnames
    assert "beta.example.com" in hostnames


def test_https_listener_name_sanitizes_dots():
    """
    arrange: a gateway name and a dotted hostname.
    act: call https_listener_name.
    assert: dots in the hostname are replaced with hyphens.
    """
    result = https_listener_name("my-gateway", "example.com")
    assert result == "my-gateway-https-example-com"


def test_https_listener_name_truncates_long_names():
    """
    arrange: a hostname long enough to push the combined name past 253 characters.
    act: call https_listener_name.
    assert: the result is at most 253 characters.
    """
    long_hostname = "a" * 300
    result = https_listener_name("gw", long_hostname)
    assert len(result) <= 253
