# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for functions containing charm utilities."""

import functools
import logging
import typing

import ops
from ops.model import SecretNotFoundError

from resource_manager.resource_manager import InvalidResourceError
from state.exception import CharmStateValidationBaseError
from tls_relation import InvalidCertificateError

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
        method: typing.Callable[[C, typing.Any], None],
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
                InvalidResourceError: when creation of k8s resources fails.
                InvalidCertificateError: When the provider certificate is invalid.
                SecretNotFoundError: When the required juju secret is missing.
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
            except InvalidResourceError:
                logger.exception("Error creating kubernetes resource")
                raise
            except (InvalidCertificateError, SecretNotFoundError):
                logger.exception("TLS certificates error.")
                raise

        return wrapper

    return decorator
