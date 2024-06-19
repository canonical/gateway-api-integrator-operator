# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""gateway-api-integrator secret resource manager."""


import logging
import typing

from lightkube import Client
from lightkube.core.client import LabelSelector
from lightkube.models.meta_v1 import ObjectMeta
from lightkube.resources.core_v1 import Secret
from lightkube.types import PatchType

from state.config import CharmConfig
from state.secret import SecretResourceDefinition
from state.tls import TLSInformation

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
            labels: Label to be added to created resources.
            client: Initialized lightkube client.
        """
        self._client = client
        self._labels = labels

    @property
    def _name(self) -> str:
        """Returns "gateway"."""
        return "gateway"

    @_map_k8s_auth_exception
    def _gen_resource(self, definition: SecretResourceDefinition, *args: typing.Any) -> Secret:
        """Generate a Gateway resource from a gateway resource definition.

        Args:
            definition: The gateway resoucre definition to use.
            args: Additional arguments.

        Returns:
            A dictionary representing the gateway custom resource.

        Raises:
            CreateSecretError: if the method is not called with the correct arguments.
        """
        if (
            len(args) != 2
            or not isinstance(args[0], CharmConfig)
            or not isinstance(args[1], TLSInformation)
        ):
            raise CreateSecretError("_gen_resource called with the wrong parameters.")

        config: CharmConfig
        tls_information: TLSInformation
        config, tls_information = args
        tls_secret_name = f"{definition.secret_resource_name_prefix}-{config.external_hostname}"

        secret = Secret(
            apiVersion="v1",
            kind="Secret",
            metadata=ObjectMeta(name=tls_secret_name, labels=self._labels),
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
    def _patch_resource(self, name: str, resource: Secret) -> None:
        """Replace an existing gateway resource in the current namespace.

        Args:
            name: The name of the resource to patch.
            resource: The modified gateway resource object.
        """
        # Patch the resource with server-side apply
        # force=True is required here so that the charm keeps control of the resource
        self._client.patch(  # type: ignore[type-var]
            # mypy can't detect that this is ok for patching custom resources
            Secret,
            name,
            resource,
            patch_type=PatchType.APPLY,
            force=True,
        )

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
