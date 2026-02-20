# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator resource definition."""

import dataclasses

import ops
from charms.gateway_api_integrator.v0.gateway_route import GatewayRouteProvider
from charms.tls_certificates_interface.v4.tls_certificates import TLSCertificatesRequiresV4

from state.config import CharmConfig

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
    hostname: str | None
    tls_certs: dict[str, str]
    tls_keys: dict[str, str]

    @classmethod
    def from_charm(
        cls,
        charm: ops.CharmBase,
        config: CharmConfig,
        certificates: TLSCertificatesRequiresV4,
        gateway_route_provider: GatewayRouteProvider,
    ) -> "TLSInformation":
        """Get TLS information from a charm instance.

        Args:
            charm: The gateway-api-integrator charm.
            config: The charm configuration.
            certificates: TLS certificates requirer library.
            gateway_route_provider: The gateway route provider.

        Returns:
            TLSInformation: Information about configured TLS certs.
        """
        tls_certs = {}
        tls_keys = {}
        secret_resource_name_prefix = f"{charm.app.name}-secret"

        gateway_route_requirer_data = gateway_route_provider.get_data()
        hostname = config.external_hostname
        if (
            gateway_route_requirer_data is not None
            and gateway_route_requirer_data.application_data.hostname is not None
        ):
            hostname = gateway_route_requirer_data.application_data.hostname

        if hostname is not None:
            cls.validate(charm)
            for cert in certificates.get_provider_certificates():
                common_name = cert.certificate.common_name
                chain = cert.chain
                if chain[0] != cert.certificate:
                    chain.reverse()
                tls_certs[common_name] = "\n\n".join([str(cert) for cert in chain])
                tls_keys[common_name] = str(certificates.private_key)

        return cls(
            secret_resource_name_prefix=secret_resource_name_prefix,
            hostname=hostname,
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
