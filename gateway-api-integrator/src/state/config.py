# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator configuration."""

import itertools
import logging
import typing

import ops
from charms.gateway_api_integrator.v0.gateway_route import valid_fqdn
from lightkube import Client
from lightkube.generic_resource import create_global_resource
from pydantic import BeforeValidator, Field, ValidationError
from pydantic.dataclasses import dataclass

from resource_manager.permission import map_k8s_auth_exception

from .exception import CharmStateValidationBaseError

CUSTOM_RESOURCE_GROUP_NAME = "gateway.networking.k8s.io"
GATEWAY_CLASS_RESOURCE_NAME = "GatewayClass"
GATEWAY_CLASS_PLURAL = "gatewayclasses"

logger = logging.getLogger()


class InvalidCharmConfigError(CharmStateValidationBaseError):
    """Exception raised when a charm configuration is found to be invalid."""


class GatewayClassUnavailableError(CharmStateValidationBaseError):
    """Exception raised when a charm configuration is found to be invalid."""


@dataclass(frozen=True)
class CharmConfig:
    """A component of charm state that contains the charm's configuration.

    Attributes:
        gateway_class_name: The configured gateway class.
        external_hostname: The configured gateway hostname.
        enforce_https: Whether to enforce HTTPS by redirecting HTTP to HTTPS.
    """

    external_hostname: typing.Annotated[str, BeforeValidator(valid_fqdn)] | None
    gateway_class_name: str = Field(min_length=1)
    enforce_https: bool = Field()

    @classmethod
    @map_k8s_auth_exception
    def from_charm(cls, charm: ops.CharmBase, client: Client) -> "CharmConfig":
        """Create a CharmConfig class from a charm instance.

        Args:
            charm: The gateway-api-integrator charm.
            client: The lightkube client

        Raises:
            InvalidCharmConfigError: When the charm's config is invalid.
            GatewayClassUnavailableError: When the cluster has no available gateway classes.

        Returns:
            CharmConfig: Instance of the charm config state component.
        """
        gateway_class_name = typing.cast(str, charm.config.get("gateway-class"))
        gateway_class_generic_resource = create_global_resource(
            CUSTOM_RESOURCE_GROUP_NAME, "v1", GATEWAY_CLASS_RESOURCE_NAME, GATEWAY_CLASS_PLURAL
        )
        gateway_classes = tuple(client.list(gateway_class_generic_resource))
        if not gateway_classes:
            logger.error("No gateway class available on cluster.")
            raise GatewayClassUnavailableError("No gateway class available on cluster.")

        gateway_class_names = tuple(
            gateway_class.metadata.name
            for gateway_class in gateway_classes
            if gateway_class.metadata and gateway_class.metadata.name
        )
        if gateway_class_name not in gateway_class_names:
            available_gateway_classes = ",".join(gateway_class_names)
            logger.error(
                ("Configured gateway class %s not present on the cluster.Available ones are: %r"),
                gateway_class_name,
                available_gateway_classes,
            )
            raise InvalidCharmConfigError(
                f"Gateway class must be one of: [{available_gateway_classes}]"
            )

        enforce_https = typing.cast(bool, charm.config.get("enforce-https", True))
        external_hostname = typing.cast(str | None, charm.config.get("external-hostname"))

        # Validate that hostname is provided when HTTPS is enforced
        if enforce_https and not external_hostname:
            raise InvalidCharmConfigError(
                "external-hostname is required when enforce-https is true"
            )

        try:
            return cls(
                gateway_class_name=gateway_class_name,
                external_hostname=external_hostname,
                enforce_https=enforce_https,
            )
        except ValidationError as exc:
            error_field_str = ",".join(f"{field}" for field in get_invalid_config_fields(exc))
            raise InvalidCharmConfigError(f"invalid configuration: {error_field_str}") from exc


def get_invalid_config_fields(exc: ValidationError) -> typing.Set[int | str]:
    """Return a list on invalid config from pydantic validation error.

    Args:
        exc: The validation error exception.

    Returns:
        str: list of fields that failed validation.
    """
    error_fields = set(itertools.chain.from_iterable(error["loc"] for error in exc.errors()))
    return error_fields
