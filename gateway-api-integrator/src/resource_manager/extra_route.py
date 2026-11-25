# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.
"""Resource management for the routes configured with the extra-routes option."""

import logging
import typing

import httpx2 as httpx
from lightkube import Client
from lightkube.core.client import LabelSelector
from lightkube.core.exceptions import ApiError
from lightkube.generic_resource import GenericNamespacedResource, create_namespaced_resource
from lightkube.models.meta_v1 import ObjectMeta
from lightkube.types import PatchType

from helpers import truncate_k8s_resource_name
from state.exception import CharmStateValidationBaseError
from state.extra_routes import ExtraRoute, ExtraRouteProtocol

from .gateway import http_listener_name, https_listener_name
from .permission import map_k8s_auth_exception

logger = logging.getLogger(__name__)

CUSTOM_RESOURCE_GROUP_NAME = "gateway.networking.k8s.io"
EXTRA_ROUTE_LABEL = "gateway-api-integrator.charm.juju.is/extra-route"
# TCPRoute and UDPRoute graduated to v1 in Gateway API v1.6, older clusters serve v1alpha2.
L4_ROUTE_API_VERSIONS = ("v1", "v1alpha2")


class L4RouteCRDMissingError(CharmStateValidationBaseError):
    """Exception raised when TCPRoute/UDPRoute are needed but the cluster does not serve them."""


def route_resource_name(gateway_name: str, route_name: str) -> str:
    """Return the name of the resource backing an extra route."""
    return truncate_k8s_resource_name(f"{gateway_name}-x-{route_name}")


def _backend_refs(route: ExtraRoute) -> list[dict[str, typing.Any]]:
    return [{"name": route.service, "port": route.service_port}]


def _http_rule(route: ExtraRoute, hsts_max_age: int | None) -> dict[str, typing.Any]:
    filters: list[dict[str, typing.Any]] = []
    if route.strip_prefix and route.path_prefix != "/":
        filters.append(
            {
                "type": "URLRewrite",
                "urlRewrite": {"path": {"type": "ReplacePrefixMatch", "replacePrefixMatch": "/"}},
            }
        )
    if hsts_max_age is not None:
        filters.append(
            {
                "type": "ResponseHeaderModifier",
                "responseHeaderModifier": {
                    "add": [
                        {
                            "name": "Strict-Transport-Security",
                            "value": f"max-age={hsts_max_age}",
                        }
                    ]
                },
            }
        )
    rule: dict[str, typing.Any] = {
        "matches": [{"path": {"type": "PathPrefix", "value": route.path_prefix}}],
        "backendRefs": _backend_refs(route),
    }
    if filters:
        rule["filters"] = filters
    return rule


def _parent_refs(
    gateway_name: str, namespace: str, section_names: list[str]
) -> list[dict[str, str]]:
    return [
        {"name": gateway_name, "namespace": namespace, "sectionName": section_name}
        for section_name in section_names
    ]


def build_http_route_specs(
    routes: typing.Iterable[ExtraRoute],
    gateway_name: str,
    namespace: str,
    *,
    https: bool,
    enforce_https: bool,
    hsts_max_age: int | None,
) -> dict[str, dict[str, typing.Any]]:
    """Build the HTTPRoute specs of the HTTP extra routes, keyed by resource name.

    Args:
        routes: The configured extra routes, non-HTTP ones are ignored.
        gateway_name: Name of the Gateway the routes attach to.
        namespace: Namespace of the Gateway.
        https: Whether the Gateway has HTTPS listeners for the route hostnames.
        enforce_https: Whether HTTP requests are redirected to HTTPS.
        hsts_max_age: max-age of the Strict-Transport-Security header added to HTTPS
            responses, None to disable it.

    Returns:
        Mapping of HTTPRoute resource name to spec.
    """
    specs: dict[str, dict[str, typing.Any]] = {}
    redirected_hostnames: set[str] = set()
    for route in routes:
        if route.protocol != ExtraRouteProtocol.HTTP:
            continue
        hostnames = list(route.hostnames)
        if https:
            specs[route_resource_name(gateway_name, route.name)] = {
                "parentRefs": _parent_refs(
                    gateway_name,
                    namespace,
                    [https_listener_name(gateway_name, h) for h in hostnames],
                ),
                "hostnames": hostnames,
                "rules": [_http_rule(route, hsts_max_age if enforce_https else None)],
            }
        if enforce_https:
            for hostname in hostnames:
                if hostname in redirected_hostnames:
                    continue
                redirected_hostnames.add(hostname)
                name = route_resource_name(gateway_name, f"redirect-{hostname.replace('.', '-')}")
                specs[name] = {
                    "parentRefs": _parent_refs(
                        gateway_name, namespace, [http_listener_name(gateway_name, hostname)]
                    ),
                    "hostnames": [hostname],
                    "rules": [
                        {
                            "filters": [
                                {
                                    "type": "RequestRedirect",
                                    "requestRedirect": {"scheme": "https", "statusCode": 301},
                                }
                            ]
                        }
                    ],
                }
        else:
            specs[route_resource_name(gateway_name, f"{route.name}-http")] = {
                "parentRefs": _parent_refs(
                    gateway_name,
                    namespace,
                    [http_listener_name(gateway_name, h) for h in hostnames],
                ),
                "hostnames": hostnames,
                "rules": [_http_rule(route, None)],
            }
    return specs


