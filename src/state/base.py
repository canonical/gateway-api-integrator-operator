# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator charm state constructor."""
import dataclasses
import typing

from .config import CharmConfig
from .gateway import GatewayResourceDefinition
from .secret import SecretResourceDefinition
from .tls import TLSInformation

Components = typing.TypeVar(
    "Components", GatewayResourceDefinition, CharmConfig, SecretResourceDefinition, TLSInformation
)


class State:  # pylint: disable=too-few-public-methods
    """Fragment of charmstate that consists of one or several state components."""

    def __init__(self, *components: Components):
        """Create the state object with state components.

        Args:
            components: state components with which the state fragment will be built.
        """
        for c in components:
            for field in dataclasses.fields(type(c)):
                setattr(self, field.name, getattr(c, field.name))
