# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""Generic kubernetes resource manager for gateway-api-integrator."""

import abc
import functools
import logging
import typing

import lightkube
import lightkube.generic_resource
import lightkube.resources
import lightkube.resources.apiextensions_v1
import lightkube.resources.apps_v1
import lightkube.resources.core_v1
import lightkube.resources.discovery_v1
from lightkube.core.exceptions import ApiError

from state.config import CharmConfig
from state.gateway import GatewayResourceDefinition

logger = logging.getLogger(__name__)

AnyResource = typing.TypeVar(
    "AnyResource",
    lightkube.resources.core_v1.Endpoints,
    lightkube.resources.discovery_v1.EndpointSlice,
    lightkube.resources.core_v1.Service,
    lightkube.resources.core_v1.Secret,
    lightkube.generic_resource.GenericNamespacedResource,
)

ResourceDefinition: typing.TypeAlias = GatewayResourceDefinition

CREATED_BY_LABEL = "gateway-api-integrator.charm.juju.is/managed-by"


class InvalidResourceError(Exception):
    """Custom error that indicates invalid resource definition.

    Args:
        msg: error message.
    """

    def __init__(self, msg: str):
        """Construct the InvalidGatewayError object.

        Args:
            msg: error message.
        """
        self.msg = msg


class InsufficientPermissionError(Exception):
    """Custom error that indicates insufficient permission to create k8s resources.

    Args:
        msg: error message.
    """

    def __init__(self, msg: str):
        """Construct the InsufficientPermissionError object.

        Args:
            msg: error message.
        """
        self.msg = msg


def _map_k8s_auth_exception(func: typing.Callable) -> typing.Callable:
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


# Helper function here since AnyResource are lightkube classes
def resource_name(resource: AnyResource | None) -> typing.Optional[str]:
    """Get the resource name from metadata.

    Args:
        resource (AnyResource): The kubernetes resource.

    Returns:
        typing.Optional[str]: The resource name, or None if not set.
    """
    if resource is None or resource.metadata is None or resource.metadata.name is None:
        return None
    return resource.metadata.name


class ResourceManager(typing.Protocol[AnyResource]):
    """Abstract base class for a generic Kubernetes resource controller."""

    @property
    @abc.abstractmethod
    def _name(self) -> str:
        """Abstract property that returns the name of the resource type.

        Returns:
            Name of the resource type.
        """

    @abc.abstractmethod
    def _gen_resource(self, definition: ResourceDefinition, config: CharmConfig) -> AnyResource:
        """Abstract method to generate a resource from ingress definition.

        Args:
            definition: Ingress definition to use for generating the resource.
            config: The charm's configuration.
        """

    @abc.abstractmethod
    def _create_resource(self, resource: AnyResource) -> None:
        """Abstract method to create a new resource in the current namespace.

        Args:
            resource: The resource object to create.
        """

    @abc.abstractmethod
    def _patch_resource(self, name: str, resource: AnyResource) -> None:
        """Abstract method to patch an existing resource in the current namespace.

        Args:
            name: The name of the resource to patch.
            resource: The modified resource object.
        """

    @abc.abstractmethod
    def _list_resource(self) -> typing.List[AnyResource]:
        """Abstract method to list resources in the current namespace based on a label selector."""

    @abc.abstractmethod
    def _delete_resource(self, name: str) -> None:
        """Abstract method to delete a resource from the current namespace.

        Args:
            name: The name of the resource to delete.
        """

    def define_resource(self, definition: ResourceDefinition, config: CharmConfig) -> AnyResource:
        """Create or update a resource in kubernetes.

        Args:
            definition: The ingress definition
            config: The charm's configuration.

        Returns:
            The name of the created or modified resource.

        Raises:
            InvalidResourceError: If the generated resource is invalid.
        """
        resource_list = self._list_resource()
        resource = self._gen_resource(definition, config)
        res_name = resource_name(resource)
        if not res_name:
            raise InvalidResourceError("Missing resource name.")

        resources = [resource_name(r) for r in resource_list if resource_name(r) is not None]
        if res_name in resources:
            self._patch_resource(name=res_name, resource=resource)
        else:
            self._create_resource(resource=resource)
        return resource

    def cleanup_resources(
        self,
        exclude: typing.Optional[AnyResource] = None,
    ) -> None:
        """Remove unused resources.

        Args:
            exclude: The name of resource to be excluded from the cleanup.
        """
        for resource in self._list_resource():
            excluded_resource_name = resource_name(exclude)
            res_name = resource_name(resource)
            if not res_name or not excluded_resource_name:
                continue
            if res_name == excluded_resource_name:
                continue
            self._delete_resource(name=res_name)
