# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""gateway-api-integrator service resource manager."""


import dataclasses
import logging
import typing

from lightkube import Client
from lightkube.core.client import LabelSelector
from lightkube.models.core_v1 import ServicePort, ServiceSpec
from lightkube.models.meta_v1 import ObjectMeta
from lightkube.resources.core_v1 import Service
from lightkube.types import PatchType

from state.base import ResourceDefinition
from state.http_route import HTTPRouteResourceInformation

from .permission import map_k8s_auth_exception
from .resource_manager import ResourceManager

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class ServiceResourceDefinition(ResourceDefinition):
    """A part of charm state with information required to manage gateway resource.

    It consists of 1 components:
        - ServiceResourceDefinition

    Attributes:
        service_name: The gateway resource's name
        service_port: The configured gateway hostname.
        service_port_name: The configured gateway class.
        application_name: The application name.
    """

    service_name: str
    service_port: int
    service_port_name: str
    application_name: str

    def __init__(
        self,
        http_route_resource_information: HTTPRouteResourceInformation,
    ):
        """Create the state object with state components.

        Args:
            http_route_resource_information: HTTPRouteResourceInformation state component.
        """
        super().__init__(http_route_resource_information)


class ServiceResourceManager(ResourceManager[Service]):
    """service resource manager."""

    def __init__(self, labels: LabelSelector, client: Client) -> None:
        """Initialize the ServiceResourceManager.

        Args:
            labels: Label to be added to created resources.
            client: Initialized lightkube client.
        """
        self._client = client
        self._labels = labels

    @map_k8s_auth_exception
    def _gen_resource(self, resource_definition: ResourceDefinition) -> Service:
        """Generate a Gateway resource from a gateway resource definition.

        Args:
            resource_definition: Part of charm state consisting of 1 component:
                - HTTPRouteResourceManager

        Returns:
            A dictionary representing the gateway custom resource.
        """
        service_resource_definition = typing.cast(ServiceResourceDefinition, resource_definition)

        service = Service(
            apiVersion="v1",
            kind="Service",
            metadata=ObjectMeta(
                name=service_resource_definition.service_name, labels=self._labels
            ),
            spec=ServiceSpec(
                ports=[
                    ServicePort(
                        port=service_resource_definition.service_port,
                        name=service_resource_definition.service_port_name,
                        targetPort=service_resource_definition.service_port,
                    )
                ],
                selector={"app.kubernetes.io/name": service_resource_definition.application_name},
            ),
        )

        return service

    @map_k8s_auth_exception
    def _create_resource(self, resource: Service) -> None:
        """Create a new secret resource in a given namespace.

        Args:
            resource: The secret resource object to create.
        """
        self._client.create(resource)

    @map_k8s_auth_exception
    def _patch_resource(self, name: str, resource: Service) -> None:
        """Replace an existing gateway resource in the current namespace.

        Args:
            name: The name of the resource to patch.
            resource: The modified gateway resource object.
        """
        # Patch the resource with server-side apply
        # force=True is required here so that the charm keeps control of the resource
        self._client.patch(  # type: ignore[type-var]
            # mypy can't detect that this is ok for patching custom resources
            Service,
            name,
            resource,
            patch_type=PatchType.APPLY,
            force=True,
        )

    @map_k8s_auth_exception
    def _list_resource(self) -> typing.List[Service]:
        """List secret resources in a given namespace based on a label selector.

        Returns:
            A list of matched secret resources.
        """
        return list(self._client.list(res=Service, labels=self._labels))

    @map_k8s_auth_exception
    def _delete_resource(self, name: str) -> None:
        """Delete a secret resource from a given namespace.

        Args:
            name: The name of the secret resource to delete.
        """
        self._client.delete(res=Service, name=name)
