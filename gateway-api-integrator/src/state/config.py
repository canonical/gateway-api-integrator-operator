# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator configuration."""

import itertools
import logging
import typing
from enum import StrEnum

import ops
from charms.gateway_api_integrator.v0.gateway_route import (
    GatewayRouteInvalidRelationDataError,
    GatewayRouteProvider,
    GatewayRouteRelationMissingError,
    valid_fqdn,
)
from charms.traefik_k8s.v2.ingress import IngressPerAppProvider
from pydantic import BeforeValidator, Field, ValidationError
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


@dataclass(frozen=True)
class CharmConfig:
    """A component of charm state that contains the charm's configuration.

    Attributes:
        gateway_class_name: The configured gateway class.
        hostname: The configured gateway hostname.
        enforce_https: Whether to enforce HTTPS by redirecting HTTP to HTTPS.
    """

    hostname: typing.Annotated[str, BeforeValidator(valid_fqdn)] | None
    gateway_class_name: str = Field(min_length=1)
    enforce_https: bool = Field()
    proxy_mode: ProxyMode = Field()

    @classmethod
    @map_k8s_auth_exception
    def from_charm_and_providers(
        cls,
        charm: ops.CharmBase,
        available_gateway_classes: list[str],
        ingress_provider: IngressPerAppProvider,
        gateway_route_provider: GatewayRouteProvider,
    ) -> "CharmConfig":
        """Create a CharmConfig class from a charm instance.

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
            CharmConfig: Instance of the charm config state component.
        """
        enforce_https = typing.cast(bool, charm.config.get("enforce-https", True))
        if charm.model.get_relation(TLS_CERTIFICATES_INTEGRATION) is None and enforce_https:
            raise InvalidCharmConfigError(
                "Certificates relation is needed if enforce-https is enabled."
            )

        proxy_mode = cls._validate_state(
            ingress_provider.relations, gateway_route_provider.relation
        )
        gateway_class_name = typing.cast(str, charm.config.get("gateway-class"))
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

        try:
            gateway_route_requirer_data = gateway_route_provider.get_data()
            hostname = gateway_route_requirer_data.application_data.hostname
        except (GatewayRouteInvalidRelationDataError, GatewayRouteRelationMissingError):
            hostname = typing.cast(str | None, charm.config.get("external-hostname"))

        try:
            return cls(
                gateway_class_name=gateway_class_name,
                hostname=hostname,
                enforce_https=enforce_https,
                proxy_mode=proxy_mode,
            )
        except ValidationError as exc:
            error_field_str = ",".join(f"{field}" for field in get_invalid_config_fields(exc))
            raise InvalidCharmConfigError(f"invalid configuration: {error_field_str}") from exc

    @staticmethod
    def _validate_state(
        ingress_relations: list[ops.Relation],
        gateway_route_relation: ops.Relation | None,
    ) -> ProxyMode:
        """Validate the charm config state.

        Raises:
            InvalidCharmConfigError: When the charm config is invalid.
        """
        is_ingress_related = bool(ingress_relations)
        is_gateway_route_related = gateway_route_relation is not None
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
