# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator charm state constructor."""

import dataclasses
import typing

from src.state.http_route import HTTPRouteResourceInformation

from .config import CharmConfig
from .gateway import GatewayResourceInformation
from .tls import TLSInformation

Component = typing.Union[
    GatewayResourceInformation,
    CharmConfig,
    TLSInformation,
    HTTPRouteResourceInformation,
]


class ResourceDefinition:  # pylint: disable=too-few-public-methods
    """Fragment of charm state that consists of one or several state components."""

    def __init__(self, *components: Component):
        """Create the state object with state components.

        Args:
            components: state components with which the state fragment will be built.
        """
        for component in components:
            for field in dataclasses.fields(component):
                setattr(self, field.name, getattr(component, field.name))
