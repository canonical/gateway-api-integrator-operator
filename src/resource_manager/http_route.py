# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""gateway-api-integrator http_route resource manager."""


import logging
import typing
from enum import Enum

from lightkube import Client
from lightkube.core.client import LabelSelector
from lightkube.generic_resource import GenericNamespacedResource, create_namespaced_resource
from lightkube.models.meta_v1 import ObjectMeta
from lightkube.types import PatchType

from exception import ResourceManagementBaseError
from state.gateway import GatewayResourceDefinition
from state.http_route import HTTPRouteResourceDefinition

from .decorator import map_k8s_auth_exception
from .resource_manager import ResourceManager

logger = logging.getLogger(__name__)

CUSTOM_RESOURCE_GROUP_NAME = "httproute.gateway.networking.k8s.io"
HTTP_ROUTE_RESOURCE_NAME = "HTTPRoute"
HTTP_ROUTE_PLURAL = "httproutes"


class CreateHTTPRouteError(ResourceManagementBaseError):
    """Represents an error when creating the secret resource."""


class HTTPRouteType(Enum):
    """_summary_.

    Attrs:
        HTTP: _description_
        HTTPS: _description_
    """

    HTTP = "http"
    HTTPS = "https"


class HTTPRouteResourceManager(ResourceManager[GenericNamespacedResource]):
    """service resource manager."""

    def __init__(self, labels: LabelSelector, client: Client) -> None:
        """Initialize the HTTPRouteResourceManager.

        Args:
            labels: Label to be added to created resources.
            client: Initialized lightkube client.
        """
        self._client = client
        self._labels = labels
        self._http_route_generic_resource_class = create_namespaced_resource(
            CUSTOM_RESOURCE_GROUP_NAME, "v1", HTTP_ROUTE_RESOURCE_NAME, HTTP_ROUTE_PLURAL
        )

    @map_k8s_auth_exception
    def _gen_resource(
        self, definition: HTTPRouteResourceDefinition, *args: typing.Any
    ) -> GenericNamespacedResource:
        """Generate a Gateway resource from a gateway resource definition.

        Args:
            definition: The gateway resoucre definition to use.
            args: Additional arguments.

        Returns:
            A dictionary representing the gateway custom resource.

        Raises:
            CreateHTTPRouteError: if the method is not called with the correct arguments.
        """
        if (
            len(args) != 2
            or not isinstance(args[0], GatewayResourceDefinition)
            or not isinstance(args[1], HTTPRouteType)
        ):
            raise CreateHTTPRouteError("_gen_resource called with the wrong parameters.")

        http_route_type: HTTPRouteType
        gateway_resource_definition: GatewayResourceDefinition
        http_route_type, gateway_resource_definition = args

        spec = {
            "parentRefs": [
                {
                    "name": gateway_resource_definition.gateway_name,
                    "namespace": self._client.namespace,
                    "sectionName": f"{http_route_type}-listener",
                }
            ],
        }
        if http_route_type == HTTPRouteType.HTTPS:
            spec["rules"] = [
                {
                    "matches": [
                        {"path": {"type": "PathPrefix", "value": f"/{definition.service_name}"}}
                    ],
                    "backendRefs": [
                        {"name": definition.service_name, "port": definition.service_port}
                    ],
                }
            ]
        else:
            spec["rules"] = [
                {
                    "filters": [
                        {
                            "type": "RequestRedirect",
                            "RequestRedirect": {"scheme": "https", "statusCode": 301},
                        }
                    ]
                }
            ]
        http_route = self._http_route_generic_resource_class(
            apiVersion="v1",
            kind="Service",
            metadata=ObjectMeta(name=definition.service_name, labels=self._labels),
            spec=spec,
        )

        return http_route

    @map_k8s_auth_exception
    def _create_resource(self, resource: GenericNamespacedResource) -> None:
        """Create a new secret resource in a given namespace.

        Args:
            resource: The secret resource object to create.
        """
        self._client.create(resource)

    @map_k8s_auth_exception
    def _patch_resource(self, name: str, resource: GenericNamespacedResource) -> None:
        """Replace an existing gateway resource in the current namespace.

        Args:
            name: The name of the resource to patch.
            resource: The modified gateway resource object.
        """
        # Patch the resource with server-side apply
        # force=True is required here so that the charm keeps control of the resource
        self._client.patch(  # type: ignore[type-var]
            # mypy can't detect that this is ok for patching custom resources
            self._http_route_generic_resource_class,
            name,
            resource,
            patch_type=PatchType.APPLY,
            force=True,
        )

    @map_k8s_auth_exception
    def _list_resource(self) -> typing.List[GenericNamespacedResource]:
        """List secret resources in a given namespace based on a label selector.

        Returns:
            A list of matched secret resources.
        """
        return list(
            self._client.list(res=self._http_route_generic_resource_class, labels=self._labels)
        )

    @map_k8s_auth_exception
    def _delete_resource(self, name: str) -> None:
        """Delete a secret resource from a given namespace.

        Args:
            name: The name of the secret resource to delete.
        """
        self._client.delete(res=self._http_route_generic_resource_class, name=name)
