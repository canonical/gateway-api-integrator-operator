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

from state.base import ResourceDefinition
from state.exception import CharmStateValidationBaseError
from state.tls import TLSInformation

from .permission import map_k8s_auth_exception
from .resource_manager import ResourceManager

logger = logging.getLogger(__name__)


class CertificateDataNotReadyError(CharmStateValidationBaseError):
    """Exception raised when certificates data is not set on the tls provider."""


@dataclasses.dataclass
class SecretResourceDefinition(ResourceDefinition):
    """A part of charm state with information required to manage secret resource.

    Attrs:
        hostname: The configured gateway hostname.
        secret_resource_name_prefix: Prefix of the secret resource name.
        certificate: TLS certificate.
        private_key: Password-ecrypted private key.
        password: Private key password.
    """

    hostname: str
    secret_resource_name_prefix: str
    certificate: str
    private_key: str
    password: str

    @classmethod
    def from_tls_information(
        cls, tls_information: TLSInformation, hostname: str
    ) -> "SecretResourceDefinition":
        """Get certificate information for a given hostname.

        Args:
            tls_information: TLSInformation state component.
            hostname: The requested hostname.

        Raises:
            CertificateDataNotReadyError: When the certificate data is not ready.

        Returns:
            SecretResourceDefinition: Information about the certificate.
        """
        if hostname not in tls_information.tls_certs.keys():
            raise CertificateDataNotReadyError("Certificate data missing or incomplete.")

        return SecretResourceDefinition(
            hostname=hostname,
            secret_resource_name_prefix=tls_information.secret_resource_name_prefix,
            certificate=tls_information.tls_certs[hostname],
            private_key=tls_information.tls_keys[hostname]["key"],
            password=tls_information.tls_keys[hostname]["password"],
        )


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


class TLSSecretResourceManager(ResourceManager[Secret]):
    """Kubernetes Ingress resource controller."""

    def __init__(self, labels: LabelSelector, client: Client) -> None:
        """Initialize the TLSSecretResourceManager.

        Args:
            labels: Label to be added to created resources.
            client: Initialized lightkube client.
        """
        self._client = client
        self._labels = labels

    @map_k8s_auth_exception
    def _gen_resource(self, resource_definition: ResourceDefinition) -> Secret:
        """Generate a Gateway resource from a gateway resource definition.

        Args:
            resource_definition: Part of charm state.

        Returns:
            A Secret resource object.
        """
        secret_resource_definition = typing.cast(SecretResourceDefinition, resource_definition)
        prefix = secret_resource_definition.secret_resource_name_prefix
        tls_secret_name = f"{prefix}-{secret_resource_definition.hostname}"

        secret = Secret(
            apiVersion="v1",
            kind="Secret",
            metadata=ObjectMeta(name=tls_secret_name, labels=self._labels),
            stringData={
                "tls.crt": secret_resource_definition.certificate,
                "tls.key": _get_decrypted_key(
                    secret_resource_definition.private_key,
                    secret_resource_definition.password,
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
