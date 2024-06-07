# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator resource definition."""

import dataclasses
import typing

import ops
from pydantic import ValidationError

from .config import CharmConfig, InvalidCharmConfigError, get_invalid_config_fields


@dataclasses.dataclass(frozen=True)
class GatewayResourceDefinition:
    """Base class containing kubernetes resource definition.

    Attrs:
        config: The config data of the charm.
        namespace: The gateway resource's namespace.
        gateway_name: The gateway resource's name
    """

    config: CharmConfig
    namespace: str
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
            namespace = charm.model.name
            gateway_name = charm.app.name
        except ValidationError as exc:
            error_field_str = ",".join(f"{f}" for f in get_invalid_config_fields(exc))
            raise InvalidCharmConfigError(f"invalid configuration: {error_field_str}") from exc

        return cls(config=config, namespace=namespace, gateway_name=gateway_name)
