# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""gateway-api-integrator http_route resource manager."""


import logging
import typing

from lightkube import Client
from lightkube.core.client import LabelSelector
from lightkube.generic_resource import GenericNamespacedResource, create_namespaced_resource
from lightkube.models.meta_v1 import ObjectMeta
from lightkube.types import PatchType

from exception import ResourceManagementBaseError
from state.base import State
from state.http_route import HTTPRouteType

from .permission import map_k8s_auth_exception
from .resource_manager import ResourceManager

logger = logging.getLogger(__name__)

CUSTOM_RESOURCE_GROUP_NAME = "gateway.networking.k8s.io"
HTTP_ROUTE_RESOURCE_NAME = "HTTPRoute"
HTTP_ROUTE_PLURAL = "httproutes"


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
    def _gen_resource(self, state: State) -> GenericNamespacedResource:
        """Generate a Gateway resource from a gateway resource definition.

        Args:
            state: Part of charm state consisting of 3 components:
                - HTTPRouteResourceDefinition
                - GatewayResourceDefinition
                - HTTPRouteResourceType

        Returns:
            A dictionary representing the gateway custom resource.
        """
        listener_id = f"{state.gateway_name}-{state.http_route_type.value}-listener"
        spec = {
            "parentRefs": [
                {
                    "name": state.gateway_name,
                    "namespace": self._client.namespace,
                    "sectionName": listener_id,
                }
            ],
        }
        if state.http_route_type == HTTPRouteType.HTTPS:
            spec["rules"] = [
                {
                    "matches": [
                        {"path": {"type": "PathPrefix", "value": f"/{state.service_name}"}}
                    ],
                    "backendRefs": [{"name": state.service_name, "port": state.service_port}],
                }
            ]
        else:
            spec["rules"] = [
                {
                    "filters": [
                        {
                            "type": "RequestRedirect",
                            "requestRedirect": {"scheme": "https", "statusCode": 301},
                        }
                    ]
                }
            ]
        http_route = self._http_route_generic_resource_class(
            apiVersion=f"{CUSTOM_RESOURCE_GROUP_NAME}/v1",
            kind=HTTP_ROUTE_RESOURCE_NAME,
            metadata=ObjectMeta(
                name=f"{state.service_name}-{state.http_route_type.value}", labels=self._labels
            ),
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
