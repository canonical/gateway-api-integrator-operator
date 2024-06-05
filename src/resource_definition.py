# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator resource definition."""

import dataclasses
import re
from typing import Union, cast

from ops.model import ConfigData, Model


def is_valid_hostname(hostname: str) -> bool:
    """Check if a hostname is valid.

    Args:
        hostname: hostname to check.

    Returns:
        If the hostname is valid.
    """
    # This regex comes from the error message kubernetes shows when trying to set an
    # invalid hostname.
    # See https://github.com/canonical/nginx-ingress-integrator-operator/issues/2
    # for an example.
    if not hostname:
        return False
    result = re.fullmatch(
        "[a-z0-9]([-a-z0-9]*[a-z0-9])?(\\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*", hostname
    )
    if result:
        return True
    return False


class ResourceDefinition:
    """Base class containing kubernetes resource definition.

    Attrs:
        config: The config data of the charm.
        name: The name of the resource.
        model: The model of the charm, used to determine the resource's namespace.
        namespace: The resource's namespace.
    """

    config: ConfigData
    name: str
    model: Model

    def get_config(self, field: str) -> Union[str, float, int, bool, None]:
        """Get data from charm config.

        Args:
            field: Config field to get.

        Returns:
            The field's content.
        """
        # Config fields with a default of None don't appear in the dict
        config_data = self.config.get(field, None)
        return config_data

    @property
    def namespace(self) -> str:
        """The namespace of the resource."""
        return self.model.name


@dataclasses.dataclass
class GatewayResourceDefinition(ResourceDefinition):
    """Class containing information about the gateway object.

    Attrs:
        hostname: The hostname of the gateway's listeners.
        gateway_class: The gateway class.
    """

    def __init__(self, name: str, config: ConfigData, model: Model) -> None:
        """Create a GatewayResourceDefinition Object.

        Args:
            name: The gateway resource name.
            config: The charm's configuration.
            model: The charm's juju model.
        """
        super().__init__()
        self.name = name
        self.config = config
        self.model = model

    @property
    def hostname(self) -> str:
        """The hostname of the gateway's listeners."""
        hostname = cast(str, self.get_config("external-hostname"))
        if is_valid_hostname(hostname=hostname):
            return hostname
        return ""

    @property
    def gateway_class(self) -> str:
        """The gateway's gateway class defined via config."""
        gateway_class = cast(str, self.get_config("gateway-class"))
        return gateway_class
