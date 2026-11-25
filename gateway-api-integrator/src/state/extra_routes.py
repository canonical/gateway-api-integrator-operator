# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator ``extra-routes`` configuration state."""

import ipaddress
import json
import re
import typing
from dataclasses import dataclass, field
from enum import StrEnum

from charms.gateway_api_integrator.v1.gateway_route import valid_fqdn

from .exception import CharmStateValidationBaseError

_NAME_RE = re.compile(r"^[a-z0-9]([-a-z0-9]{0,40}[a-z0-9])?$")
RESERVED_TCP_PORTS = (80, 443)


class ExtraRoutesConfigError(CharmStateValidationBaseError):
    """Exception raised when the ``extra-routes`` option is invalid."""


class ExtraRouteProtocol(StrEnum):
    """Protocol of an extra route.

    Attrs:
        HTTP: HTTPRoute served on the shared HTTP/HTTPS listeners, selected by hostname.
        TCP: TCPRoute on a dedicated plain TCP listener.
        TLS_TERMINATE: TCPRoute on a dedicated TLS listener terminating TLS at the gateway.
        UDP: UDPRoute on a dedicated UDP listener.
    """

    HTTP = "http"
    TCP = "tcp"
    TLS_TERMINATE = "tls-terminate"
    UDP = "udp"


@dataclass(frozen=True)
class ExtraRoute:
    """A statically configured route to a Service in the charm's model.

    Attributes:
        name: DNS label identifying the route.
        protocol: Route protocol.
        service: Name of the backing Service in the charm's namespace.
        service_port: Port of the backing Service.
        port: Gateway listener port, required for non-HTTP routes.
        hostnames: Hostnames served by the route. Required for HTTP routes; for
            tls-terminate routes the first hostname selects the certificate.
        path_prefix: Path prefix matched by HTTP routes.
        strip_prefix: Whether HTTP routes rewrite the matched prefix to "/".
    """

    name: str
    protocol: ExtraRouteProtocol
    service: str
    service_port: int
    port: int | None = None
    hostnames: tuple[str, ...] = field(default_factory=tuple)
    path_prefix: str = "/"
    strip_prefix: bool = False

    @property
    def is_l4(self) -> bool:
        """Whether the route is served by a dedicated L4 listener."""
        return self.protocol != ExtraRouteProtocol.HTTP

    @property
    def listener_name(self) -> str:
        """Name of the dedicated Gateway listener of an L4 route."""
        return f"{self.protocol.value}-{self.port}"


def _build_route(index: int, item: typing.Any) -> ExtraRoute:
    """Build and validate a single route entry."""
    prefix = f"extra-routes[{index}]"
    if not isinstance(item, dict):
        raise ExtraRoutesConfigError(f"{prefix} must be an object")
    try:
        protocol = ExtraRouteProtocol(str(item.get("protocol", "http")))
        route = ExtraRoute(
            name=str(item["name"]),
            protocol=protocol,
            service=str(item["service"]),
            service_port=int(item["service_port"]),
            port=int(item["port"]) if item.get("port") is not None else None,
            hostnames=tuple(valid_fqdn(str(h)) for h in item.get("hostnames", [])),
            path_prefix=str(item.get("path_prefix", "/")),
            strip_prefix=bool(item.get("strip_prefix", False)),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ExtraRoutesConfigError(f"{prefix} is incomplete or malformed: {exc!r}") from exc

    _validate_route(prefix, route)
    return route


def _validate_route(prefix: str, route: ExtraRoute) -> None:
    """Validate the cross-field constraints of a route."""
    if not _NAME_RE.match(route.name):
        raise ExtraRoutesConfigError(f"{prefix}.name must be a DNS label of at most 42 characters")
    if not 1 <= route.service_port <= 65535:
        raise ExtraRoutesConfigError(f"{prefix}.service_port is out of range")
    if not route.path_prefix.startswith("/"):
        raise ExtraRoutesConfigError(f"{prefix}.path_prefix must start with '/'")
    if route.protocol == ExtraRouteProtocol.HTTP:
        if not route.hostnames:
            raise ExtraRoutesConfigError(f"{prefix}.hostnames is required for http routes")
        return
    if route.port is None or not 1 <= route.port <= 65535:
        raise ExtraRoutesConfigError(f"{prefix}.port is required for {route.protocol} routes")
    if route.protocol != ExtraRouteProtocol.UDP and route.port in RESERVED_TCP_PORTS:
        raise ExtraRoutesConfigError(f"{prefix}.port {route.port} is reserved for HTTP(S)")
    if route.protocol == ExtraRouteProtocol.TLS_TERMINATE and not route.hostnames:
        raise ExtraRoutesConfigError(
            f"{prefix}.hostnames is required for tls-terminate routes to select the certificate"
        )


def parse_extra_routes(value: str | None) -> tuple[ExtraRoute, ...]:
    """Parse and validate the JSON ``extra-routes`` option.

    Args:
        value: The raw config value.

    Raises:
        ExtraRoutesConfigError: When the value is malformed.

    Returns:
        The validated routes.
    """
    if not value or not value.strip():
        return ()
    try:
        raw = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ExtraRoutesConfigError(f"extra-routes is not valid JSON: {exc}") from exc
    if not isinstance(raw, list):
        raise ExtraRoutesConfigError("extra-routes must be a JSON list")

    routes = tuple(_build_route(index, item) for index, item in enumerate(raw))
    names: set[str] = set()
    listeners: dict[tuple[bool, int], str] = {}
    for route in routes:
        if route.name in names:
            raise ExtraRoutesConfigError(f"duplicate extra route name {route.name!r}")
        names.add(route.name)
        if route.is_l4:
            key = (route.protocol == ExtraRouteProtocol.UDP, typing.cast(int, route.port))
            if key in listeners:
                raise ExtraRoutesConfigError(
                    f"extra route {route.name!r} reuses {route.protocol.value}/{route.port} "
                    f"already used by {listeners[key]!r}"
                )
            listeners[key] = route.name
    return routes


def parse_external_ips(value: str | None) -> tuple[str, ...]:
    """Parse the comma separated ``external-ips`` option.

    Args:
        value: The raw config value.

    Raises:
        ExtraRoutesConfigError: When an entry is not an IP address.

    Returns:
        The validated addresses.
    """
    ips = []
    for item in re.split(r"[,\s]+", (value or "").strip()):
        if not item:
            continue
        try:
            ips.append(str(ipaddress.ip_address(item)))
        except ValueError as exc:
            raise ExtraRoutesConfigError(
                f"external-ips contains invalid address {item!r}"
            ) from exc
    return tuple(ips)
