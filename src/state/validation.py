# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for functions containing charm utilities."""

import functools
import logging
import typing

import ops
from ops.model import SecretNotFoundError

import client
from resource_manager.resource_manager import InvalidResourceError
from state.exception import CharmStateValidationBaseError
from state.http_route import IngressIntegrationMissingError
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
            except (CharmStateValidationBaseError, IngressIntegrationMissingError) as exc:
                if defer:
                    event: ops.EventBase
                    event, *_ = args
                    event.defer()
                logger.exception("Error setting up charm state component: %s", str(exc))
                instance.unit.status = ops.BlockedStatus(str(exc))
                _clean_up_resources_in_blocked_state(instance)
                return None
            except InvalidResourceError:
                logger.exception("Error creating kubernetes resource")
                raise
            except (InvalidCertificateError, SecretNotFoundError):
                logger.exception("TLS certificates error.")
                raise

        return wrapper

    return decorator


# We broadly catch all of the exceptions here because we don't want to raise another exception
# during exception handling. This method is private by design to prevent it from being used
# elsewhere.
# pylint: disable=broad-exception-caught
def _clean_up_resources_in_blocked_state(instance: ops.CharmBase) -> None:
    """Clean up all managed resources in the k8s namespace.

    This method should only be called in the exception handling code of the
    `validate_config_and_integration` decorator. We assume that at this point every resources
    except for the `gateway` and `secret` resources are no longer needed.

    Args:
        instance: The charm instance.
    """
    try:
        client.cleanup_all_resources(
            client.get_client(field_manager=instance.app.name, namespace=instance.model.name),
            client.application_label_selector(instance.app.name),
        )
    except Exception:
        logger.exception("Error raised during cleanup while handling another error, skipping.")
