# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""gateway-api-integrator secret resource manager."""


import logging
from typing import List

from lightkube import Client
from lightkube.core.client import LabelSelector
from lightkube.models.core_v1 import Secret
from lightkube.models.meta_v1 import ObjectMeta

from state.secret import SecretResourceDefinition

from .resource_manager import ResourceManager, _map_k8s_auth_exception

LOGGER = logging.getLogger(__name__)


class CreateSecretError(Exception):
    """Represents an error when creating the secret resource."""

    def __init__(self, msg: str):
        """Initialize a new instance of the CreateSecretError exception.

        Args:
            msg: Explanation of the error.
        """
        self.msg = msg


class GatewayResourceManager(ResourceManager[Secret]):
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

    @_map_k8s_auth_exception
    def _gen_resource_from_definition(self, definition: SecretResourceDefinition) -> Secret:
        """Generate a Gateway resource from a gateway resource definition.

        Args:
            definition: The gateway resoucre definition to use.

        Returns:
            A dictionary representing the gateway custom resource.
        """
        secret = Secret(
            apiVersion="gateway.networking.k8s.io/v1",
            kind="Gateway",
            metadata=ObjectMeta(
                name=definition.name, namespace=self._namespace, labels=self._labels
            ),
            stringData={
                "tls.crt": definition.tls_certs["hostname"],
                "tls.key": definition.tls_keys["hostname"],
            },
            type="kubernetes.io/tls",
        )

        LOGGER.info("Generated secret resource: %s", secret)
        return secret

    @_map_k8s_auth_exception
    def _create_resource(self, resource: Secret) -> None:
        """Create a new secret resource in a given namespace.

        Args:
            resource: The secret resource object to create.
        """
        self._client.create(resource)

    @_map_k8s_auth_exception
    def _patch_resource(self, resource: Secret) -> None:
        """Replace an existing secret resource in a given namespace.

        Args:
            resource: The modified secret resource object.
        """
        self._client.replace(resource)

    @_map_k8s_auth_exception
    def _list_resource(self) -> List[Secret]:
        """List secret resources in a given namespace based on a label selector.

        Returns:
            A list of matched secret resources.
        """
        return list(self._client.list(res=Secret, namespace=self._namespace, labels=self._labels))

    @_map_k8s_auth_exception
    def _delete_resource(self, name: str) -> None:
        """Delete a secret resource from a given namespace.

        Args:
            name: The name of the secret resource to delete.
        """
        self._client.delete(res=Secret, name=name, namespace=self._namespace)
