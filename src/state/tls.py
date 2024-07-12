# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator resource definition."""

import dataclasses

import ops
from charms.tls_certificates_interface.v3.tls_certificates import TLSCertificatesRequiresV3
from ops.jujuversion import JujuVersion

from tls_relation import get_hostname_from_cert

from .exception import CharmStateValidationBaseError

TLS_CERTIFICATES_INTEGRATION = "certificates"


class SecretNotSupportedError(CharmStateValidationBaseError):
    """Exception raised when the juju version does not support secrets."""


class TlsIntegrationMissingError(CharmStateValidationBaseError):
    """Exception raised when certificates relation is missing."""


@dataclasses.dataclass(frozen=True)
class TLSInformation:
    """A component of charm state containing information about TLS.

    Attrs:
        secret_resource_name_prefix: Prefix of the secret resource name.
        tls_certs: A dict of hostname: certificate obtained from the relation.
        tls_keys: A dict of hostname: private_key stored in juju secrets.
    """

    secret_resource_name_prefix: str
    tls_certs: dict[str, str]
    tls_keys: dict[str, dict[str, str]]

    @classmethod
    def from_charm(
        cls, charm: ops.CharmBase, certificates: TLSCertificatesRequiresV3
    ) -> "TLSInformation":
        """Get TLS information from a charm instance.

        Args:
            charm: The gateway-api-integrator charm.
            certificates: TLS certificates requirer library.

        Raises:
            TlsIntegrationMissingError: When integration is not ready.
            SecretNotSupportedError: When running with incompatible juju version.

        Returns:
            TLSInformation: Information about configured TLS certs.
        """
        if not JujuVersion.from_environ().has_secrets:
            raise SecretNotSupportedError(
                "The charm requires the 'secrets' feature to be supported (juju version >= 3.0.3)."
            )

        tls_requirer_integration = charm.model.get_relation(TLS_CERTIFICATES_INTEGRATION)
        if (
            tls_requirer_integration is None
            or tls_requirer_integration.data.get(charm.app) is None
        ):
            raise TlsIntegrationMissingError("Certificates integration not ready.")

        tls_certs = {}
        tls_keys = {}
        secret_resource_name_prefix = f"{charm.app.name}-secret"

        for cert in certificates.get_provider_certificates():
            hostname = get_hostname_from_cert(cert.certificate)
            tls_certs[hostname] = cert.certificate
            secret = charm.model.get_secret(label=f"private-key-{hostname}")
            tls_keys[hostname] = {
                "key": secret.get_content()["key"],
                "password": secret.get_content()["password"],
            }

        return cls(
            secret_resource_name_prefix=secret_resource_name_prefix,
            tls_certs=tls_certs,
            tls_keys=tls_keys,
        )
