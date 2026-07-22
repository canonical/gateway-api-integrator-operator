# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

# Disable protected access rules to test charm._labels and charm._ingress_provider
# Disable duplicate-code as we're initializing the http-route resource the same way as in charm.py
# pylint: disable=protected-access,duplicate-code
"""Unit tests for http_route resource."""

from unittest.mock import MagicMock

import pytest
from lightkube.core.client import Client
from ops import testing

from charm import GatewayAPICharm
from resource_manager.gateway import http_listener_name, https_listener_name
from resource_manager.http_route import (
    HTTPRouteResourceDefinition,
    HTTPRouteResourceManager,
    HTTPRouteType,
)
from state.gateway import GatewayResourceInformation
from state.http_route import (
    HTTPRouteResourceInformation,
    IngressIntegrationDataValidationError,
)

from .conftest import GATEWAY_CLASS_CONFIG, TEST_EXTERNAL_HOSTNAME_CONFIG


@pytest.mark.usefixtures("client_with_mock_external")
def test_http_route_resource_information_validation_error() -> None:
    """
    arrange: Given a charm with ingress integration with invalid data.
    act: Initialize HTTPRouteResourceInformation state component.
    assert: IngressIntegrationDataValidationError is raised.
    """
    gateway_relation = testing.Relation(endpoint="gateway", interface="ingress")
    ctx = testing.Context(GatewayAPICharm)
    state_in = testing.State(leader=True, relations=[gateway_relation])

    with ctx(ctx.on.update_status(), state_in) as manager:
        charm = manager.charm
        with pytest.raises(IngressIntegrationDataValidationError):
            HTTPRouteResourceInformation.from_ingress(charm._ingress_provider, None)


@pytest.mark.usefixtures("client_with_mock_external")
def test_http_route_gen_resource(gateway_relation: testing.Relation) -> None:
    """
    arrange: Given a charm with valid config and mocked client.
    act: Call _gen_resource from the required state components.
    assert: The k8s resource is correctly generated.
    """
    client_mock = MagicMock(spec=Client)
    ctx = testing.Context(GatewayAPICharm)
    state_in = testing.State(
        leader=True,
        config={
            "external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
            "gateway-class": GATEWAY_CLASS_CONFIG,
        },
        relations=[gateway_relation],
    )

    with ctx(ctx.on.update_status(), state_in) as manager:
        charm = manager.charm
        http_route_resource_information = HTTPRouteResourceInformation.from_ingress(
            charm._ingress_provider, None
        )
        gateway_resource_information = GatewayResourceInformation.from_charm(charm)
        http_route_resource_manager = HTTPRouteResourceManager(
            labels=charm._labels,
            client=client_mock,
        )
        https_route_resource = http_route_resource_manager._gen_resource(
            HTTPRouteResourceDefinition(
                http_route_resource_information,
                gateway_resource_information,
                HTTPRouteType.HTTPS,
            )
        )
        assert (
            https_route_resource.spec["parentRefs"][0]["sectionName"] == f"{charm.app.name}-https"
        )


def _hsts_filters(spec: dict) -> list[dict]:
    """Return the ResponseHeaderModifier HSTS filters found in a route spec."""
    filters = []
    for rule in spec.get("rules", []):
        for rule_filter in rule.get("filters", []):
            if rule_filter.get("type") == "ResponseHeaderModifier":
                for header in rule_filter["responseHeaderModifier"]["add"]:
                    if header["name"] == "Strict-Transport-Security":
                        filters.append(rule_filter)
    return filters


def _build_route_spec(gateway_relation: testing.Relation, **definition_kwargs) -> dict:
    """Build an HTTPRoute resource spec for the given definition kwargs.

    Requires the ``client_with_mock_external`` fixture to be active.
    """
    ctx = testing.Context(GatewayAPICharm)
    state_in = testing.State(
        leader=True,
        config={
            "external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
            "gateway-class": GATEWAY_CLASS_CONFIG,
        },
        relations=[gateway_relation],
    )

    with ctx(ctx.on.update_status(), state_in) as manager:
        charm = manager.charm
        http_route_resource_information = HTTPRouteResourceInformation.from_ingress(
            charm._ingress_provider, "gateway.internal"
        )
        gateway_resource_information = GatewayResourceInformation.from_charm(charm)
        definition = HTTPRouteResourceDefinition(
            http_route_resource_information,
            gateway_resource_information,
            **definition_kwargs,
        )
        return definition.http_route_resource_spec("test-namespace")


