# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator charm state."""

import itertools
import logging
import typing
from enum import StrEnum

import ops
from charms.gateway_api_integrator.v1.gateway_route import (
    GatewayRouteProvider,
    valid_fqdn,
)
from charms.traefik_k8s.v2.ingress import IngressPerAppProvider
from pydantic import BeforeValidator, Field, ValidationError, ValidationInfo, field_validator
from pydantic.dataclasses import dataclass

from resource_manager.permission import map_k8s_auth_exception

from .exception import CharmStateValidationBaseError

TLS_CERTIFICATES_INTEGRATION = "certificates"

logger = logging.getLogger()


class InvalidCharmConfigError(CharmStateValidationBaseError):
    """Exception raised when a charm configuration is found to be invalid."""


class GatewayClassUnavailableError(CharmStateValidationBaseError):
    """Exception raised when a charm configuration is found to be invalid."""


class IngressGatewayRouteConflictError(CharmStateValidationBaseError):
    """Exception raised when both ingress and gateway-route integrations are established."""


class HostnameMissingError(CharmStateValidationBaseError):
    """Exception raised when a related mode requires hostname but none is configured."""


class ProxyMode(StrEnum):
    """StrEnum of possible modes of the gateway-api-integrator charm.

    Attrs:
        GATEWAY_ROUTE: When gateway-route is related.
        INGRESS: when ingress is related.
        INACTIVE: when gateway-api-integrator is not loadbalancing traffic.
    """

    GATEWAY_ROUTE = "gateway-route"
    INGRESS = "ingress"
    INACTIVE = "inactive"


INGRESS_RELATION = "gateway"
GATEWAY_ROUTE_RELATION = "gateway-route"


