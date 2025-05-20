# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator secret resource definition."""

import dataclasses

import ops


@dataclasses.dataclass(frozen=True)
class SecretResourceDefinition:
    """A component of charm state that contains secret resource definition.

    Attrs:
        secret_resource_name_prefix (str):
    """

    secret_resource_name_prefix: str

    @classmethod
    def from_charm(cls, charm: ops.CharmBase) -> "SecretResourceDefinition":
        """Create a resource definition from charm instance.

        Args:
            charm: The charm instance.

        Returns:
            SecretResourceDefinition: The secret resource definition object.
        """
        secret_resource_name_prefix = f"{charm.app.name}-secret"

        return cls(
            secret_resource_name_prefix=secret_resource_name_prefix,
        )
