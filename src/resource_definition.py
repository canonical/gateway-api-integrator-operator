# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator resource definition."""

import dataclasses
import itertools
import typing

import ops
from pydantic import BaseModel, Field, ValidationError


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


class CharmConfig(BaseModel):
    """Charm configuration.

    Attrs:
        gateway_class (_type_): _description_
        external_hostname: The configured gateway hostname.
    """

    gateway_class: str = Field(min_length=1)
    external_hostname: str = Field(
        pattern=r"[a-z0-9]([-a-z0-9]*[a-z0-9])?(\\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*"
    )


@dataclasses.dataclass(frozen=True)
class GatewayResourceDefinition:
    """Base class containing kubernetes resource definition.

    Attrs:
        config: The config data of the charm.
        gateway_name: The gateway resource's name
    """

    config: CharmConfig
    gateway_name: str

    @classmethod
    def from_charm(cls, charm: ops.CharmBase) -> "GatewayResourceDefinition":
        """Create a resource definition from charm instance.

        Args:
            charm (ops.CharmBase): _description_

        Raises:
            InvalidCharmConfigError: _description_

        Returns:
            ResourceDefinition: _description_
        """
        try:
            config = CharmConfig(
                gateway_class=typing.cast(str, charm.config.get("gateway-class")),
                external_hostname=typing.cast(str, charm.config.get("external-hostname")),
            )
            gateway_name = charm.app.name
        except ValidationError as exc:
            error_fields = set(
                itertools.chain.from_iterable(error["loc"] for error in exc.errors())
            )
            error_field_str = " ".join(f"{field}" for field in error_fields)
            raise InvalidCharmConfigError(f"invalid configuration: {error_field_str}") from exc

        return cls(config=config, gateway_name=gateway_name)
