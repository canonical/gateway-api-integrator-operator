# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator resource definition."""

import dataclasses

import ops


@dataclasses.dataclass(frozen=True)
class GatewayResourceDefinition:
    """A component of charm state that contains gateway resource definition.

    Attrs:
        gateway_name: The gateway resource's name
    """

    # We're expecting more fields to be added.
    gateway_name: str

    @classmethod
    def from_charm(cls, charm: ops.CharmBase) -> "GatewayResourceDefinition":
        """Create a resource definition from charm instance.

        Args:
            charm: The charm instance.

        Returns:
            GatewayResourceDefinition: The gateway resource definition object.
        """
        return cls(gateway_name=charm.app.name)
