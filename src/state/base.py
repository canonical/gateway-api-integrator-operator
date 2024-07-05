# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator charm state constructor."""
import dataclasses
from typing import Any, ClassVar, Protocol


class Dataclass(Protocol):  # pylint: disable=too-few-public-methods
    """Definition of dataclass."""

    # Checking for this attribute is currently
    # the most reliable way to ascertain that something is a dataclass
    __dataclass_fields__: ClassVar[dict[str, Any]]


class State:  # pylint: disable=too-few-public-methods
    """Fragment of charmstate that consists of one or several state components.

    A state component should always be a dataclass.
    """

    def __init__(self, *components: Dataclass):
        """Create the state object with state components.

        Args:
            components: state components with which the state fragment will be built.
        """
        for component in components:
            for field in dataclasses.fields(component):
                setattr(self, field.name, getattr(component, field.name))
