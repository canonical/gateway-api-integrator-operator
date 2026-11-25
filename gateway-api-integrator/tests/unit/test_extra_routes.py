# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the extra-routes option."""

import json
from unittest.mock import MagicMock

import httpx2 as httpx
import pytest
from lightkube.core.exceptions import ApiError

from resource_manager import extra_route
from resource_manager.extra_route import (
    ExtraRouteResourceManager,
    L4RouteCRDMissingError,
    build_http_route_specs,
    build_l4_route_spec,
)
from resource_manager.gateway import GatewayResourceDefinition
from state.extra_routes import (
    ExtraRouteProtocol,
    ExtraRoutesConfigError,
    parse_external_ips,
    parse_extra_routes,
)

HTTP_ROUTE = {
    "name": "ui",
    "service": "telemetry-ui",
    "service_port": 8080,
    "hostnames": ["telemetry.example.com"],
}
MQTTS_ROUTE = {
    "name": "mqtts",
    "protocol": "tls-terminate",
    "port": 8883,
    "service": "emqx",
    "service_port": 1883,
    "hostnames": ["telemetry.example.com"],
}
QUIC_ROUTE = {
    "name": "quic",
    "protocol": "udp",
    "port": 14567,
    "service": "emqx",
    "service_port": 14567,
}


def _routes(*items: dict):
    return parse_extra_routes(json.dumps(list(items)))


def test_parse_extra_routes_valid():
    """
    arrange: JSON with an HTTP, a tls-terminate and a UDP route.
    act: parse the option.
    assert: routes are returned with defaults applied.
    """
    routes = _routes(HTTP_ROUTE, MQTTS_ROUTE, QUIC_ROUTE)

    assert [r.protocol for r in routes] == [
        ExtraRouteProtocol.HTTP,
        ExtraRouteProtocol.TLS_TERMINATE,
        ExtraRouteProtocol.UDP,
    ]
    assert routes[0].path_prefix == "/"
    assert routes[1].listener_name == "tls-terminate-8883"
    assert routes[2].is_l4


@pytest.mark.parametrize(
    "value",
    [
        "not json",
        '{"name": "x"}',
        json.dumps([{**HTTP_ROUTE, "hostnames": []}]),
        json.dumps([{**HTTP_ROUTE, "name": "Bad_Name"}]),
        json.dumps([{**HTTP_ROUTE, "path_prefix": "api"}]),
        json.dumps([{**QUIC_ROUTE, "port": None}]),
        json.dumps([{**MQTTS_ROUTE, "port": 443}]),
        json.dumps([{**MQTTS_ROUTE, "hostnames": []}]),
        json.dumps([HTTP_ROUTE, HTTP_ROUTE]),
        json.dumps([MQTTS_ROUTE, {**MQTTS_ROUTE, "name": "other"}]),
        json.dumps([{**HTTP_ROUTE, "protocol": "sctp"}]),
    ],
)
def test_parse_extra_routes_invalid(value: str):
    """
    arrange: malformed extra-routes values.
    act: parse the option.
    assert: ExtraRoutesConfigError is raised.
    """
    with pytest.raises(ExtraRoutesConfigError):
        parse_extra_routes(value)


def test_parse_external_ips():
    """
    arrange: comma separated addresses, with one invalid in the second case.
    act: parse the option.
    assert: addresses are normalized and invalid ones rejected.
    """
    assert parse_external_ips("10.0.0.1, 10.0.0.2") == ("10.0.0.1", "10.0.0.2")
    assert parse_external_ips(None) == ()
    with pytest.raises(ExtraRoutesConfigError):
        parse_external_ips("10.0.0.1,example.com")


def test_http_route_specs_enforce_https():
    """
    arrange: an HTTP route with a path prefix to strip, HTTPS enforced.
    act: build the HTTPRoute specs.
    assert: one HTTPS route with rewrite and HSTS plus one redirect on the HTTP listener.
    """
    routes = _routes(
        {**HTTP_ROUTE, "path_prefix": "/api", "strip_prefix": True},
        {**HTTP_ROUTE, "name": "root"},
    )

    specs = build_http_route_specs(
        routes, "gw", "ns", https=True, enforce_https=True, hsts_max_age=60
    )

    assert len(specs) == 3
    api = specs["gw-x-ui"]
    assert api["parentRefs"][0]["sectionName"] == "gw-https-telemetry-example-com"
    filter_types = [f["type"] for f in api["rules"][0]["filters"]]
    assert filter_types == ["URLRewrite", "ResponseHeaderModifier"]
    redirects = [s for n, s in specs.items() if "redirect" in n]
    assert len(redirects) == 1
    assert redirects[0]["parentRefs"][0]["sectionName"] == "gw-http-telemetry-example-com"
    assert redirects[0]["rules"][0]["filters"][0]["type"] == "RequestRedirect"


def test_http_route_specs_plain_http():
    """
    arrange: an HTTP route, no TLS and no enforcement.
    act: build the HTTPRoute specs.
    assert: the route attaches to the HTTP listener only.
    """
    specs = build_http_route_specs(
        _routes(HTTP_ROUTE), "gw", "ns", https=False, enforce_https=False, hsts_max_age=None
    )

    assert list(specs) == ["gw-x-ui-http"]
    assert specs["gw-x-ui-http"]["parentRefs"][0]["sectionName"] == "gw-http-telemetry-example-com"
    assert "filters" not in specs["gw-x-ui-http"]["rules"][0]