@dataclass(frozen=True)
class CharmState:
    """Base charm state shared by all proxy modes.

    Attributes:
        gateway_class_name: The configured gateway class.
        enforce_https: Whether to enforce HTTPS by redirecting HTTP to HTTPS.
        proxy_mode: Current proxy mode selected from active relations.
        requires_ip_certificate: Whether an IP SAN certificate is required. This
            is true only when certificates are integrated, proxy mode is
            gateway-route, and at least one relation provides no hostname.
        hostnames: Set of hostnames managed in the active mode. In ingress mode,
            at most one hostname is allowed.
    """

    gateway_class_name: str = Field(min_length=1)
    enforce_https: bool = Field()
    proxy_mode: ProxyMode = Field()
    requires_ip_certificate: bool = Field()
    hostnames: set[
        typing.Annotated[
            str,
            BeforeValidator(valid_fqdn),
        ]
    ] = Field(default_factory=set)

    @field_validator("hostnames", mode="after")
    @classmethod
    def validate_ingress_hostnames_count(
        cls, hostnames: set[str], info: ValidationInfo
    ) -> set[str]:
        """Ingress mode supports at most one hostname."""
        if info.data.get("proxy_mode") == ProxyMode.INGRESS and len(hostnames) > 1:
            raise ValueError("The charm supports at most one hostname when related via ingress.")
        return hostnames

    @classmethod
    @map_k8s_auth_exception
    def from_charm_and_providers(
        cls,
        charm: ops.CharmBase,
        available_gateway_classes: list[str],
        ingress_provider: IngressPerAppProvider,
        gateway_route_provider: GatewayRouteProvider,
    ) -> "CharmState":
        """Create a mode-specific charm state from a charm instance.

        Args:
            charm: The gateway-api-integrator charm.
            available_gateway_classes: List of available gateway classes in the cluster.
            ingress_provider: The ingress per app provider instance.
            gateway_route_provider: The gateway route provider instance.

        Raises:
            InvalidCharmConfigError: When the charm's config is invalid.
            GatewayClassUnavailableError: When the cluster has no available gateway classes.
            IngressGatewayRouteConflictError: When both ingress and gateway-route is present.

        Returns:
            CharmState for inactive mode, or a mode-specific subclass for active integrations.
        """
        enforce_https = typing.cast(bool, charm.config.get("enforce-https", True))
        has_tls = charm.model.get_relation(TLS_CERTIFICATES_INTEGRATION) is not None
        if enforce_https and not has_tls:
            raise InvalidCharmConfigError(
                "Certificates relation is needed if enforce-https is enabled."
            )

        proxy_mode = cls._validate_state(
            ingress_provider.relations, gateway_route_provider.relations
        )
        gateway_class_name = typing.cast(str, charm.config.get("gateway-class"))
        config_external_hostname = cls.get_ingress_hostname(charm)

        # external-hostname is an ingress-mode-only config option. In gateway-route
        # mode hostnames come from the relation data, so setting it is a misconfiguration.
        if proxy_mode == ProxyMode.GATEWAY_ROUTE and config_external_hostname:
            raise InvalidCharmConfigError(
                "external-hostname must only be set when related via ingress, "
                "not when integrating via gateway-route."
            )

        if gateway_class_name not in available_gateway_classes:
            available_gateway_classes_str = ",".join(available_gateway_classes)
            logger.error(
                ("Configured gateway class %s not present on the cluster. Available ones are: %r"),
                gateway_class_name,
                available_gateway_classes_str,
            )
            raise InvalidCharmConfigError(
                f"Gateway class must be one of: [{available_gateway_classes_str}]"
            )

        if proxy_mode == ProxyMode.INGRESS and has_tls and not config_external_hostname:
            raise HostnameMissingError(
                "external-hostname must be set in when related to ingress and certificates"
            )

        requires_ip_certificate = cls._requires_ip_certificate(
            proxy_mode == ProxyMode.GATEWAY_ROUTE, has_tls, gateway_route_provider
        )

        if proxy_mode == ProxyMode.INGRESS:
            hostnames = {config_external_hostname} if config_external_hostname else set()
        elif proxy_mode == ProxyMode.GATEWAY_ROUTE:
            hostnames = cls.get_gateway_route_hostnames(gateway_route_provider)
        else:
            hostnames = set()

        try:
            return CharmState(
                gateway_class_name=gateway_class_name,
                enforce_https=enforce_https,
                proxy_mode=proxy_mode,
                requires_ip_certificate=requires_ip_certificate,
                hostnames=hostnames,
            )
        except ValidationError as exc:
            error_field_str = ",".join(f"{field}" for field in get_invalid_config_fields(exc))
            raise InvalidCharmConfigError(f"invalid configuration: {error_field_str}") from exc

    @staticmethod
    def get_ingress_hostname(charm: ops.CharmBase) -> str | None:
        """Return the ingress hostname from config if present."""
        config_hostname = typing.cast(str | None, charm.config.get("external-hostname"))
        if config_hostname:
            return typing.cast(str, valid_fqdn(config_hostname))

        return None

    @staticmethod
    def get_gateway_route_hostnames(gateway_route_provider: GatewayRouteProvider) -> set[str]:
        """Return hostname set used for gateway-route mode certificate requests."""
        hostnames: set[str] = set()
        requirer_data = gateway_route_provider.get_requirer_data()
        for data in requirer_data.values():
            if data.hostname:
                hostnames.add(data.hostname)
            hostnames.update(data.additional_hostnames)
        return hostnames

    @staticmethod
    def _requires_ip_certificate(
        gateway_route_active: bool,
        has_tls: bool,
        gateway_route_provider: GatewayRouteProvider,
    ) -> bool:
        """Whether any gateway-route relation provides no hostname / additional hostnames."""
        if not has_tls or not gateway_route_active:
            return False
        requirer_data = gateway_route_provider.get_requirer_data()
        return any(
            not data.hostname and not data.additional_hostnames for data in requirer_data.values()
        )

    @staticmethod
    def _validate_state(
        ingress_relations: list[ops.Relation],
        gateway_route_relations: list[ops.Relation],
    ) -> ProxyMode:
        """Validate the charm config state.

        Raises:
            InvalidCharmConfigError: When the charm config is invalid.
        """
        is_ingress_related = bool(ingress_relations)
        is_gateway_route_related = bool(gateway_route_relations)
        if is_ingress_related and is_gateway_route_related:
            raise IngressGatewayRouteConflictError(
                "Both Ingress and Gateway Route integrations are established. Only one is allowed."
            )
        if is_ingress_related:
            return ProxyMode.INGRESS
        if is_gateway_route_related:
            return ProxyMode.GATEWAY_ROUTE
        return ProxyMode.INACTIVE


def get_invalid_config_fields(exc: ValidationError) -> typing.Set[int | str]:
    """Return a list on invalid config from pydantic validation error.

    Args:
        exc: The validation error exception.

    Returns:
        str: list of fields that failed validation.
    """
    error_fields = set(itertools.chain.from_iterable(error["loc"] for error in exc.errors()))
    return error_fields
