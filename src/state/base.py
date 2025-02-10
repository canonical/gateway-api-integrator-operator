# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator charm state constructor."""
import dataclasses
import typing

from .config import CharmConfig
from .gateway import GatewayResourceInformation
from .tls import TLSInformation

Components = typing.TypeVar(
    "Components",
    GatewayResourceInformation,
    CharmConfig,
    TLSInformation,
)


class ResourceDefinition:  # pylint: disable=too-few-public-methods
    """Fragment of charmstate that consists of one or several state components."""

    def __init__(self, *components: Components):
        """Create the state object with state components.

        Args:
            components: state components with which the state fragment will be built.
        """
        for component in components:
            for field in dataclasses.fields(component):
                setattr(self, field.name, getattr(component, field.name))
