# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator resource definition."""

import itertools
import typing

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


class CharmConfig(BaseModel):
    """Charm configuration.

    Attrs:
        gateway_class (_type_): _description_
        external_hostname: The configured gateway hostname.
    """

    gateway_class: str = Field(min_length=1)
    external_hostname: str = Field(
        pattern=r"[a-z0-9]([-a-z0-9]*[a-z0-9])?(\\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*"
    )


def get_invalid_config_fields(exc: ValidationError) -> typing.Set[int | str]:
    """Return a list on invalid config from pydantic validation error.

    Args:
        exc (ValidationError): _description_

    Returns:
        str: _description_
    """
    error_fields = set(itertools.chain.from_iterable(error["loc"] for error in exc.errors()))
    return error_fields
