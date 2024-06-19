# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""nginx-ingress-integrator k8s ingress controller."""


import logging
import time
import typing

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

from state.config import CharmConfig
from state.gateway import GatewayResourceDefinition
from state.secret import SecretResourceDefinition

from .resource_manager import ResourceManager, _map_k8s_auth_exception

logger = logging.getLogger(__name__)

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

    def __init__(self, labels: LabelSelector, client: Client) -> None:
        """Initialize the GatewayResourceManager.

        Args:
            labels: Label to be added to created resources.
            client: Initialized lightkube client.
        """
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
        gateway_classes = tuple(self._client.list(self._gateway_class_generic_resource))

        if not gateway_classes:
            logger.error("Cluster has no available gateway class.")
            raise CreateGatewayError("No gateway class available.")

        gateway_class_names = (
            gateway_class.metadata.name
            for gateway_class in gateway_classes
            if gateway_class.metadata
        )
        if configured_gateway_class not in gateway_class_names:
            logger.error(
                "Configured gateway class %s not present on the cluster.", configured_gateway_class
            )
            raise CreateGatewayError(f"Gateway class {configured_gateway_class} not found.")

        resource.spec["gatewayClassName"] = configured_gateway_class

    @_map_k8s_auth_exception
    def _gen_resource(self, definition: GatewayResourceDefinition, *args: typing.Any) -> dict:
        """Generate a Gateway resource from a gateway resource definition.

        Args:
            definition: The gateway resoucre definition to use.
            args: Additional arguments.

        Returns:
            A dictionary representing the gateway custom resource.

        Raises:
            CreateGatewayError: if the method is not called with the correct arguments.
        """
        if (
            len(args) != 2
            or not isinstance(args[0], CharmConfig)
            or not isinstance(args[1], SecretResourceDefinition)
        ):
            raise CreateGatewayError("_gen_resource called with the wrong parameters.")

        config: CharmConfig
        secret: SecretResourceDefinition
        config, secret = args
        tls_secret_name = f"{secret.secret_resource_name_prefix}-{config.external_hostname}"
        gateway = self._gateway_generic_resource(
            apiVersion="gateway.networking.k8s.io/v1",
            kind="Gateway",
            metadata=ObjectMeta(name=definition.gateway_name, labels=self._labels),
            spec={
                "listeners": [
                    {
                        "protocol": "HTTP",
                        "port": 80,
                        "name": f"{definition.gateway_name}-http-listener",
                        "hostname": config.external_hostname,
                        "allowedRoutes": {"namespaces": {"from": "All"}},
                    },
                    {
                        "protocol": "HTTPS",
                        "port": 443,
                        "name": f"{definition.gateway_name}-https-listener",
                        "hostname": config.external_hostname,
                        "allowedRoutes": {"namespaces": {"from": "All"}},
                        "tls": {"certificateRefs": [{"kind": "Secret", "name": tls_secret_name}]},
                    },
                ]
            },
        )

        self._set_gateway_class(configured_gateway_class=config.gateway_class, resource=gateway)
        logger.info("Generated gateway resource: %s", gateway)
        return gateway

    @_map_k8s_auth_exception
    def _create_resource(self, resource: GenericNamespacedResource) -> None:
        """Create a new gateway resource in the current namespace.

        Args:
            resource: The gateway resource object to create.
        """
        self._client.create(resource)

    @_map_k8s_auth_exception
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
            self._gateway_generic_resource,
            name,
            resource,
            patch_type=PatchType.APPLY,
            force=True,
        )

    @_map_k8s_auth_exception
    def _list_resource(self) -> typing.List[GenericNamespacedResource]:
        """List gateway resources in the current namespace based on a label selector.

        Returns:
            A list of matched gateway resources.
        """
        return list(self._client.list(res=self._gateway_generic_resource, labels=self._labels))

    @_map_k8s_auth_exception
    def _delete_resource(self, name: str) -> None:
        """Delete a gateway resource from the current namespace.

        Args:
            name: The name of the V1Ingress resource to delete.
        """
        self._client.delete(
            res=self._gateway_generic_resource,
            name=name,
        )

    def gateway_address(self, name: str) -> typing.Optional[str]:
        """Return the LB address of the gateway resource.

        Poll the address for 100 seconds.

        Args:
            name (str): name of the gateway resource.

        Returns:
            Optional[str]: The addresses assigned to the gateway object, or none.
        """
        deadline = time.time() + 60
        delay = 5
        gateway_address = None
        while time.time() < deadline:
            try:
                gateway = self._client.get(
                    self._gateway_generic_resource,
                    name=name,
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
            logger.info("Gateway address not ready, waiting for %s seconds before retrying", delay)
            time.sleep(delay)
        return gateway_address
