# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator secret resource definition."""

import dataclasses

import ops


@dataclasses.dataclass(frozen=True)
class SecretResourceDefinition:
    """_summary_.

    Raises:
        InvalidCharmConfigError: _description_

    Attrs:
        secret_resource_name_prefix (str):

    Returns:
        _type_: _description_
    """

    secret_resource_name_prefix: str

    @classmethod
    def from_charm(cls, charm: ops.CharmBase) -> "SecretResourceDefinition":
        """Create a resource definition from charm instance.

        Args:
            charm (ops.CharmBase): _description_

        Returns:
            ResourceDefinition: _description_
        """
        secret_resource_name_prefix = f"{charm.app.name}-secret-"

        return cls(
            secret_resource_name_prefix=secret_resource_name_prefix,
        )
