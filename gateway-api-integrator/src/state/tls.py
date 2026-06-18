# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator resource definition."""

from typing import Self

import ops
from charmlibs.interfaces.tls_certificates import TLSCertificatesRequiresV4
from pydantic import ValidationError, model_validator
from pydantic.dataclasses import dataclass
import logging
logger = logging.getLogger(__name__)
from .exception import CharmStateValidationBaseError

TLS_CERTIFICATES_INTEGRATION = "certificates"


class TlsIntegrationMissingError(CharmStateValidationBaseError):
    """Exception raised when certificates relation is missing."""


class TLSInformationInvalidError(CharmStateValidationBaseError):
    """Exception raised when TLS information is invalid."""


class TLSInformationNotReadyError(CharmStateValidationBaseError):
    """Exception raised when requested TLS certificates are not yet available."""


@dataclass(frozen=True)
class TLSInformation:
    """A component of charm state containing information about TLS.

    Attributes:
        secret_resource_name_prefix: Prefix of the secret resource name.
        tls_certs: A dict of hostname: certificate obtained from the relation.
        tls_keys: A dict of hostname: private_key stored in juju secrets.
    """

    secret_resource_name_prefix: str
    tls_certs: dict[str, str]
    tls_keys: dict[str, str]

    @model_validator(mode="after")
    def validate_tls_certs_and_tls_keys(self) -> Self:
        """Validate tls_certs and tls_keys."""
        if len(self.tls_certs) < 1 or len(self.tls_keys) < 1:
            raise ValueError("At least 1 pair of cert/key is required.")
        if set(self.tls_certs.keys()) != set(self.tls_keys.keys()):
            raise ValueError("parsed tls_certs and tls_keys must belong to the same hostnames.")
        return self

    @property
    def hostnames(self) -> list[str]:
        """Get the list of hostnames for the TLS information."""
        return sorted(self.tls_certs.keys())

    @classmethod
    def from_charm(
        cls,
        charm: ops.CharmBase,
        hostnames: set[str],
        certificates: TLSCertificatesRequiresV4,
        gateway_address: str | None = None,
    ) -> Self | None:
        """Get TLS information from a charm instance.

        Args:
            charm: The gateway-api-integrator charm.
            hostnames: Hostnames for which TLS certs are expected.
            certificates: TLS certificates requirer library.
            gateway_address: The gateway LB address. When provided, the certificate
                issued for this IP (IP SAN) is consumed in addition to any
                per-hostname certificates.

        Returns:
            TLSInformation if certificates are available, None otherwise.
        """
        cls.validate(charm)

        targets = set(hostnames)
        if gateway_address:
            targets.add(gateway_address)

        if not targets:
            return None
        logger.info(f"Targets: {', '.join(sorted(targets))}")
        tls_certs: dict[str, str] = {}
        tls_keys: dict[str, str] = {}
        secret_resource_name_prefix = f"{charm.app.name}-secret"
        for cert in certificates.get_provider_certificates():
            logger.info(f"cert: {cert.certificate}")
            cn = cert.certificate.common_name
            if cn in targets:
                chain = cert.chain
                if chain[0] != cert.certificate:
                    chain.reverse()
                tls_certs[cn] = "\n\n".join([str(c) for c in chain])
                tls_keys[cn] = str(certificates.private_key)

        missing_targets = targets - set(tls_certs.keys())
        if missing_targets:
            missing_targets_str = ", ".join(sorted(missing_targets))
            raise TLSInformationNotReadyError(
                f"Waiting for TLS certificates to be issued for: {missing_targets_str}."
            )

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
            TlsIntegrationMissingError: When integration is not ready.
        """
        tls_requirer_integration = charm.model.get_relation(TLS_CERTIFICATES_INTEGRATION)
        if (
            tls_requirer_integration is None
            or tls_requirer_integration.data.get(charm.app) is None
        ):
            raise TlsIntegrationMissingError("Certificates integration not ready.")
