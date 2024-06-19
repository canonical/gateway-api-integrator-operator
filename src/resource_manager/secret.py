# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""gateway-api-integrator secret resource manager."""


import logging
import typing

from lightkube import Client
from lightkube.core.client import LabelSelector
from lightkube.models.core_v1 import Secret
from lightkube.models.meta_v1 import ObjectMeta

import state
import state.config
import state.secret
import state.tls

from .resource_manager import ResourceManager, _map_k8s_auth_exception

logger = logging.getLogger(__name__)


class CreateSecretError(Exception):
    """Represents an error when creating the secret resource."""

    def __init__(self, msg: str):
        """Initialize a new instance of the CreateSecretError exception.

        Args:
            msg: Explanation of the error.
        """
        self.msg = msg


class SecretResourceManager(ResourceManager[Secret]):
    """Kubernetes Ingress resource controller."""

    def __init__(self, labels: LabelSelector, client: Client) -> None:
        """Initialize the SecretResourceManager.

        Args:
            namespace: Kubernetes namespace.
            labels: Label to be added to created resources.
            client: Initialized lightkube client.
        """
        self._client = client
        self._labels = labels

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

    @_map_k8s_auth_exception
    def _gen_resource(
        self, definition: state.secret.SecretResourceDefinition, *args: typing.Any
    ) -> dict:
        """Generate a Gateway resource from a gateway resource definition.

        Args:
            definition: The gateway resoucre definition to use.

        Returns:
            A dictionary representing the gateway custom resource.
        """
        if (
            len(args) != 2
            or not isinstance(args[0], state.config.CharmConfig)
            or not isinstance(args[1], state.tls.TLSInformation)
        ):
            raise CreateSecretError("_gen_resource called with the wrong parameters.")

        config: state.config.CharmConfig
        tls_information: state.tls.TLSInformation
        config, tls_information = args
        secret = Secret(
            apiVersion="gateway.networking.k8s.io/v1",
            kind="Gateway",
            metadata=ObjectMeta(name=definition.name, labels=self._labels),
            stringData={
                "tls.crt": tls_information.tls_certs[config.external_hostname],
                "tls.key": tls_information.tls_keys[config.external_hostname],
            },
            type="kubernetes.io/tls",
        )

        logger.info("Generated secret resource: %s", secret)
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
    def _list_resource(self) -> typing.List[Secret]:
        """List secret resources in a given namespace based on a label selector.

        Returns:
            A list of matched secret resources.
        """
        return list(self._client.list(res=Secret, labels=self._labels))

    @_map_k8s_auth_exception
    def _delete_resource(self, name: str) -> None:
        """Delete a secret resource from a given namespace.

        Args:
            name: The name of the secret resource to delete.
        """
        self._client.delete(res=Secret, name=name)
