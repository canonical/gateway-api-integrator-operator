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

from resource_definition import GatewayResourceDefinition

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


class KuberentesCreateResourceError(Exception):
    """Custom error that indicates insufficient permission to create k8s resources.

    Args:
        msg: error message.
    """

    def __init__(self, msg: str):
        """Construct the KuberentesCreateResourceError object.

        Args:
            msg: error message.
        """
        self.msg = msg


def _map_k8s_auth_exception(func: typing.Callable) -> typing.Callable:
    """Remap the kubernetes 403 ApiException to KuberentesCreateResourceError.

    Args:
        func: function to be wrapped.

    Returns:
        A wrapped function.
    """

    @functools.wraps(func)
    def wrapper(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        """Remap the kubernetes 403 ApiException to KuberentesCreateResourceError.

        Args:
            args: function arguments.
            kwargs: function keyword arguments.

        Returns:
            The function return value.

        Raises:
            ApiException: if the Python kubernetes raised an unknown ApiException
            KuberentesCreateResourceError: if the Python kubernetes raised a permission error
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
                raise KuberentesCreateResourceError(
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
    if resource is None:
        return None
    if resource.metadata is None:
        return None
    if resource.metadata.name is None:
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

    @property
    @abc.abstractmethod
    def _namespace(self) -> str:
        """Abstract property that returns the namespace of the controller.

        Returns:
            The namespace.
        """

    @abc.abstractmethod
    def _gen_resource_from_definition(self, definition: ResourceDefinition) -> AnyResource:
        """Abstract method to generate a resource from ingress definition.

        Args:
            definition: Ingress definition to use for generating the resource.
        """

    @abc.abstractmethod
    def _create_resource(self, resource: AnyResource) -> None:
        """Abstract method to create a new resource in a given namespace.

        Args:
            resource: The resource object to create.
        """

    @abc.abstractmethod
    def _patch_resource(self, name: str, resource: AnyResource) -> None:
        """Abstract method to patch an existing resource in a given namespace.

        Args:
            name: The name of the resource to patch.
            resource: The modified resource object.
        """

    @abc.abstractmethod
    def _list_resource(self) -> typing.List[AnyResource]:
        """Abstract method to list resources in a given namespace based on a label selector."""

    @abc.abstractmethod
    def _delete_resource(self, name: str) -> None:
        """Abstract method to delete a resource from a given namespace.

        Args:
            name: The name of the resource to delete.
        """

    def define_resource(
        self,
        definition: ResourceDefinition,
    ) -> AnyResource:
        """Create or update a resource in kubernetes.

        Args:
            definition: The ingress definition

        Returns:
            The name of the created or modified resource.

        Raises:
            InvalidResourceError: If the generated resource is invalid.
        """
        resource_list = self._list_resource()
        resource = self._gen_resource_from_definition(definition)
        if not resource.metadata:
            raise InvalidResourceError("Missing resource metadata.")

        if not resource.metadata.name:
            raise InvalidResourceError("Missing resource name.")

        resources = [r.metadata.name for r in resource_list if r.metadata]
        if resource.metadata.name in resources:
            self._patch_resource(name=resource.metadata.name, resource=resource)
            logger.info(
                "%s updated in namespace %s with name %s",
                self._name,
                self._namespace,
                resource.metadata.name,
            )
        else:
            self._create_resource(resource=resource)
            logger.info(
                "%s created in namespace %s with name %s",
                self._name,
                self._namespace,
                resource.metadata.name,
            )
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
            if res_name is None or excluded_resource_name is None:
                continue
            if res_name == excluded_resource_name:
                continue
            self._delete_resource(name=res_name)
            logger.info(
                "%s deleted in namespace %s with name %s",
                self._name,
                self._namespace,
                resource,
            )