@pytest.mark.usefixtures("client_with_mock_external")
def test_https_route_injects_hsts_filter_when_enforced(
    gateway_relation: testing.Relation,
) -> None:
    """
    arrange: Given an HTTPS HTTPRouteResourceDefinition with hsts_max_age set.
    act: Generate the HTTPRoute resource spec.
    assert: A ResponseHeaderModifier filter adds Strict-Transport-Security: max-age=<value>.
    """
    spec = _build_route_spec(
        gateway_relation,
        http_route_type=HTTPRouteType.HTTPS,
        hsts_max_age=31536000,
    )
    hsts_filters = _hsts_filters(spec)
    assert len(hsts_filters) == 1
    header = hsts_filters[0]["responseHeaderModifier"]["add"][0]
    assert header == {"name": "Strict-Transport-Security", "value": "max-age=31536000"}


@pytest.mark.usefixtures("client_with_mock_external")
def test_https_route_omits_hsts_filter_when_not_enforced(
    gateway_relation: testing.Relation,
) -> None:
    """
    arrange: Given an HTTPS HTTPRouteResourceDefinition with hsts_max_age unset (None).
    act: Generate the HTTPRoute resource spec.
    assert: No Strict-Transport-Security ResponseHeaderModifier filter is present.
    """
    spec = _build_route_spec(
        gateway_relation,
        http_route_type=HTTPRouteType.HTTPS,
    )
    assert _hsts_filters(spec) == []


@pytest.mark.usefixtures("client_with_mock_external")
def test_https_route_hsts_filter_zero_max_age(
    gateway_relation: testing.Relation,
) -> None:
    """
    arrange: Given an HTTPS HTTPRouteResourceDefinition with hsts_max_age=0.
    act: Generate the HTTPRoute resource spec.
    assert: The header is still emitted as max-age=0 to clear cached HSTS policy.
    """
    spec = _build_route_spec(
        gateway_relation,
        http_route_type=HTTPRouteType.HTTPS,
        hsts_max_age=0,
    )
    hsts_filters = _hsts_filters(spec)
    assert len(hsts_filters) == 1
    header = hsts_filters[0]["responseHeaderModifier"]["add"][0]
    assert header["value"] == "max-age=0"


@pytest.mark.usefixtures("client_with_mock_external")
def test_http_redirect_route_never_injects_hsts_filter(
    gateway_relation: testing.Relation,
) -> None:
    """
    arrange: Given an HTTP redirect HTTPRouteResourceDefinition.
    act: Generate the HTTPRoute resource spec.
    assert: No Strict-Transport-Security filter is added to the redirect rule.
    """
    spec = _build_route_spec(
        gateway_relation,
        http_route_type=HTTPRouteType.HTTP,
        redirect_https=True,
    )
    assert _hsts_filters(spec) == []


def test_patch_http_route(mock_lightkube_client: MagicMock):
    """
    arrange: Given an HTTPRouteResourceManager with mocked lightkube client.
    act: Call _patch_resource.
    assert: The mocked client method is called.
    """
    http_route_resource_manager = HTTPRouteResourceManager(
        labels={},
        client=mock_lightkube_client,
    )
    http_route_resource_manager._patch_resource("", None)
    mock_lightkube_client.patch.assert_called_once()


def test_http_route_resource_information():
    """
    arrange: Provide valid values for all HTTPRouteResourceInformation fields.
    act: Instantiate HTTPRouteResourceInformation.
    assert: All fields are correctly set.
    """
    info = HTTPRouteResourceInformation(
        application_name="my-app",
        requirer_model_name="my-model",
        service_name="gateway-api-integrator-my-app-service",
        service_port=8080,
        service_port_name="tcp-8080",
        filters=[],
        paths=["/my-model-my-app"],
        hostname="gateway.internal",
    )
    assert info.application_name == "my-app"
    assert info.requirer_model_name == "my-model"
    assert info.service_name == "gateway-api-integrator-my-app-service"
    assert info.service_port == 8080
    assert info.service_port_name == "tcp-8080"
    assert info.filters == []
    assert info.paths == ["/my-model-my-app"]
    assert info.hostname == "gateway.internal"


def test_http_route_resource_information_hostname_none():
    """
    arrange: Provide None as hostname.
    act: Instantiate HTTPRouteResourceInformation.
    assert: hostname is None.
    """
    info = HTTPRouteResourceInformation(
        application_name="my-app",
        requirer_model_name="my-model",
        service_name="gateway-api-integrator-my-app-service",
        service_port=8080,
        service_port_name="tcp-8080",
        filters=[],
        paths=["/my-model-my-app"],
        hostname=None,
    )
    assert info.hostname is None


