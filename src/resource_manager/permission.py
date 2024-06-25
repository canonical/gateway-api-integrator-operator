# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""Decorator for mapping k8s 403 exceptions."""


import functools
import logging
import typing

from lightkube.core.exceptions import ApiError

from exception import CharmStateValidationBaseError

logger = logging.getLogger(__name__)


class InsufficientPermissionError(CharmStateValidationBaseError):
    """Custom error that indicates insufficient permission to create k8s resources."""


def map_k8s_auth_exception(func: typing.Callable) -> typing.Callable:
    """Remap the kubernetes 403 ApiException to InsufficientPermissionError.

    Args:
        func: function to be wrapped.

    Returns:
        A wrapped function.
    """

    @functools.wraps(func)
    def wrapper(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        """Remap the kubernetes 403 ApiException to InsufficientPermissionError.

        Args:
            args: function arguments.
            kwargs: function keyword arguments.

        Returns:
            The function return value.

        Raises:
            ApiException: if the Python kubernetes raised an unknown ApiException
            InsufficientPermissionError: if the Python kubernetes raised a permission error
        """
        try:
            return func(*args, **kwargs)
        except ApiError as exc:
            if exc.status.code == 403:
                logger.error(
                    "Insufficient permissions to create the k8s service, "
                    "will request `juju trust` to be run"
                )
                juju_trust_cmd = "juju trust <gateway-api-integrator> --scope=cluster"
                raise InsufficientPermissionError(
                    f"Insufficient permissions, try: `{juju_trust_cmd}`"
                ) from exc
            raise

    return wrapper
