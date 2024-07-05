# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""Gateway resource manager."""


import logging
import time
import typing

from lightkube import Client
from lightkube.core.client import LabelSelector
from lightkube.core.exceptions import ApiError
from lightkube.generic_resource import GenericNamespacedResource, create_namespaced_resource
from lightkube.models.meta_v1 import ObjectMeta
from lightkube.types import PatchType

from state.base import State

from .permission import map_k8s_auth_exception
from .resource_manager import ResourceManager

logger = logging.getLogger(__name__)

CUSTOM_RESOURCE_GROUP_NAME = "gateway.networking.k8s.io"
GATEWAY_RESOURCE_NAME = "Gateway"
GATEWAY_PLURAL = "gateways"


class CreateGatewayError(Exception):
    """Represents an error when creating the gateway resource."""


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
        self._gateway_generic_resource = create_namespaced_resource(
            CUSTOM_RESOURCE_GROUP_NAME, "v1", GATEWAY_RESOURCE_NAME, GATEWAY_PLURAL
        )

    @property
    def _name(self) -> str:
        """Returns "gateway"."""
        return "gateway"

    @property
    def _label_selector(self) -> str:
        """Return the label selector for resources managed by this controller.

        Return:
            The label selector.
        """
        return ",".join(f"{k}={v}" for k, v in self._labels.items())

    @map_k8s_auth_exception
    def _gen_resource(self, state: State) -> dict:
        """Generate a Gateway resource from a gateway resource definition.

        Args:
            state: Fragment of charm state consists of 3 components:
                - GatewayResourceManager
                - CharmConfig
                - SecretResourceManager

        Returns:
            A dictionary representing the gateway custom resource.
        """
        tls_secret_name = f"{state.secret_resource_name_prefix}-{state.external_hostname}"
        gateway = self._gateway_generic_resource(
            apiVersion="gateway.networking.k8s.io/v1",
            kind="Gateway",
            metadata=ObjectMeta(name=state.gateway_name, labels=self._labels),
            spec={
                "gatewayClassName": state.gateway_class,
                "listeners": [
                    {
                        "protocol": "HTTP",
                        "port": 80,
                        "name": f"{state.gateway_name}-http-listener",
                        "hostname": state.external_hostname,
                        "allowedRoutes": {"namespaces": {"from": "All"}},
                    },
                    {
                        "protocol": "HTTPS",
                        "port": 443,
                        "name": f"{state.gateway_name}-https-listener",
                        "hostname": state.external_hostname,
                        "allowedRoutes": {"namespaces": {"from": "All"}},
                        "tls": {"certificateRefs": [{"kind": "Secret", "name": tls_secret_name}]},
                    },
                ],
            },
        )
        return gateway

    @map_k8s_auth_exception
    def _create_resource(self, resource: GenericNamespacedResource) -> None:
        """Create a new gateway resource in the current namespace.

        Args:
            resource: The gateway resource object to create.
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
            self._gateway_generic_resource,
            name,
            resource,
            patch_type=PatchType.APPLY,
            force=True,
        )

    @map_k8s_auth_exception
    def _list_resource(self) -> typing.List[GenericNamespacedResource]:
        """List gateway resources in the current namespace based on a label selector.

        Returns:
            A list of matched gateway resources.
        """
        return list(self._client.list(res=self._gateway_generic_resource, labels=self._labels))

    @map_k8s_auth_exception
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
            name: name of the gateway resource.

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
