# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator resource definition."""

import dataclasses
import typing
from typing import Dict

import ops
from ops.jujuversion import JujuVersion
from ops.model import Relation
from pydantic import ValidationError

from .config import CharmConfig, InvalidCharmConfigError, get_invalid_config_fields

TLS_CERTIFICATES_INTEGRATION = "certificates"


class TlsIntegrationMissingError(Exception):
    """Exception raised when _situation_.

    Attrs:
        msg (str): Explanation of the error.
    """

    def __init__(self, msg: str):
        """Initialize a new instance of the TlsIntegrationMissingError exception.

        Args:
            msg (str): Explanation of the error.
        """
        self.msg = msg


@dataclasses.dataclass(frozen=True)
class TLSInformation:
    """A component of charm state containing resource definition for kubernetes secret.

    Attrs:
        tls_requirer_integration: The integration instance with a TLS provider.
        tls_certs: A dict of hostname: certificate obtained from the relation.
        tls_keys: A dict of hostname: private_key stored in juju secrets.
        config: The charm's configuration data.
    """

    tls_requirer_integration: Relation
    tls_certs: Dict[str, str]
    tls_keys: Dict[str, str]
    config: CharmConfig

    @classmethod
    def from_charm(cls, charm: ops.CharmBase) -> "TLSInformation":
        """Create a resource definition from charm instance.

        Args:
            charm (ops.CharmBase): _description_

        Raises:
            TlsIntegrationMissingError: _description_
            InvalidCharmConfigError: _description_

        Returns:
            TLSInformation: _description_
        """
        tls_requirer_integration = charm.model.get_relation(TLS_CERTIFICATES_INTEGRATION)
        if tls_requirer_integration is None:
            raise TlsIntegrationMissingError("certificates integration not set up.")

        try:
            config = CharmConfig(
                gateway_class=typing.cast(str, charm.config.get("gateway-class")),
                external_hostname=typing.cast(str, charm.config.get("external-hostname")),
            )
        except ValidationError as exc:
            error_field_str = ",".join(f"{f}" for f in get_invalid_config_fields(exc))
            raise InvalidCharmConfigError(f"invalid configuration: {error_field_str}") from exc

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
            config=config,
            tls_requirer_integration=tls_requirer_integration,
            tls_certs=tls_certs,
            tls_keys=tls_keys,
        )
