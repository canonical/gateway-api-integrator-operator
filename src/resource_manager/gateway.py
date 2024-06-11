# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""nginx-ingress-integrator k8s ingress controller."""


import logging
import time
from typing import List, Optional

from lightkube import Client
from lightkube.core.client import LabelSelector
from lightkube.core.exceptions import ApiError
from lightkube.generic_resource import (
    GenericNamespacedResource,
    create_global_resource,
    create_namespaced_resource,
)
from lightkube.models.meta_v1 import ObjectMeta
from lightkube.types import PatchType

from resource_definition import GatewayResourceDefinition

from .resource_manager import ResourceManager, _map_k8s_auth_exception

LOGGER = logging.getLogger(__name__)

CUSTOM_RESOURCE_GROUP_NAME = "gateway.networking.k8s.io"
GATEWAY_CLASS_RESOURCE_NAME = "GatewayClass"
GATEWAY_CLASS_PLURAL = "gatewayclasses"
GATEWAY_RESOURCE_NAME = "Gateway"
GATEWAY_PLURAL = "gateways"


class CreateGatewayError(Exception):
    """Represents an error when creating the gateway resource."""

    def __init__(self, msg: str):
        """Initialize a new instance of the CreateGatewayError exception.

        Args:
            msg: Explanation of the error.
        """
        self.msg = msg


class GatewayResourceManager(ResourceManager[GenericNamespacedResource]):
    """Kubernetes Ingress resource controller."""

    def __init__(self, namespace: str, labels: LabelSelector, client: Client) -> None:
        """Initialize the GatewayResourceManager.

        Args:
            namespace: Kubernetes namespace.
            labels: Label to be added to created resources.
            client: Initialized lightkube client.
        """
        self._ns = namespace
        self._client = client
        self._labels = labels
        self._gateway_class_generic_resource = create_global_resource(
            CUSTOM_RESOURCE_GROUP_NAME, "v1", GATEWAY_CLASS_RESOURCE_NAME, GATEWAY_CLASS_PLURAL
        )
        self._gateway_generic_resource = create_namespaced_resource(
            CUSTOM_RESOURCE_GROUP_NAME, "v1", GATEWAY_RESOURCE_NAME, GATEWAY_PLURAL
        )

    @property
    def _name(self) -> str:
        """Returns "gateway"."""
        return "gateway"

    @property
    def _namespace(self) -> str:
        """Returns the kubernetes namespace.

        Returns:
            The namespace.
        """
        return self._ns

    @property
    def _label_selector(self) -> str:
        """Return the label selector for resources managed by this controller.

        Return:
            The label selector.
        """
        return ",".join(f"{k}={v}" for k, v in self._labels.items())

    def _set_gateway_class(
        self, configured_gateway_class: str, resource: GenericNamespacedResource
    ) -> None:
        """Set the configured gateway class, otherwise the cluster's default gateway class.

        Args:
            configured_gateway_class: The desired gateway class name.
            resource: The Ingress resource object.

        Raises:
            CreateGatewayError: When there's no available gateway classes
        """
        gateway_classes = list(self._client.list(self._gateway_class_generic_resource))

        if not gateway_classes:
            LOGGER.error("Cluster has no available gateway class.")
            raise CreateGatewayError("No gateway class available.")

        gateway_class_names = [
            gateway_class.metadata.name
            for gateway_class in gateway_classes
            if gateway_class.metadata
        ]
        if configured_gateway_class not in gateway_class_names:
            LOGGER.error(
                "Configured gateway class %s not present on the cluster.", configured_gateway_class
            )
            raise CreateGatewayError(f"Gateway class {configured_gateway_class} not found.")

        resource.spec["gatewayClassName"] = configured_gateway_class

    @_map_k8s_auth_exception
    def _gen_resource_from_definition(self, definition: GatewayResourceDefinition) -> dict:
        """Generate a Gateway resource from a gateway resource definition.

        Args:
            definition: The gateway resoucre definition to use.

        Returns:
            A dictionary representing the gateway custom resource.
        """
        gateway = self._gateway_generic_resource(
            apiVersion="gateway.networking.k8s.io/v1",
            kind="Gateway",
            metadata=ObjectMeta(
                name=definition.gateway_name, namespace=self._namespace, labels=self._labels
            ),
            spec={
                "listeners": [
                    {
                        "protocol": "HTTP",
                        "port": 80,
                        "name": f"{definition.gateway_name}-http-listener",
                        "hostname": definition.config.external_hostname,
                        "allowedRoutes": {"namespaces": {"from": "All"}},
                    },
                ]
            },
        )

        self._set_gateway_class(
            configured_gateway_class=definition.config.gateway_class, resource=gateway
        )
        LOGGER.info("Generated gateway resource: %s", gateway)
        return gateway

    @_map_k8s_auth_exception
    def _create_resource(self, resource: GenericNamespacedResource) -> None:
        """Create a new gateway resource in a given namespace.

        Args:
            resource: The gateway resource object to create.
        """
        self._client.create(resource)

    @_map_k8s_auth_exception
    def _patch_resource(self, name: str, resource: GenericNamespacedResource) -> None:
        """Replace an existing gateway resource in a given namespace.

        Args:
            name: The name of the resource to patch.
            resource: The modified gateway resource object.
        """
        # Patch the resource with server-side apply
        # force=True is required here so that the charm keeps control of the resource
        self._client.patch(  # type: ignore[type-var]
            # mypy can't detect that this is ok for patching custom resources
            self._gateway_generic_resource,
            name,
            resource,
            patch_type=PatchType.APPLY,
            force=True,
        )

    @_map_k8s_auth_exception
    def _list_resource(self) -> List[GenericNamespacedResource]:
        """List gateway resources in a given namespace based on a label selector.

        Returns:
            A list of matched gateway resources.
        """
        return list(
            self._client.list(
                res=self._gateway_generic_resource, namespace=self._namespace, labels=self._labels
            )
        )

    @_map_k8s_auth_exception
    def _delete_resource(self, name: str) -> None:
        """Delete a gateway resource from a given namespace.

        Args:
            name: The name of the V1Ingress resource to delete.
        """
        self._client.delete(
            res=self._gateway_generic_resource, name=name, namespace=self._namespace
        )

    def gateway_address(self, name: str) -> Optional[str]:
        """Return the LB address of the gateway resource.

        Poll the address for 100 seconds.

        Args:
            name (str): _description_

        Returns:
            Optional[str]: _description_
        """
        deadline = time.time() + 60
        delay = 5
        gateway_address = None
        while time.time() < deadline:
            try:
                gateway = self._client.get(
                    self._gateway_generic_resource, name=name, namespace=self._namespace
                )
                gateway_addresses = [
                    addr["value"] for addr in gateway.status["addresses"]  # type: ignore
                ]
                if gateway_addresses:
                    gateway_address = ",".join(gateway_addresses)
            except (ApiError, AttributeError, TypeError, KeyError):
                pass
            if gateway_address:
                break
            LOGGER.info("Gateway address not ready, waiting for %s seconds before retrying", delay)
            time.sleep(delay)
        return gateway_address
