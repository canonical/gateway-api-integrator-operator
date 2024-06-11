# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator resource definition."""

import itertools
import typing
import ops
import dataclasses

from pydantic import BaseModel, Field, ValidationError


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


@dataclasses.dataclass(frozen=True)
class CharmConfig(BaseModel):
    """A component of charm state that contains the charm's configuration.

    Attrs:
        gateway_class (_type_): _description_
        external_hostname: The configured gateway hostname.
    """

    gateway_class: str = Field(min_length=1)
    external_hostname: str = Field(
        pattern=r"[a-z0-9]([-a-z0-9]*[a-z0-9])?(\\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*"
    )

    @classmethod
    def from_charm(cls, charm: ops.CharmBase) -> "CharmConfig":
        """Create a CharmConfig class from a charm instance.

        Args:
            charm (ops.CharmBase): _description_

        Raises:
            InvalidCharmConfigError: _description_

        Returns:
            CharmConfig: _description_
        """
        try:
            return cls(
                gateway_class=typing.cast(str, charm.config.get("gateway-class")),
                external_hostname=typing.cast(str, charm.config.get("external-hostname")),
            )
        except ValidationError as exc:
            error_field_str = ",".join(f"{f}" for f in get_invalid_config_fields(exc))
            raise InvalidCharmConfigError(f"invalid configuration: {error_field_str}") from exc


def get_invalid_config_fields(exc: ValidationError) -> typing.Set[int | str]:
    """Return a list on invalid config from pydantic validation error.

    Args:
        exc (ValidationError): _description_

    Returns:
        str: _description_
    """
    error_fields = set(itertools.chain.from_iterable(error["loc"] for error in exc.errors()))
    return error_fields
