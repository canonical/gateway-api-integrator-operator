# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
# Since the relations invoked in the methods are taken from the charm,
# mypy guesses the relations might be None about all of them.
"""Gateway API TLS relation business logic."""
import secrets
import string
from typing import Dict, Union

from charms.tls_certificates_interface.v3.tls_certificates import (
    CertificateAvailableEvent,
    CertificateExpiringEvent,
    CertificateInvalidatedEvent,
    TLSCertificatesRequiresV3,
    generate_csr,
    generate_private_key,
)
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.x509.oid import NameOID
from ops.jujuversion import JujuVersion
from ops.model import Model, Relation, SecretNotFoundError

TLS_CERT = "certificates"


class TLSRelationService:
    """TLS Relation service class."""

    def __init__(self, model: Model) -> None:
        """Init method for the class.

        Args:
            model: The charm model used to get the relations and secrets.
        """
        self.charm_model = model
        self.charm_app = model.app

    def generate_password(self) -> str:
        """Generate a random 12 character password.

        Returns:
            str: Private key string.
        """
        chars = string.ascii_letters + string.digits
        return "".join(secrets.choice(chars) for _ in range(12))

    def update_relation_data_fields(self, relation_fields: dict, tls_relation: Relation) -> None:
        """Update a dict of items from the app relation databag.

        Args:
            relation_fields: items to update
            tls_relation: TLS certificates relation
        """
        for key, value in relation_fields.items():
            tls_relation.data[self.charm_app].update({key: value})

    def pop_relation_data_fields(
        self,
        relation_fields: list,
        tls_relation: Relation,
    ) -> None:
        """Pop a list of items from the app relation databag.

        Args:
            relation_fields: items to pop
            tls_relation: TLS certificates relation
        """
        for item in relation_fields:
            tls_relation.data[self.charm_app].pop(item)

    def get_relation_data_field(self, relation_field: str, tls_relation: Relation) -> str:
        """Get an item from the app relation databag.

        Args:
            relation_field: item to get
            tls_relation: TLS certificates relation

        Returns:
            The value from the field.

        Raises:
            KeyError: if the field is not found in the relation databag.
        """
        field_value = tls_relation.data[self.charm_app].get(relation_field)
        if not field_value:
            raise KeyError(f"{relation_field} field not found in {tls_relation.name}")

        return field_value

    def get_hostname_from_cert(self, certificate: str) -> str:
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

    # The charm will not have annotations to avoid circular imports.
    def certificate_relation_joined(  # type: ignore[no-untyped-def]
        self,
        hostname: str,
        certificates: TLSCertificatesRequiresV3,
        tls_integration: Relation,
    ) -> None:
        """Handle the TLS Certificate joined event.

        Args:
            hostname: Certificate's hostname.
            certificates: The certificate requirer library instance.
            tls_integration: The tls certificates integration.
        """
        private_key_dict = self._get_private_key(hostname)
        csr = generate_csr(
            private_key=private_key_dict["key"].encode(),
            private_key_password=private_key_dict["password"].encode(),
            subject=hostname,
            sans_dns=[hostname],
        )
        self.update_relation_data_fields({f"csr-{hostname}": csr.decode()}, tls_integration)
        certificates.request_certificate_creation(certificate_signing_request=csr)

    def certificate_relation_created(self, hostname: str, tls_integration: Relation) -> None:
        """Handle the TLS Certificate created event.

        Args:
            hostname: Certificate's hostname.
            tls_integration: The tls certificates integration.
        """
        private_key_password = self.generate_password().encode()
        private_key = generate_private_key(password=private_key_password)
        private_key_dict = {
            "password": private_key_password.decode(),
            "key": private_key.decode(),
        }
        if JujuVersion.from_environ().has_secrets:
            try:
                secret = self.charm_model.get_secret(label=f"private-key-{hostname}")
                secret.set_content(private_key_dict)
            except SecretNotFoundError:
                secret = self.charm_app.add_secret(
                    content=private_key_dict, label=f"private-key-{hostname}"
                )
                secret.grant(tls_integration)

    def certificate_relation_available(
        self, event: CertificateAvailableEvent, tls_integration: Relation
    ) -> None:
        """Handle the TLS Certificate available event.

        Args:
            event: The event that fires this method.
            tls_integration: The tls certificates integration.
        """
        hostname = self.get_hostname_from_cert(event.certificate)
        self.update_relation_data_fields(
            {
                f"certificate-{hostname}": event.certificate,
                f"ca-{hostname}": event.ca,
                f"chain-{hostname}": str(event.chain_as_pem()),
            },
            tls_integration,
        )

    def certificate_expiring(  # type: ignore[no-untyped-def]
        self,
        event: Union[CertificateExpiringEvent, CertificateInvalidatedEvent],
        certificates: TLSCertificatesRequiresV3,
        tls_integration: Relation,
    ) -> None:
        """Handle the TLS Certificate expiring event.

        Args:
            event: The event that fires this method.
            certificates: The certificate requirer library instance.
            tls_integration: The tls certificates integration.
        """
        hostname = self.get_hostname_from_cert(event.certificate)
        old_csr = self.get_relation_data_field(f"csr-{hostname}", tls_integration)
        private_key_dict = self._get_private_key(hostname)
        new_csr = generate_csr(
            private_key=private_key_dict["key"].encode(),
            private_key_password=private_key_dict["password"].encode(),
            subject=hostname,
            sans_dns=[hostname],
        )
        certificates.request_certificate_renewal(
            old_certificate_signing_request=old_csr.encode(),
            new_certificate_signing_request=new_csr,
        )
        self.update_relation_data_fields({f"csr-{hostname}": new_csr.decode()}, tls_integration)

    def _get_decrypted_key(self, private_key: str, password: str) -> str:
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

    def _get_private_key(self, hostname: str) -> Dict[str, str]:
        """Return the private key and its password from either juju secrets or the relation data.

        Args:
            hostname: The hostname of the private key we want to fetch.

        Returns:
            The encrypted private key.
        """
        private_key_dict = {}
        if JujuVersion.from_environ().has_secrets:
            secret = self.charm_model.get_secret(label=f"private-key-{hostname}")
            private_key_dict["key"] = secret.get_content()["key"]
            private_key_dict["password"] = secret.get_content()["password"]
        return private_key_dict
