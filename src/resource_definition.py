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
    config: ConfigData
    name: str
    model: Model

    def _get_config(self, field: str) -> Union[str, float, int, bool, None]:
        """Get data from charm config.

        Args:
            charm: The charm.
            field: Config field.

        Returns:
            The field's content.
        """
        # Config fields with a default of None don't appear in the dict
        config_data = self.config.get(field, None)
        return config_data


@dataclasses.dataclass
class GatewayResourceDefinition(ResourceDefinition):
    """Class containing ingress definition collected from the Charm configuration or relation.

    See config.yaml for descriptions of each property.
    """

    def __init__(  # pylint: disable=too-many-arguments
        self, name: str, config: ConfigData, model: Model
    ) -> None:
        """Create a GatewayResourceDefinition Object.

        Args:
            name: The gateway resource name.
            config: The charm's configuration.
        """
        super().__init__()
        self.name = name
        self.config = config
        self.model = model

    @property
    def hostname(self) -> str:
        hostname = cast(str, self._get_config("external-hostname"))
        if is_valid_hostname(hostname=hostname):
            return hostname
        return ""

    @property
    def gateway_class(self) -> str:
        gateway_class = cast(str, self._get_config("gateway-class"))
        return gateway_class

    @property
    def namespace(self) -> str:
        return self.model.name
