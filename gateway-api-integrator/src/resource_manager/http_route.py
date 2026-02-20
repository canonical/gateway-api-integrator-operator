# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""gateway-api-integrator http_route resource manager."""

import dataclasses
import logging
import typing
from enum import StrEnum

from lightkube import Client
from lightkube.core.client import LabelSelector
from lightkube.generic_resource import GenericNamespacedResource, create_namespaced_resource
from lightkube.models.meta_v1 import ObjectMeta
from lightkube.types import PatchType

from state.base import ResourceDefinition
from state.gateway import GatewayResourceInformation
from state.http_route import HTTPRouteResourceInformation

from .permission import map_k8s_auth_exception
from .resource_manager import ResourceManager

logger = logging.getLogger(__name__)

CUSTOM_RESOURCE_GROUP_NAME = "gateway.networking.k8s.io"
HTTP_ROUTE_RESOURCE_NAME = "HTTPRoute"
HTTP_ROUTE_PLURAL = "httproutes"


class HTTPRouteType(StrEnum):
    """StrEnum of possible http_route types.

    Attrs:
        HTTP: http.
        HTTPS: https.
    """

    HTTP = "http"
    HTTPS = "https"


@dataclasses.dataclass
class HTTPRouteResourceDefinition(ResourceDefinition):
    """A part of charm state with information required to manage gateway resource.

    It consists of 2 components:
        - HTTPRouteResourceInformation
        - GatewayResourceDefinition

    Attributes:
        application_name: The requirer application name.
        requirer_model_name: The name of the requirer model.
        gateway_name: The gateway resource's name.
        service_name: The configured gateway hostname.
        service_port: The configured gateway class.
        http_route_type: Type of the HTTP route, can be http or https.
        paths: The list of paths to be added to the HTTPRoute resource.
        filters: The list of filters to be applied to the HTTPRoute resource.
        matches: The list of matches for the HTTPRoute resource.
    """

    application_name: str
    requirer_model_name: str
    gateway_name: str
    service_name: str
    service_port: int
    http_route_type: HTTPRouteType
    redirect_https: bool
    paths: list[str]
    filters: list[dict]
    hostname: str | None

    def __init__(
        self,
        http_route_resource_information: HTTPRouteResourceInformation,
        gateway_resource_information: GatewayResourceInformation,
        http_route_type: HTTPRouteType,
        redirect_https: bool = False,
    ):
        """Create the state object with state components.

        Args:
            http_route_resource_information: HTTPRouteResourceInformation state component.
            gateway_resource_information: GatewayResourceInformation state component.
            http_route_type: Type of the HTTP route, can be http or https.
            redirect_https: Whether to redirect HTTP traffic to HTTPS.
        """
        super().__init__(http_route_resource_information, gateway_resource_information)
        self.http_route_type = http_route_type
        self.redirect_https = redirect_https

    @property
    def matches(self) -> list[dict[str, dict[str, str]]]:
        """Get the list of matches for the HTTPRoute resource.

        Returns:
            The list of matches.
        """
        match_list = []

        for path in self.paths:
            match_list.append(
                {
                    "path": {
                        "type": "PathPrefix",
                        "value": path,
                    }
                }
            )
        return match_list

    @property
    def listener_id(self) -> str:
        """Get the listener id for the HTTPRoute resource.

        The listener id is used to reference the corresponding listener in the parent Gateway resource.

        Returns:
            The listener id.
        """
        return f"{self.gateway_name}-{self.http_route_type}-listener"

    @property
    def http_route_resource_name(self) -> str:
        """Get the HTTPRoute resource name.

        Returns:
            The HTTPRoute resource name.
        """
        return f"{self.gateway_name}-{self.http_route_type}"

    @property
    def http_route_hostnames(self) -> list[str] | None:
        """Get the hostnames for the HTTPRoute resource.

        Returns:
            The list of hostnames or None if hostname is not set.
        """
        return None if self.hostname is None else [self.hostname]

    def http_route_resource_spec(self, namespace: str) -> dict[str, typing.Any]:
        """Generate a Gateway resource from a gateway resource definition.

        Args:
            namespace: The namespace where the gateway resource is located.

        Returns:
            A dictionary representing the gateway custom resource.
        """
        if self.redirect_https:
            return {
                "parentRefs": [
                    {
                        "name": self.gateway_name,
                        "namespace": namespace,
                        "sectionName": self.listener_id,
                    }
                ],
                "rules": [
                    {
                        "filters": [
                            {
                                "type": "RequestRedirect",
                                "requestRedirect": {"scheme": "https", "statusCode": 301},
                            }
                        ]
                    }
                ],
                "hostnames": self.http_route_hostnames,
            }

        return {
            "parentRefs": [
                {
                    "name": self.gateway_name,
                    "namespace": namespace,
                    "sectionName": self.listener_id,
                }
            ],
            "rules": [
                {
                    "matches": self.matches,
                    "filters": self.filters,
                    "backendRefs": [
                        {
                            "name": self.service_name,
                            "port": self.service_port,
                        }
                    ],
                }
            ],
            "hostnames": self.http_route_hostnames,
        }


class HTTPRouteResourceManager(ResourceManager[GenericNamespacedResource]):
    """HTTP route resource manager."""

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
    def _gen_resource(self, resource_definition: ResourceDefinition) -> GenericNamespacedResource:
        """Generate a Gateway resource from a gateway resource definition.

        Args:
            resource_definition: Part of charm state consisting of 2 components:
                - HTTPRouteResourceInformation
                - GatewayResourceDefinition

        Returns:
            A dictionary representing the gateway custom resource.
        """
        http_route_resource_definition = typing.cast(
            HTTPRouteResourceDefinition, resource_definition
        )

        http_route = self._http_route_generic_resource_class(
            apiVersion=f"{CUSTOM_RESOURCE_GROUP_NAME}/v1",
            kind=HTTP_ROUTE_RESOURCE_NAME,
            metadata=ObjectMeta(
                name=http_route_resource_definition.http_route_resource_name,
                labels=self._labels,
            ),
            spec=http_route_resource_definition.http_route_resource_spec(self._client.namespace),
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
