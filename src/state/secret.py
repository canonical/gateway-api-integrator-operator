# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator secret resource definition."""

import dataclasses
import typing

import ops

from .tls import TLSInformation


@dataclasses.dataclass(frozen=True)
class SecretResourceDefinition:
    """_summary_.

    Raises:
        InvalidCharmConfigError: _description_

    Attrs:
        secret_resource_name (str):
        namespace (str):
        tls_certs (typing.Dict[str, str]):
        tls_keys (typing.Dict[str, str]):

    Returns:
        _type_: _description_
    """

    secret_resource_name_prefix: str
    namespace: str
    tls_certs: typing.Dict[str, str]
    tls_keys: typing.Dict[str, str]

    @classmethod
    def from_charm_and_tls_information(
        cls, charm: ops.CharmBase, tls_information: TLSInformation
    ) -> "SecretResourceDefinition":
        """Create a resource definition from charm instance.

        Args:
            charm (ops.CharmBase): _description_
            tls_information (TLSInformation) : _description_

        Returns:
            ResourceDefinition: _description_
        """
        namespace = charm.model.name
        secret_resource_name_prefix = f"{charm.app.name}-secret-"

        return cls(
            tls_certs=tls_information.tls_certs,
            tls_keys=tls_information.tls_keys,
            namespace=namespace,
            secret_resource_name_prefix=secret_resource_name_prefix,
        )
