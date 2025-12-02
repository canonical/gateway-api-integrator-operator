# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
# Since the relations invoked in the methods are taken from the charm,
# mypy guesses the relations might be None about all of them.
"""Gateway API TLS relation business logic."""
import logging
import secrets
import string
import typing

from charms.tls_certificates_interface.v4.tls_certificates import (
    ProviderCertificate,
    TLSCertificatesRequiresV4,
)
from cryptography import x509
from cryptography.x509.oid import NameOID
from ops.model import Model

from lib.charms.tls_certificates_interface.v4.tls_certificates import Certificate

TLS_CERT = "certificates"
logger = logging.getLogger()


class InvalidCertificateError(Exception):
    """Exception raised when certificates is invalid."""


class TLSRelationService:
    """TLS Relation service class."""

    def __init__(self, model: Model, certificates: TLSCertificatesRequiresV4) -> None:
        """Init method for the class.

        Args:
            model: The charm's current model.
            certificates: The TLS certificates requirer library.
        """
        self.certificates = certificates
        self.model = model
        self.application = self.model.app
        self.integration_name = self.certificates.relationship_name

    def certificate_expiring(
        self,
        certificate: str,
    ) -> None:
        """Handle the TLS Certificate expiring event.

        Args:
            certificate: The certificate that is expiring.
        """
        if expiring_cert := self._get_cert(certificate):
            # In v4, certificate renewal is handled automatically by the library
            # when the certificate's expiry secret expires
            self.certificates.renew_certificate(expiring_cert)

    def certificate_invalidated(self) -> None:
        """Handle TLS Certificate revocation."""
        # In v4, certificate invalidation and revocation is handled by the library
        # Certificates are automatically removed when invalidated
        pass

    def revoke_all_certificates(self) -> None:
        """Revoke all provider certificates and remove all revisions in juju secret."""
        # In v4, we need to regenerate the private key which will trigger new certificate requests
        # The library manages certificate lifecycle internally
        try:
            self.certificates.regenerate_private_key()
        except Exception as e:
            logger.warning("Failed to regenerate private key: %s", e)

    def _get_cert(self, certificate: str) -> typing.Optional[ProviderCertificate]:
        """Get a cert from the provider's integration data that matches 'certificate'.

        Args:
            certificate: the certificate to match with provider certificates

        Returns:
            typing.Optional[ProviderCertificate]: ProviderCertificate if exists, else None.
        """
        provider_certificates = self.certificates.get_provider_certificates()
        matching_certs = [
            cert for cert in provider_certificates if str(cert.certificate) == certificate
        ]
        return matching_certs[0] if matching_certs else None
