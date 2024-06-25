# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator configuration."""

import itertools
import typing

import ops
from pydantic import Field, ValidationError
from pydantic.dataclasses import dataclass


class InvalidCharmConfigError(Exception):
    """Exception raised when a charm configuration is found to be invalid.

    Attrs:
        msg (str): Explanation of the error.
    """

    def __init__(self, msg: str):
        """Initialize a new instance of the InvalidCharmConfigError exception.

        Args:
            msg (str): Explanation of the error.
        """
        self.msg = msg


@dataclass(frozen=True)
class CharmConfig:
    """A component of charm state that contains the charm's configuration.

    Attrs:
        gateway_class (str): The configured gateway class.
        external_hostname (str): The configured gateway hostname.
    """

    gateway_class: str = Field(min_length=1)
    external_hostname: str = Field(
        min_length=1, pattern=r"[a-z0-9]([-a-z0-9]*[a-z0-9])?(\\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*"
    )

    @classmethod
    def from_charm(cls, charm: ops.CharmBase) -> "CharmConfig":
        """Create a CharmConfig class from a charm instance.

        Args:
            charm (ops.CharmBase): The gateway-api-integrator charm.

        Raises:
            InvalidCharmConfigError: When validation of the charm's config failed.

        Returns:
            CharmConfig: Instance of the charm config state component.
        """
        try:
            return cls(
                gateway_class=typing.cast(str, charm.config.get("gateway-class")),
                external_hostname=typing.cast(str, charm.config.get("external-hostname")),
            )
        except ValidationError as exc:
            error_field_str = ",".join(f"{field}" for field in get_invalid_config_fields(exc))
            raise InvalidCharmConfigError(f"invalid configuration: {error_field_str}") from exc


def get_invalid_config_fields(exc: ValidationError) -> typing.Set[int | str]:
    """Return a list on invalid config from pydantic validation error.

    Args:
        exc (ValidationError): The validation error exception.

    Returns:
        str: list of fields that failed validation.
    """
    error_fields = set(itertools.chain.from_iterable(error["loc"] for error in exc.errors()))
    return error_fields
