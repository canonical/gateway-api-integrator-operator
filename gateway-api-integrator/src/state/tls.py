# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator resource definition."""

from typing import Annotated

import ops
from charms.gateway_api_integrator.v0.gateway_route import valid_fqdn
from charms.tls_certificates_interface.v4.tls_certificates import TLSCertificatesRequiresV4
from pydantic import BeforeValidator, ValidationError, model_validator
from pydantic.dataclasses import dataclass

from .exception import CharmStateValidationBaseError

TLS_CERTIFICATES_INTEGRATION = "certificates"


class TlsIntegrationMissingError(CharmStateValidationBaseError):
    """Exception raised when certificates relation is missing."""


class HostnameMissingError(CharmStateValidationBaseError):
    """Exception raised when hostname not configured in enforce_https mode.

    Hostname is configured either via the gateway-route relation or by setting external-hostname.
    """


class TLSInformationInvalidError(CharmStateValidationBaseError):
    """Exception raised when TLS information is invalid."""


@dataclass(frozen=True)
class TLSInformation:
    """A component of charm state containing information about TLS.

    Attributes:
        secret_resource_name_prefix: Prefix of the secret resource name.
        tls_certs: A dict of hostname: certificate obtained from the relation.
        tls_keys: A dict of hostname: private_key stored in juju secrets.
    """

    secret_resource_name_prefix: str
    tls_certs: dict[Annotated[str, BeforeValidator(valid_fqdn)], str]
    tls_keys: dict[Annotated[str, BeforeValidator(valid_fqdn)], str]

    @model_validator(mode="after")
    def validate_tls_certs_and_tls_keys(self) -> "TLSInformation":
        """Validate tls_certs and tls_keys."""
        if len(self.tls_certs) != 1 or len(self.tls_keys) != 1:
            raise ValueError("Only 1 pair of cert/key is supported.")
        if set(self.tls_certs.keys()) != set(self.tls_keys.keys()):
            raise ValueError("parsed tls_certs and tls_keys must belong to the same hostname.")
        return self

    # The pydantic validation above ensures that there is exactly one hostname.
    @property
    def hostname(self) -> str:
        """Get the hostname for the TLS information."""
        return next(iter(self.tls_certs.keys()))

    @classmethod
    def from_charm(
        cls,
        charm: ops.CharmBase,
        hostname: str | None,
        certificates: TLSCertificatesRequiresV4,
    ) -> "TLSInformation":
        """Get TLS information from a charm instance.

        Args:
            charm: The gateway-api-integrator charm.
            hostname: The configured hostname.
            certificates: TLS certificates requirer library.

        Returns:
            TLSInformation: Information about configured TLS certs.
        """
        cls.validate(charm)
        if hostname is None:
            raise HostnameMissingError("Hostname must be configured to use TLS.")

        tls_certs = {}
        tls_keys = {}
        secret_resource_name_prefix = f"{charm.app.name}-secret"
        for cert in certificates.get_provider_certificates():
            if hostname == cert.certificate.common_name:
                chain = cert.chain
                if chain[0] != cert.certificate:
                    chain.reverse()
                tls_certs[hostname] = "\n\n".join([str(cert) for cert in chain])
                tls_keys[hostname] = str(certificates.private_key)
        try:
            return cls(
                secret_resource_name_prefix=secret_resource_name_prefix,
                tls_certs=tls_certs,
                tls_keys=tls_keys,
            )
        except ValidationError as exc:
            raise TLSInformationInvalidError("Invalid TLS information.") from exc

    @classmethod
    def validate(cls, charm: ops.CharmBase) -> None:
        """Validate the precondition to initialize this state component.

        Args:
            charm: The gateway-api-integrator charm.
            enforce_https: Whether to enforce HTTPS.

        Raises:
            HostnameMissingError: When hostname is not configured.
            TlsIntegrationMissingError: When integration is not ready.
        """
        tls_requirer_integration = charm.model.get_relation(TLS_CERTIFICATES_INTEGRATION)
        if (
            tls_requirer_integration is None
            or tls_requirer_integration.data.get(charm.app) is None
        ):
            raise TlsIntegrationMissingError("Certificates integration not ready.")