def build_l4_route_spec(
    route: ExtraRoute, gateway_name: str, namespace: str
) -> dict[str, typing.Any]:
    """Build the TCPRoute/UDPRoute spec of an L4 extra route."""
    return {
        "parentRefs": _parent_refs(gateway_name, namespace, [route.listener_name]),
        "rules": [{"backendRefs": _backend_refs(route)}],
    }


def _is_not_found(exc: Exception) -> bool:
    if isinstance(exc, ApiError):
        return exc.status.code == 404
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 404
    return False


class ExtraRouteResourceManager:
    """Manages the HTTPRoute, TCPRoute and UDPRoute resources of the extra routes."""

    def __init__(self, gateway_name: str, client: Client) -> None:
        """Initialize the manager.

        The resources carry a dedicated label rather than the charm's managed-by label so that
        the cleanup of the ingress and gateway-route resources never removes them.

        Args:
            gateway_name: Name of the Gateway the routes attach to.
            client: Initialized lightkube client.
        """
        self._gateway_name = gateway_name
        self._client = client
        self._labels: LabelSelector = {EXTRA_ROUTE_LABEL: gateway_name}

    @map_k8s_auth_exception
    def reconcile(
        self,
        routes: tuple[ExtraRoute, ...],
        *,
        https: bool,
        enforce_https: bool,
        hsts_max_age: int | None,
    ) -> None:
        """Create or update the route resources and delete the stale ones.

        Args:
            routes: The configured extra routes.
            https: Whether the Gateway has HTTPS listeners for the route hostnames.
            enforce_https: Whether HTTP requests are redirected to HTTPS.
            hsts_max_age: max-age of the Strict-Transport-Security header, None to disable it.

        Raises:
            L4RouteCRDMissingError: When TCP or UDP routes are configured but the cluster
                serves no matching CRD.
        """
        namespace = typing.cast(str, self._client.namespace)
        http_specs = build_http_route_specs(
            routes,
            self._gateway_name,
            namespace,
            https=https,
            enforce_https=enforce_https,
            hsts_max_age=hsts_max_age,
        )
        self._sync("HTTPRoute", "httproutes", ("v1",), http_specs)

        missing: list[str] = []
        for kind, plural, protocols in (
            ("TCPRoute", "tcproutes", (ExtraRouteProtocol.TCP, ExtraRouteProtocol.TLS_TERMINATE)),
            ("UDPRoute", "udproutes", (ExtraRouteProtocol.UDP,)),
        ):
            specs = {
                route_resource_name(self._gateway_name, route.name): build_l4_route_spec(
                    route, self._gateway_name, namespace
                )
                for route in routes
                if route.protocol in protocols
            }
            if not self._sync(kind, plural, L4_ROUTE_API_VERSIONS, specs) and specs:
                missing.append(kind)
        if missing:
            raise L4RouteCRDMissingError(
                f"{' and '.join(missing)} not served by the cluster; "
                "upgrade the Gateway API CRDs or the gateway class controller"
            )

    def cleanup(self) -> None:
        """Delete all route resources managed for the extra routes."""
        self.reconcile((), https=False, enforce_https=False, hsts_max_age=None)

    def _sync(
        self,
        kind: str,
        plural: str,
        versions: tuple[str, ...],
        specs: dict[str, dict[str, typing.Any]],
    ) -> bool:
        """Apply the desired resources of a kind and delete the stale ones.

        Returns:
            False when no version of the kind is served by the cluster, True otherwise.
        """
        for version in versions:
            resource_class = create_namespaced_resource(
                CUSTOM_RESOURCE_GROUP_NAME, version, kind, plural
            )
            try:
                existing = list(self._client.list(resource_class, labels=self._labels))
            except (ApiError, httpx.HTTPStatusError) as exc:
                if _is_not_found(exc):
                    continue
                raise
            self._apply(resource_class, version, kind, specs)
            for resource in existing:
                name = typing.cast(ObjectMeta, resource.metadata).name
                if name and name not in specs:
                    self._client.delete(resource_class, name=name)
            return True
        return False

    def _apply(
        self,
        resource_class: type[GenericNamespacedResource],
        version: str,
        kind: str,
        specs: dict[str, dict[str, typing.Any]],
    ) -> None:
        for name, spec in specs.items():
            resource = resource_class(
                apiVersion=f"{CUSTOM_RESOURCE_GROUP_NAME}/{version}",
                kind=kind,
                metadata=ObjectMeta(name=name, labels=self._labels),
                spec=spec,
            )
            # force=True keeps the charm in control of the resource.
            self._client.patch(  # type: ignore[type-var]
                resource_class, name, resource, patch_type=PatchType.APPLY, force=True
            )
