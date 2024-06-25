# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator resource definition."""

import dataclasses

import ops
from ops.jujuversion import JujuVersion
from ops.model import Relation

TLS_CERTIFICATES_INTEGRATION = "certificates"


class TlsIntegrationMissingError(Exception):
    """Exception raised when _situation_."""


@dataclasses.dataclass(frozen=True)
class TLSInformation:
    """A component of charm state containing resource definition for kubernetes secret.

    Attrs:
        tls_requirer_integration: The integration instance with a TLS provider.
        tls_certs: A dict of hostname: certificate obtained from the relation.
        tls_keys: A dict of hostname: private_key stored in juju secrets.
    """

    tls_requirer_integration: Relation
    tls_certs: dict[str, str]
    tls_keys: dict[str, str]

    @classmethod
    def from_charm(cls, charm: ops.CharmBase) -> "TLSInformation":
        """Get TLS information from a charm instance.

        Args:
            charm (ops.CharmBase): The gateway-api-integrator charm.

        Raises:
            TlsIntegrationMissingError: When integration is not ready.

        Returns:
            TLSInformation: Information about configured TLS certs.
        """
        tls_requirer_integration = charm.model.get_relation(TLS_CERTIFICATES_INTEGRATION)
        if (
            tls_requirer_integration is None
            or tls_requirer_integration.data.get(charm.app) is None
        ):
            raise TlsIntegrationMissingError("Certificates integration not ready.")

        tls_certs = {}
        tls_keys = {}

        for key, value in tls_requirer_integration.data[charm.app].items():
            if key.startswith("chain-"):
                hostname = key.split("-", maxsplit=1)[1]
                tls_certs[hostname] = value

                if JujuVersion.from_environ().has_secrets:
                    secret = charm.model.get_secret(label=f"private-key-{hostname}")
                    tls_keys[hostname] = secret.get_content()["key"]

        return cls(
            tls_requirer_integration=tls_requirer_integration,
            tls_certs=tls_certs,
            tls_keys=tls_keys,
        )
