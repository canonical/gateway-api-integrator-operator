# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""Generic kubernetes resource manager for gateway-api-integrator."""

import abc
import logging
import typing

from lightkube.generic_resource import GenericNamespacedResource
from lightkube.resources.core_v1 import Secret, Service

from state.base import ResourceDefinition

logger = logging.getLogger(__name__)

AnyResource = typing.TypeVar(
    "AnyResource",
    Service,
    Secret,
    GenericNamespacedResource,
)
CREATED_BY_LABEL = "gateway-api-integrator.charm.juju.is/managed-by"


class InvalidResourceError(Exception):
    """Custom error that indicates invalid resource definition."""


# Helper function here since AnyResource are lightkube classes
def resource_name(resource: AnyResource | None) -> typing.Optional[str]:
    """Get the resource name from metadata.

    Args:
        resource: The kubernetes resource.

    Returns:
        typing.Optional[str]: The resource name, or None if not set.
    """
    if resource is None or resource.metadata is None or resource.metadata.name is None:
        return None
    return resource.metadata.name


class ResourceManager(typing.Protocol[AnyResource]):
    """Abstract base class for a generic Kubernetes resource controller."""

    @abc.abstractmethod
    def _gen_resource(self, resource_definition: ResourceDefinition) -> AnyResource:
        """Abstract method to generate a resource from ingress definition.

        Args:
            resource_definition: The data necessary to create the k8s resource.
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

    def define_resource(self, state: ResourceDefinition) -> AnyResource:
        """Create or update a resource in kubernetes.

        Args:
            state: Fragment of charm state consists of several components.

        Returns:
            The name of the created or modified resource.

        Raises:
            InvalidResourceError: If the generated resource is invalid.
        """
        resource_list = self._list_resource()
        resource = self._gen_resource(state)
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
        exclude: list[AnyResource],
    ) -> None:
        """Remove unused resources.

        Args:
            exclude: The name of resource to be excluded from the cleanup.
        """
        excluded_resource_names = [resource_name(resource) for resource in exclude]
        for resource in self._list_resource():
            res_name = resource_name(resource)
            if not res_name or res_name in excluded_resource_names:
                continue
            self._delete_resource(name=res_name)
