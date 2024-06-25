# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator configuration."""

import itertools
import logging
import typing

import ops
from lightkube import Client
from lightkube.generic_resource import create_global_resource
from pydantic import Field, ValidationError
from pydantic.dataclasses import dataclass

CUSTOM_RESOURCE_GROUP_NAME = "gateway.networking.k8s.io"
GATEWAY_CLASS_RESOURCE_NAME = "GatewayClass"
GATEWAY_CLASS_PLURAL = "gatewayclasses"

logger = logging.getLogger()


class InvalidCharmConfigError(Exception):
    """Exception raised when a charm configuration is found to be invalid.

    Attrs:
        msg (str): Explanation of the error.
    """

    def __init__(self, msg: str):
        """Initialize a new instance of the InvalidCharmConfigError exception.

        Args:
            msg (str): Explanation of the error.
        """
        self.msg = msg


class GatewayClassUnavailableError(Exception):
    """Exception raised when a charm configuration is found to be invalid.

    Attrs:
        msg (str): Explanation of the error.
    """

    def __init__(self, msg: str):
        """Initialize a new instance of the InvalidCharmConfigError exception.

        Args:
            msg (str): Explanation of the error.
        """
        self.msg = msg


@dataclass(frozen=True)
class CharmConfig:
    """A component of charm state that contains the charm's configuration.

    Attrs:
        gateway_class (str): The configured gateway class.
        external_hostname (str): The configured gateway hostname.
    """

    gateway_class: str = Field(min_length=1)
    external_hostname: str = Field(
        min_length=1, pattern=r"[a-z0-9]([-a-z0-9]*[a-z0-9])?(\\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*"
    )

    @classmethod
    def from_charm(cls, charm: ops.CharmBase, client: Client) -> "CharmConfig":
        """Create a CharmConfig class from a charm instance.

        Args:
            charm (ops.CharmBase): The gateway-api-integrator charm.
            client (lightkube.Client): The lightkube client

        Raises:
            InvalidCharmConfigError: _description_
            GatewayClassUnavailableError: When the cluster has no available gateway classes.

        Returns:
            CharmConfig: Instance of the charm config state component.
        """
        gateway_class = typing.cast(str, charm.config.get("gateway-class"))
        gateway_class_generic_resource = create_global_resource(
            CUSTOM_RESOURCE_GROUP_NAME, "v1", GATEWAY_CLASS_RESOURCE_NAME, GATEWAY_CLASS_PLURAL
        )
        gateway_classes = tuple(client.list(gateway_class_generic_resource))
        if not gateway_classes:
            logger.error("No gateway class available on cluster.")
            raise GatewayClassUnavailableError("No gateway class available on cluster.")

        gateway_class_names = (
            gateway_class.metadata.name
            for gateway_class in gateway_classes
            if gateway_class.metadata and gateway_class.metadata.name
        )
        if gateway_class not in gateway_class_names:
            available_gateway_classes = ",".join(gateway_class_names)
            logger.error(
                (
                    "Configured gateway class %s not present on the cluster."
                    "Available ones are: %s"
                ),
                gateway_class,
                available_gateway_classes,
            )
            raise InvalidCharmConfigError(
                f"Gateway class must be one of {available_gateway_classes}"
            )

        try:
            return cls(
                gateway_class=gateway_class,
                external_hostname=typing.cast(str, charm.config.get("external-hostname")),
            )
        except ValidationError as exc:
            error_field_str = ",".join(f"{field}" for field in get_invalid_config_fields(exc))
            raise InvalidCharmConfigError(f"invalid configuration: {error_field_str}") from exc


def get_invalid_config_fields(exc: ValidationError) -> typing.Set[int | str]:
    """Return a list on invalid config from pydantic validation error.

    Args:
        exc (ValidationError): The validation error exception.

    Returns:
        str: list of fields that failed validation.
    """
    error_fields = set(itertools.chain.from_iterable(error["loc"] for error in exc.errors()))
    return error_fields
