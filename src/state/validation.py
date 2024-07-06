# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for functions containing charm utilities."""

import functools
import logging
import typing

import ops

from exception import CharmStateValidationBaseError
from resource_manager.resource_manager import InvalidResourceError

logger = logging.getLogger(__name__)

C = typing.TypeVar("C", bound=ops.CharmBase)


def validate_config_and_integration(
    defer: bool = False,
) -> typing.Callable[
    [typing.Callable[[C, typing.Any], None]], typing.Callable[[C, typing.Any], None]
]:
    """Create a decorator that puts the charm in blocked state if the config is wrong.

    Args:
        defer: whether to defer the event.

    Returns:
        the function decorator.
    """

    def decorator(
        method: typing.Callable[[C, typing.Any], None]
    ) -> typing.Callable[[C, typing.Any], None]:
        """Create a decorator that puts the charm in blocked state if the config is wrong.

        Args:
            method: observer method to wrap.

        Returns:
            the function wrapper.
        """

        @functools.wraps(method)
        def wrapper(instance: C, *args: typing.Any) -> None:
            """Block the charm if the config is wrong.

            Args:
                instance: the instance of the class with the hook method.
                args: Additional events

            Returns:
                The value returned from the original function. That is, None.

            Raises:
                RuntimeError: when creation of k8s resources fails.
            """
            try:
                return method(instance, *args)
            except CharmStateValidationBaseError as exc:
                if defer:
                    event: ops.EventBase
                    event, *_ = args
                    event.defer()
                logger.exception("Error setting up charm state.")
                instance.unit.status = ops.BlockedStatus(str(exc))
                return None
            except InvalidResourceError as exc:
                logger.exception("Error creating kubernetes resource")
                raise RuntimeError("Error creating kubernetes resource.") from exc

        return wrapper

    return decorator
