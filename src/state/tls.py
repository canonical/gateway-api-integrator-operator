# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator resource definition."""

import dataclasses

import ops
from charms.tls_certificates_interface.v4.tls_certificates import TLSCertificatesRequiresV4

from .exception import CharmStateValidationBaseError

TLS_CERTIFICATES_INTEGRATION = "certificates"


class TlsIntegrationMissingError(CharmStateValidationBaseError):
    """Exception raised when certificates relation is missing."""


@dataclasses.dataclass(frozen=True)
class TLSInformation:
    """A component of charm state containing information about TLS.

    Attributes:
        secret_resource_name_prefix: Prefix of the secret resource name.
        tls_certs: A dict of hostname: certificate obtained from the relation.
        tls_keys: A dict of hostname: private_key stored in juju secrets.
    """

    secret_resource_name_prefix: str
    tls_certs: dict[str, str]
    tls_keys: dict[str, dict[str, str]]

    @classmethod
    def from_charm(
        cls, charm: ops.CharmBase, certificates: TLSCertificatesRequiresV4
    ) -> "TLSInformation":
        """Get TLS information from a charm instance.

        Args:
            charm: The gateway-api-integrator charm.
            certificates: TLS certificates requirer library.

        Returns:
            TLSInformation: Information about configured TLS certs.
        """
        cls.validate(charm)

        tls_certs = {}
        tls_keys = {}
        secret_resource_name_prefix = f"{charm.app.name}-secret"

        for provider_certificate in certificates.get_provider_certificates():
            certificate = provider_certificate.certificate
            hostname = certificate.common_name
            chain = [c.raw for c in provider_certificate.chain]
            if chain[0] != certificate.raw:
                chain.reverse()
            tls_certs[hostname] = "\n\n".join(chain)
            if certificates.private_key:
                tls_keys[hostname] = {
                    "key": certificates.private_key.raw,
                    "password": "",  # v4 doesn't use password for private keys
                }

        return cls(
            secret_resource_name_prefix=secret_resource_name_prefix,
            tls_certs=tls_certs,
            tls_keys=tls_keys,
        )

    @classmethod
    def validate(cls, charm: ops.CharmBase) -> None:
        """Validate the precondition to initialize this state component.

        Args:
            charm: The gateway-api-integrator charm.

        Raises:
            TlsIntegrationMissingError: When integration is not ready.
        """
        tls_requirer_integration = charm.model.get_relation(TLS_CERTIFICATES_INTEGRATION)
        if (
            tls_requirer_integration is None
            or tls_requirer_integration.data.get(charm.app) is None
        ):
            raise TlsIntegrationMissingError("Certificates integration not ready.")
