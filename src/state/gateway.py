# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator resource definition."""

import dataclasses

import ops


@dataclasses.dataclass(frozen=True)
class GatewayResourceDefinition:
    """Base class containing kubernetes resource definition.

    Attrs:
        namespace: The gateway resource's namespace.
        gateway_name: The gateway resource's name
    """

    namespace: str
    gateway_name: str

    @classmethod
    def from_charm(cls, charm: ops.CharmBase) -> "GatewayResourceDefinition":
        """Create a resource definition from charm instance.

        Args:
            charm (ops.CharmBase): _description_

        Returns:
            ResourceDefinition: _description_
        """
        return cls(namespace=charm.model.name, gateway_name=charm.app.name)