def test_l4_route_spec():
    """
    arrange: a UDP route.
    act: build its spec.
    assert: it attaches to the dedicated listener and targets the Service port.
    """
    spec = build_l4_route_spec(_routes(QUIC_ROUTE)[0], "gw", "ns")

    assert spec["parentRefs"] == [{"name": "gw", "namespace": "ns", "sectionName": "udp-14567"}]
    assert spec["rules"] == [{"backendRefs": [{"name": "emqx", "port": 14567}]}]


def _gateway_definition(routes, secrets, ips=()):
    definition = object.__new__(GatewayResourceDefinition)
    definition.gateway_name = "gw"
    definition.gateway_class_name = "envoy"
    definition.hostnames = {h for r in routes for h in r.hostnames}
    definition.tls_hostname_secrets = secrets
    definition.extra_routes = routes
    definition.external_ips = ips
    return definition


def test_gateway_spec_l4_listeners_and_addresses():
    """
    arrange: tls-terminate and UDP routes with a certificate secret and an external IP.
    act: build the Gateway spec.
    assert: dedicated listeners and the requested address are present.
    """
    routes = _routes(HTTP_ROUTE, MQTTS_ROUTE, QUIC_ROUTE)
    spec = _gateway_definition(
        routes, [("telemetry.example.com", "secret")], ("10.0.0.1",)
    ).gateway_resource_spec

    listeners = {listener["name"]: listener for listener in spec["listeners"]}
    assert listeners["tls-terminate-8883"]["protocol"] == "TLS"
    assert listeners["tls-terminate-8883"]["tls"]["certificateRefs"][0]["name"] == "secret"
    assert listeners["udp-14567"]["protocol"] == "UDP"
    assert spec["addresses"] == [{"type": "IPAddress", "value": "10.0.0.1"}]


def test_gateway_spec_tls_listener_waits_for_secret():
    """
    arrange: a tls-terminate route without a certificate secret yet.
    act: build the Gateway spec.
    assert: the TLS listener is omitted and no addresses are set.
    """
    spec = _gateway_definition(_routes(MQTTS_ROUTE), []).gateway_resource_spec

    assert all(listener["name"] != "tls-terminate-8883" for listener in spec["listeners"])
    assert "addresses" not in spec


def _not_found_error() -> ApiError:
    response = httpx.Response(404, request=httpx.Request("GET", "http://k8s"))
    return ApiError(request=response.request, response=response)


def test_reconcile_falls_back_to_alpha_version(monkeypatch: pytest.MonkeyPatch):
    """
    arrange: a cluster serving UDPRoute only as v1alpha2.
    act: reconcile a UDP route.
    assert: the route is applied with the v1alpha2 API version.
    """
    client = MagicMock(namespace="ns")

    def list_resources(resource_class, labels):
        if (
            resource_class.__name__ == "UDPRoute"
            and resource_class._api_info.resource.version == "v1"
        ):
            raise _not_found_error()
        return []

    client.list.side_effect = list_resources
    manager = ExtraRouteResourceManager("gw", client)

    manager.reconcile(_routes(QUIC_ROUTE), https=False, enforce_https=False, hsts_max_age=None)

    applied = [call.args[2] for call in client.patch.call_args_list]
    assert [r.apiVersion for r in applied if r.kind == "UDPRoute"] == [
        "gateway.networking.k8s.io/v1alpha2"
    ]


def test_reconcile_missing_l4_crd_raises():
    """
    arrange: a cluster serving no TCPRoute version.
    act: reconcile a tls-terminate route.
    assert: L4RouteCRDMissingError is raised.
    """
    client = MagicMock(namespace="ns")

    def list_resources(resource_class, labels):
        if resource_class.__name__ == "TCPRoute":
            raise httpx.HTTPStatusError(
                "not found",
                request=httpx.Request("GET", "http://k8s"),
                response=httpx.Response(404),
            )
        return []

    client.list.side_effect = list_resources

    with pytest.raises(L4RouteCRDMissingError):
        ExtraRouteResourceManager("gw", client).reconcile(
            _routes(MQTTS_ROUTE), https=True, enforce_https=True, hsts_max_age=0
        )


def test_reconcile_missing_l4_crd_ignored_without_l4_routes():
    """
    arrange: a cluster serving no L4 CRDs and only an HTTP route configured.
    act: reconcile.
    assert: no error is raised.
    """
    client = MagicMock(namespace="ns")

    def list_resources(resource_class, labels):
        if resource_class.__name__ != "HTTPRoute":
            raise httpx.HTTPStatusError(
                "not found",
                request=httpx.Request("GET", "http://k8s"),
                response=httpx.Response(404),
            )
        return []

    client.list.side_effect = list_resources

    ExtraRouteResourceManager("gw", client).reconcile(
        _routes(HTTP_ROUTE), https=False, enforce_https=False, hsts_max_age=None
    )


def test_reconcile_deletes_stale_resources():
    """
    arrange: an existing HTTPRoute that is no longer configured.
    act: reconcile with no routes.
    assert: the stale resource is deleted.
    """
    stale = MagicMock()
    stale.metadata.name = "gw-x-old"
    client = MagicMock(namespace="ns")
    client.list.side_effect = lambda resource_class, labels: (
        [stale] if resource_class.__name__ == "HTTPRoute" else []
    )

    ExtraRouteResourceManager("gw", client).cleanup()

    assert client.delete.call_args.kwargs["name"] == "gw-x-old"
    assert extra_route.EXTRA_ROUTE_LABEL
