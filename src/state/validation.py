# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Decorator for state validation and set charm status."""

import functools
import logging
import typing

import ops

from .config import InvalidCharmConfigError
from .tls import TlsIntegrationMissingError

logger = logging.getLogger()


def block_if_not_ready(
    defer: bool = False,
) -> typing.Callable[
    [typing.Callable[[ops.CharmBase, ops.EventBase], None]],
    typing.Callable[[ops.CharmBase, ops.EventBase], None],
]:
    """Create a decorator that puts the charm in blocked state if the config is wrong.

    Args:
        defer: whether to defer the event.

    Returns:
        the function decorator.
    """

    def decorator(
        method: typing.Callable[[ops.CharmBase, ops.EventBase], None]
    ) -> typing.Callable[[ops.CharmBase, ops.EventBase], None]:
        """Create a decorator that puts the charm in blocked state if the config is wrong.

        Args:
            method: observer method to wrap.

        Returns:
            the function wrapper.
        """

        @functools.wraps(method)
        def wrapper(charm: ops.CharmBase, event: ops.EventBase) -> None:
            """Block the charm if the config is wrong.

            Args:
                charm: the charm instance.
                event: the event for the observer.

            Returns:
                The value returned from the original function. That is, None.
            """
            try:
                return method(charm, event)
            except InvalidCharmConfigError as exc:
                logger.exception("Invalid charm configuration: %s", exc)
                if defer:
                    event.defer()
                charm.unit.status = ops.BlockedStatus(exc.msg)
                return None
            except TlsIntegrationMissingError as exc:
                if defer:
                    event.defer()
                logger.exception("Waiting for TLS: %s", exc)
                charm.unit.status = ops.BlockedStatus("Waiting for TLS")
                return None

        return wrapper

    return decorator
