# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""gateway-api-integrator secret resource manager."""

import dataclasses
import logging
import typing

from cryptography.hazmat.primitives import serialization
from lightkube import Client
from lightkube.core.client import LabelSelector
from lightkube.models.meta_v1 import ObjectMeta
from lightkube.resources.core_v1 import Secret
from lightkube.types import PatchType
from ops.model import Relation

from state.base import ResourceDefinition
from state.config import CharmConfig
from state.gateway import GatewayResourceInformation
from state.tls import TLSInformation

from .permission import map_k8s_auth_exception
from .resource_manager import ResourceManager

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class SecretResourceDefinition(ResourceDefinition):
    """A part of charm state with information required to manage secret resource.

    It consistS of 3 components:
        - SecretResourceInfomation
        - CharmConfig
        - TLSInformation

    Attrs:
        external_hostname: The configured gateway hostname.
        tls_requirer_integration: The integration instance with a TLS provider.
        tls_certs: A dict of hostname: certificate obtained from the relation.
        tls_keys: A dict of hostname: private_key stored in juju secrets.
        secret_resource_name_prefix: Prefix of the secret resource name.
    """

    external_hostname: str
    tls_requirer_integration: Relation
    tls_certs: dict[str, str]
    tls_keys: dict[str, dict[str, str]]
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


def _get_decrypted_key(private_key: str, password: str) -> str:
    """Decrypted the provided private key using the provided password.

    Args:
        private_key: The encrypted private key.
        password: The password to decrypt the private key.

    Returns:
        The decrypted private key.
    """
    decrypted_key = serialization.load_pem_private_key(
        private_key.encode(), password=password.encode()
    )

    # There are multiple representation PKCS8 is the default supported by nginx controller
    return decrypted_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


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

    @map_k8s_auth_exception
    def _gen_resource(self, state: ResourceDefinition) -> Secret:
        """Generate a Gateway resource from a gateway resource definition.

        Args:
            state: Part of charm state.

        Returns:
            A Secret resource object.
        """
        secret_state = typing.cast(SecretResourceDefinition, state)

        tls_secret_name = (
            f"{secret_state.secret_resource_name_prefix}-{secret_state.external_hostname}"
        )

        secret = Secret(
            apiVersion="v1",
            kind="Secret",
            metadata=ObjectMeta(name=tls_secret_name, labels=self._labels),
            stringData={
                "tls.crt": secret_state.tls_certs[secret_state.external_hostname],
                "tls.key": _get_decrypted_key(
                    secret_state.tls_keys[secret_state.external_hostname]["key"],
                    secret_state.tls_keys[secret_state.external_hostname]["password"],
                ),
            },
            type="kubernetes.io/tls",
        )

        return secret

    @map_k8s_auth_exception
    def _create_resource(self, resource: Secret) -> None:
        """Create a new secret resource in a given namespace.

        Args:
            resource: The secret resource object to create.
        """
        self._client.create(resource)

    @map_k8s_auth_exception
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

    @map_k8s_auth_exception
    def _list_resource(self) -> typing.List[Secret]:
        """List secret resources in a given namespace based on a label selector.

        Returns:
            A list of matched secret resources.
        """
        return list(self._client.list(res=Secret, labels=self._labels))

    @map_k8s_auth_exception
    def _delete_resource(self, name: str) -> None:
        """Delete a secret resource from a given namespace.

        Args:
            name: The name of the secret resource to delete.
        """
        self._client.delete(res=Secret, name=name)
