# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

# Disable protected access rules due to the need to test charm._labels
# pylint: disable=protected-access
"""Unit tests for gateway resource."""

from unittest.mock import MagicMock

import ops
import pytest
from httpx import Response
from lightkube.core.exceptions import ApiError
from lightkube.generic_resource import GenericNamespacedResource
from lightkube.models.meta_v1 import ObjectMeta, Status
from ops import testing

from charm import GatewayAPICharm
from resource_manager.gateway import (
    GatewayResourceDefinition,
    GatewayResourceManager,
    http_listener_name,
    https_listener_name,
)
from state.charm_state import CharmState
from state.gateway import GatewayResourceInformation
from state.tls import TLSInformation

from .conftest import GATEWAY_CLASS_CONFIG, TEST_EXTERNAL_HOSTNAME_CONFIG


@pytest.mark.usefixtures("client_with_mock_external")
def test_create_gateway(
    gateway_relation: testing.Relation,
    certificates_relation: testing.Relation,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    arrange: Given a charm with mocked lightkube client, juju secret, relations and gateway ip.
    act: run the config-changed event with valid config.
    assert: the charm goes into active status.
    """
    monkeypatch.setattr(
        "resource_manager.gateway.GatewayResourceManager.current_gateway_resource",
        MagicMock(return_value=None),
    )
    ctx = testing.Context(GatewayAPICharm)
    state_in = testing.State(
        leader=True,
        config={
            "external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
            "gateway-class": GATEWAY_CLASS_CONFIG,
        },
        relations=[gateway_relation, certificates_relation],
    )

    state_out = ctx.run(ctx.on.config_changed(), state_in)

    assert state_out.unit_status.name == ops.ActiveStatus.name


def test_gateway_resource_definition_insufficient_permission(
    certificates_relation: testing.Relation,
    monkeypatch: pytest.MonkeyPatch,
    mock_lightkube_client: MagicMock,
) -> None:
    """
    arrange: given a charm with mocked lightkube client that returns 403.
    act: when agent reconciliation triggers.
    assert: The exception is handled and charm is set to blocked state.
    """
    monkeypatch.setattr(
        "lightkube.models.meta_v1.Status.from_dict", MagicMock(return_value=Status(code=403))
    )
    mock_lightkube_client.list = MagicMock(side_effect=ApiError(response=MagicMock(spec=Response)))
    ctx = testing.Context(GatewayAPICharm)
    state_in = testing.State(
        leader=True,
        config={
            "external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
            "gateway-class": GATEWAY_CLASS_CONFIG,
        },
        relations=[certificates_relation],
    )

    state_out = ctx.run(ctx.on.config_changed(), state_in)

    assert state_out.unit_status.name == ops.BlockedStatus.name


@pytest.mark.usefixtures("client_with_mock_external")
def test_gateway_gen_resource(
    gateway_relation: testing.Relation,
    certificates_relation: testing.Relation,
    mock_lightkube_client: MagicMock,
) -> None:
    """
    arrange: Given a charm with valid config and mocked client.
    act: Call _gen_resource from the required state components.
    assert: The k8s resource is correctly generated.
    """
    ctx = testing.Context(GatewayAPICharm)
    state_in = testing.State(
        leader=True,
        config={
            "external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
            "gateway-class": GATEWAY_CLASS_CONFIG,
        },
        relations=[gateway_relation, certificates_relation],
    )

    with ctx(ctx.on.update_status(), state_in) as manager:
        charm = manager.charm
        gateway_resource_information = GatewayResourceInformation.from_charm(charm)
        gateway_resource_manager = GatewayResourceManager(
            labels=charm._labels,
            client=mock_lightkube_client,
        )
        charm_state = CharmState.from_charm_and_providers(
            charm,
            [GATEWAY_CLASS_CONFIG],
            charm._ingress_provider,
            charm._gateway_route_provider,
        )
        tls_information = TLSInformation.from_charm(
            charm,
            set(),
            charm.certificates,
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
    hostnames: set[str] | None = None,
) -> GatewayResourceDefinition:
    """Construct a minimal GatewayResourceDefinition for spec-level unit tests.

    Bypasses the full constructor so tests do not need a running charm.
    """
    obj = object.__new__(GatewayResourceDefinition)
    obj.gateway_name = gateway_name
    obj.gateway_class_name = gateway_class
    obj.hostnames = {hostname for hostname, _ in tls_pairs} if hostnames is None else hostnames
    obj.tls_hostname_secrets = tls_pairs
    return obj


def test_gateway_resource_spec_no_tls():
    """
    arrange: GatewayResourceDefinition with no TLS hostnames and no managed hostnames.
    act: access gateway_resource_spec.
    assert: only the single hostname-less HTTP listener is present.
    """
    gw_def = _make_gw_def("my-gateway", [])
    spec = gw_def.gateway_resource_spec

    assert len(spec["listeners"]) == 1
    assert spec["listeners"][0]["protocol"] == "HTTP"
    assert "hostname" not in spec["listeners"][0]


def test_gateway_resource_spec_single_https_listener():
    """
    arrange: GatewayResourceDefinition with one TLS hostname.
    act: access gateway_resource_spec.
    assert: 2 listeners (per-hostname HTTP + HTTPS); the HTTP and HTTPS listeners share the
        same hostname, and the HTTPS listener has the correct name and a single certificateRef.
    """
    hostname = "example.com"
    secret_name = "my-app-secret-example.com"  # nosec B105
    gw_def = _make_gw_def("my-gateway", [(hostname, secret_name)])
    spec = gw_def.gateway_resource_spec

    assert len(spec["listeners"]) == 2

    http_listener = spec["listeners"][0]
    assert http_listener["protocol"] == "HTTP"
    assert http_listener["hostname"] == hostname
    assert http_listener["name"] == http_listener_name("my-gateway", hostname)

    https_listener = spec["listeners"][1]
    assert https_listener["protocol"] == "HTTPS"
    assert https_listener["hostname"] == hostname
    assert https_listener["name"] == https_listener_name("my-gateway", hostname)
    assert https_listener["tls"]["certificateRefs"] == [{"kind": "Secret", "name": secret_name}]


def test_gateway_resource_spec_multiple_https_listeners():
    """
    arrange: GatewayResourceDefinition with two TLS hostnames.
    act: access gateway_resource_spec.
    assert: 4 listeners (2 HTTP + 2 HTTPS); each HTTP and HTTPS listener has a distinct
        hostname, name, and certificateRef — no two listeners share the same match.
    """
    pairs = [
        ("alpha.example.com", "secret-alpha"),
        ("beta.example.com", "secret-beta"),
    ]
    gw_def = _make_gw_def("my-gateway", pairs)
    spec = gw_def.gateway_resource_spec

    assert len(spec["listeners"]) == 4

    http_listeners = [li for li in spec["listeners"] if li["protocol"] == "HTTP"]
    assert len(http_listeners) == 2
    http_names = [li["name"] for li in http_listeners]
    http_hostnames = [li["hostname"] for li in http_listeners]
    assert len(set(http_names)) == 2
    assert set(http_hostnames) == {"alpha.example.com", "beta.example.com"}

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


def test_http_listener_name_sanitizes_dots():
    """
    arrange: a gateway name and a dotted hostname.
    act: call http_listener_name.
    assert: dots in the hostname are replaced with hyphens.
    """
    result = http_listener_name("my-gateway", "example.com")
    assert result == "my-gateway-http-example-com"


def test_gateway_resource_spec_ip_cert_no_hostname_field():
    """
    arrange: GatewayResourceDefinition where the TLS 'hostname' is an IP address
        (the requires_ip_certificate=True path).
    act: access gateway_resource_spec.
    assert: the HTTPS listener does NOT include a hostname field because Gateway
        API forbids IP addresses in the listener hostname field.
    """
    ip = "10.43.45.0"
    secret_name = f"my-app-secret-{ip}"  # nosec B105
    gw_def = _make_gw_def("my-gateway", [(ip, secret_name)], hostnames=set())
    spec = gw_def.gateway_resource_spec

    assert len(spec["listeners"]) == 2
    https_listener = spec["listeners"][1]
    assert https_listener["protocol"] == "HTTPS"
    assert "hostname" not in https_listener
    assert https_listener["tls"]["certificateRefs"] == [{"kind": "Secret", "name": secret_name}]