def test_http_route_resource_information_with_strip_prefix_filter():
    """
    arrange: Provide a URLRewrite filter (strip_prefix use case).
    act: Instantiate HTTPRouteResourceInformation.
    assert: The filters list contains the expected URLRewrite filter.
    """
    url_rewrite_filter = {
        "type": "URLRewrite",
        "urlRewrite": {
            "path": {
                "type": "ReplacePrefixMatch",
                "replacePrefixMatch": "/",
            }
        },
    }
    info = HTTPRouteResourceInformation(
        application_name="my-app",
        requirer_model_name="my-model",
        service_name="gateway-api-integrator-my-app-service",
        service_port=8080,
        service_port_name="tcp-8080",
        filters=[url_rewrite_filter],
        paths=["/my-model-my-app"],
        hostname="gateway.internal",
    )
    assert len(info.filters) == 1
    assert info.filters[0]["type"] == "URLRewrite"


def test_http_route_resource_information_multiple_paths():
    """
    arrange: Provide multiple paths.
    act: Instantiate HTTPRouteResourceInformation.
    assert: All paths are stored correctly.
    """
    info = HTTPRouteResourceInformation(
        application_name="my-app",
        requirer_model_name="my-model",
        service_name="gateway-api-integrator-my-app-service",
        service_port=8080,
        service_port_name="tcp-8080",
        filters=[],
        paths=["/path-a", "/path-b", "/path-c"],
        hostname="gateway.internal",
    )
    assert info.paths == ["/path-a", "/path-b", "/path-c"]


def test_http_route_resource_information_empty_filters_and_paths():
    """
    arrange: Provide empty filters and paths lists.
    act: Instantiate HTTPRouteResourceInformation.
    assert: Both lists are empty.
    """
    info = HTTPRouteResourceInformation(
        application_name="my-app",
        requirer_model_name="my-model",
        service_name="gateway-api-integrator-my-app-service",
        service_port=8080,
        service_port_name="tcp-8080",
        filters=[],
        paths=[],
        hostname=None,
    )
    assert info.filters == []
    assert info.paths == []


# ---------------------------------------------------------------------------
# listener_id / http_route_resource_name — per-hostname HTTPS tests
# ---------------------------------------------------------------------------


def _make_http_route_def(
    gateway_name: str,
    http_route_type: HTTPRouteType,
    hostname: str | None,
) -> HTTPRouteResourceDefinition:
    """Construct a minimal HTTPRouteResourceDefinition for property-level tests.

    Bypasses the full constructor so tests do not need a charm.
    """
    obj = object.__new__(HTTPRouteResourceDefinition)
    obj.gateway_name = gateway_name
    obj.http_route_type = http_route_type
    obj.hostname = hostname
    return obj


def test_https_listener_id_uses_sanitized_hostname():
    """
    arrange: HTTPRouteResourceDefinition with HTTPS type and a dotted hostname.
    act: access listener_id.
    assert: the id is "{gateway_name}-https-{hostname_with_dots_replaced_by_hyphens}".
    """
    obj = _make_http_route_def("my-gateway", HTTPRouteType.HTTPS, "example.com")
    assert obj.listener_id == "my-gateway-https-example-com"
    assert obj.listener_id == https_listener_name("my-gateway", "example.com")


def test_http_listener_id_unchanged():
    """
    arrange: HTTPRouteResourceDefinition with HTTP type and no hostname.
    act: access listener_id.
    assert: the id is the traditional "{gateway_name}-http" (no hostname suffix).
    """
    obj = _make_http_route_def("my-gateway", HTTPRouteType.HTTP, None)
    assert obj.listener_id == "my-gateway-http"


def test_http_listener_id_uses_sanitized_hostname():
    """
    arrange: HTTPRouteResourceDefinition with HTTP type and a dotted hostname.
    act: access listener_id.
    assert: the id is "{gateway_name}-http-{hostname_with_dots_replaced_by_hyphens}".
    """
    obj = _make_http_route_def("my-gateway", HTTPRouteType.HTTP, "example.com")
    assert obj.listener_id == "my-gateway-http-example-com"
    assert obj.listener_id == http_listener_name("my-gateway", "example.com")


def test_https_listener_id_without_hostname_falls_back():
    """
    arrange: HTTPRouteResourceDefinition with HTTPS type but hostname=None.
    act: access listener_id.
    assert: falls back to "{gateway_name}-https" (legacy single-listener behaviour).
    """
    obj = _make_http_route_def("my-gateway", HTTPRouteType.HTTPS, None)
    assert obj.listener_id == "my-gateway-https"


def test_https_resource_name_uses_sanitized_hostname():
    """
    arrange: HTTPRouteResourceDefinition with HTTPS type and a dotted hostname.
    act: access http_route_resource_name.
    assert: the K8s name is "{gateway_name}-https-{sanitized}" truncated to 63 chars.
    """
    obj = _make_http_route_def("my-gateway", HTTPRouteType.HTTPS, "example.com")
    name = obj.http_route_resource_name
    assert name == "my-gateway-https-example-com"
    assert len(name) <= 63
