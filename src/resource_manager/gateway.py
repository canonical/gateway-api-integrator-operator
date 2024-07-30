# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""Gateway resource manager."""

import dataclasses
import logging
import time
import typing

from lightkube import Client
from lightkube.core.client import LabelSelector
from lightkube.generic_resource import GenericNamespacedResource, create_namespaced_resource
from lightkube.models.meta_v1 import ObjectMeta
from lightkube.types import PatchType

from state.base import ResourceDefinition
from state.config import CharmConfig
from state.gateway import GatewayResourceInformation
from state.tls import TLSInformation

from .permission import map_k8s_auth_exception
from .resource_manager import ResourceManager

logger = logging.getLogger(__name__)

CUSTOM_RESOURCE_GROUP_NAME = "gateway.networking.k8s.io"
GATEWAY_RESOURCE_NAME = "Gateway"
GATEWAY_PLURAL = "gateways"


@dataclasses.dataclass
class GatewayResourceDefinition(ResourceDefinition):
    """A part of charm state with information required to manage gateway resource.

    It consists of 3 components:
        - GatewayResourceInformation
        - CharmConfig
        - TLSInformation

    Attributes:
        gateway_name: The gateway resource's name
        external_hostname: The configured gateway hostname.
        gateway_class_name: The configured gateway class.
        secret_resource_name_prefix: Prefix of the secret resource name.
    """

    gateway_name: str
    external_hostname: str
    gateway_class_name: str
    secret_resource_name_prefix: str

    def __init__(
        self,
        gateway_resource_information: GatewayResourceInformation,
        charm_config: CharmConfig,
        tls_information: TLSInformation,
    ):
        """Create the state object with state components.

        Args:
            gateway_resource_information: GatewayResourceInformation state component.
            charm_config: CharmConfig state component.
            tls_information: TLSInformation state component.
        """
        super().__init__(gateway_resource_information, charm_config, tls_information)


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
    def _label_selector(self) -> str:
        """Return the label selector for resources managed by this controller.

        Return:
            The label selector.
        """
        return ",".join(f"{k}={v}" for k, v in self._labels.items())

    @map_k8s_auth_exception
    def _gen_resource(self, resource_definition: ResourceDefinition) -> dict:
        """Generate a Gateway resource from a gateway resource definition.

        Args:
            resource_definition: The data necessary to create the gateway resource.

        Returns:
            A dictionary representing the gateway custom resource.
        """
        gateway_resource_definition = typing.cast(GatewayResourceDefinition, resource_definition)
        prefix = gateway_resource_definition.secret_resource_name_prefix
        tls_secret_name = f"{prefix}-{gateway_resource_definition.external_hostname}"
        gateway = self._gateway_generic_resource(
            apiVersion="gateway.networking.k8s.io/v1",
            kind="Gateway",
            metadata=ObjectMeta(
                name=gateway_resource_definition.gateway_name, labels=self._labels
            ),
            spec={
                "gatewayClassName": gateway_resource_definition.gateway_class_name,
                "listeners": [
                    {
                        "protocol": "HTTP",
                        "port": 80,
                        "name": f"{gateway_resource_definition.gateway_name}-http-listener",
                        "hostname": gateway_resource_definition.external_hostname,
                        "allowedRoutes": {"namespaces": {"from": "All"}},
                    },
                    {
                        "protocol": "HTTPS",
                        "port": 443,
                        "name": f"{gateway_resource_definition.gateway_name}-https-listener",
                        "hostname": gateway_resource_definition.external_hostname,
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

        Poll the address for 60 seconds.

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
            except (AttributeError, TypeError, KeyError):
                logger.exception("Error retrieving the gateway address.")
            if gateway_address:
                break
            logger.info("Gateway address not ready, waiting for %s seconds before retrying", delay)
            time.sleep(delay)
        return gateway_address
