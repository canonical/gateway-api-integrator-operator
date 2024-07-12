# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
# Since the relations invoked in the methods are taken from the charm,
# mypy guesses the relations might be None about all of them.
"""Gateway API TLS relation business logic."""
import secrets
import string
import typing

from charms.tls_certificates_interface.v3.tls_certificates import (
    CertificateExpiringEvent,
    CertificateInvalidatedEvent,
    ProviderCertificate,
    TLSCertificatesRequiresV3,
    generate_csr,
    generate_private_key,
)
from cryptography import x509
from cryptography.x509.oid import NameOID
from ops.model import Relation, SecretNotFoundError

TLS_CERT = "certificates"


def get_hostname_from_cert(certificate: str) -> str:
    """Get the hostname from a certificate subject name.

    Args:
        certificate: The certificate in PEM format.

    Returns:
        The hostname the certificate is issue to.
    """
    decoded_cert = x509.load_pem_x509_certificate(certificate.encode())

    common_name_attribute = decoded_cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
    if not common_name_attribute:
        return ""

    return str(common_name_attribute[0].value)


class TLSRelationService:
    """TLS Relation service class."""

    def __init__(self, certificates: TLSCertificatesRequiresV3) -> None:
        """Init method for the class.

        Args:
            certificates: The TLS certificates requirer library.
        """
        self.certificates = certificates
        self.model = self.certificates.model
        self.application = self.model.app
        self.integration_name = self.certificates.relationship_name

    def generate_password(self) -> str:
        """Generate a random 12 character password.

        Returns:
            str: Private key string.
        """
        chars = string.ascii_letters + string.digits
        return "".join(secrets.choice(chars) for _ in range(12))

    def certificate_relation_joined(self, hostname: str) -> None:
        """Handle the TLS Certificate joined event.

        Args:
            hostname: Certificate's hostname.
        """
        private_key, password = self._get_private_key(hostname)
        csr = generate_csr(
            private_key=private_key.encode(),
            private_key_password=password.encode(),
            subject=hostname,
            sans_dns=[hostname],
        )
        self.certificates.request_certificate_creation(certificate_signing_request=csr)

    def certificate_relation_created(self, hostname: str) -> None:
        """Handle the TLS Certificate created event.

        Args:
            hostname: Certificate's hostname.
        """
        # At this point, TLSInformation state component should already be initialized
        tls_integration = typing.cast(Relation, self.model.get_relation(self.integration_name))

        private_key_password = self.generate_password().encode()
        private_key = generate_private_key(password=private_key_password)
        private_key_dict = {
            "password": private_key_password.decode(),
            "key": private_key.decode(),
        }
        try:
            secret = self.model.get_secret(label=f"private-key-{hostname}")
            secret.set_content(private_key_dict)
        except SecretNotFoundError:
            secret = self.application.add_secret(
                content=private_key_dict, label=f"private-key-{hostname}"
            )
            secret.grant(tls_integration)

    def certificate_expiring(
        self,
        event: CertificateExpiringEvent,
    ) -> None:
        """Handle the TLS Certificate expiring event.

        Args:
            event: The event that fires this method.
        """
        if expiring_cert := self._get_cert(event.certificate):
            hostname = get_hostname_from_cert(expiring_cert.certificate)
            old_csr = expiring_cert.csr
            private_key, password = self._get_private_key(hostname)
            new_csr = generate_csr(
                private_key=private_key.encode(),
                private_key_password=password.encode(),
                subject=hostname,
                sans_dns=[hostname],
            )
            self.certificates.request_certificate_renewal(
                old_certificate_signing_request=old_csr.encode(),
                new_certificate_signing_request=new_csr,
            )

    def certificate_invalidated(
        self,
        event: CertificateInvalidatedEvent,
    ) -> None:
        """Handle TLS Certificate revocation.

        Args:
            event: The event that fires this method.
        """
        if invalidated_cert := self._get_cert(event.certificate):
            hostname = get_hostname_from_cert(invalidated_cert.certificate)
            secret = self.model.get_secret(label=f"private-key-{hostname}")
            secret.remove_all_revisions()
            self.certificates.request_certificate_revocation(
                certificate_signing_request=invalidated_cert.csr.encode()
            )

    def _get_private_key(self, hostname: str) -> tuple[str, str]:
        """Return the private key and its password from either juju secrets or the relation data.

        Args:
            hostname: The hostname of the private key we want to fetch.

        Returns:
            The encrypted private key.
        """
        secret = self.model.get_secret(label=f"private-key-{hostname}")
        private_key = secret.get_content()["key"]
        password = secret.get_content()["password"]
        return (private_key, password)

    def _get_cert(self, certificate: str) -> typing.Optional[ProviderCertificate]:
        """Get a cert from the provider's integration data that matches 'certificate'.

        Args:
            certificate: the certificate to match with provider certificates

        Returns:
            typing.Optional[ProviderCertificate]: ProviderCertificate if exists, else None.
        """
        provider_certificates = self.certificates.get_provider_certificates()
        matching_certs = [cert for cert in provider_certificates if cert == certificate]
        return matching_certs[0] if matching_certs else None
