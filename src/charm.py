#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator charm file."""

import logging
from typing import Any, List, Union, cast

import kubernetes.client
from charms.tls_certificates_interface.v3.tls_certificates import (
    AllCertificatesInvalidatedEvent,
    CertificateAvailableEvent,
    CertificateExpiringEvent,
    CertificateInvalidatedEvent,
    TLSCertificatesRequiresV3,
)
from ops.charm import ActionEvent, CharmBase, RelationCreatedEvent, RelationJoinedEvent
from ops.jujuversion import JujuVersion
from ops.main import main
from ops.model import (
    ActiveStatus,
    BlockedStatus,
    MaintenanceStatus,
    SecretNotFoundError,
    WaitingStatus,
)

from gateway_definition import get_config
from tls_relation import TLSRelationService

TLS_CERT = "certificates"
LOGGER = logging.getLogger(__name__)


class GatewayAPICharm(CharmBase):
    """The main charm class for the gateway-api-integrator charm."""

    _authed = False

    def __init__(self, *args) -> None:  # type: ignore[no-untyped-def]
        """Init method for the class.

        Args:
            args: Variable list of positional arguments passed to the parent constructor.
        """
        super().__init__(*args)
        kubernetes.config.load_incluster_config()

        self._tls = TLSRelationService(self.model)

        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.start, self._on_start)

        self.certificates = TLSCertificatesRequiresV3(self, TLS_CERT)
        self.framework.observe(
            self.on.certificates_relation_created, self._on_certificates_relation_created
        )
        self.framework.observe(
            self.on.certificates_relation_joined, self._on_certificates_relation_joined
        )
        self.framework.observe(
            self.on.certificates_relation_broken, self._on_certificates_relation_broken
        )
        self.framework.observe(
            self.certificates.on.certificate_available, self._on_certificate_available
        )
        self.framework.observe(
            self.certificates.on.certificate_expiring, self._on_certificate_expiring
        )
        self.framework.observe(
            self.certificates.on.certificate_invalidated, self._on_certificate_invalidated
        )
        self.framework.observe(self.on.get_certificate_action, self._on_get_certificate_action)
        self.framework.observe(
            self.certificates.on.all_certificates_invalidated,
            self._on_all_certificates_invalidated,
        )

    def get_hostname(self) -> str:
        """Get a list containing all ingress hostnames.

        Returns:
            A list containing service and additional hostnames
        """
        # The relation will always exist when this method is called
        external_hostname = cast(str, get_config(self, "external-hostname"))
        return external_hostname

    def _are_relations_ready(self) -> bool:
        """Check if required relations are ready.

        Returns:
            Whether required relations are ready and execution should continue.
        """
        return self._tls.get_tls_relation() is not None

    def _reconcile(self) -> None:
        """Reconcile charm status based on configuration and integrations."""
        tls_certificates_relation = self._tls.get_tls_relation()
        if not tls_certificates_relation:
            self.unit.status = BlockedStatus("Waiting for TLS.")
            return
        self.unit.status = ActiveStatus()

    def _on_config_changed(self, _: Any) -> None:
        """Handle the config-changed event."""
        self._reconcile()

    def _on_start(self, _: Any) -> None:
        """Handle the start event."""
        self._reconcile()

    def _on_get_certificate_action(self, event: ActionEvent) -> None:
        """Triggered when users run the `get-certificate` Juju action.

        Args:
            event: Juju event
        """
        hostname = event.params["hostname"]
        tls_certificates_relation = self._tls.get_tls_relation()
        tls_secret_name = get_config(self, "tls-secret-name")

        if not tls_certificates_relation and not tls_secret_name:
            event.fail("Certificates relation not created.")
            return

        tls_rel_data = tls_certificates_relation.data[self.app]
        if any(
            not tls_rel_data.get(key)
            for key in [f"certificate-{hostname}", f"ca-{hostname}", f"chain-{hostname}"]
        ):
            event.fail("Missing or incomplete certificate data")
            return

        event.set_results(
            {
                f"certificate-{hostname}": tls_rel_data.get(f"certificate-{hostname}"),
                f"ca-{hostname}": tls_rel_data.get(f"ca-{hostname}"),
                f"chain-{hostname}": tls_rel_data.get(f"chain-{hostname}"),
            }
        )

    def _on_certificates_relation_created(self, event: RelationCreatedEvent) -> None:
        """Handle the TLS Certificate relation created event.

        Args:
            event: The event that fires this method.
        """
        if not self._are_relations_ready():
            self.unit.status = WaitingStatus("Waiting for certificates relation to be created")
            event.defer()
            return
        hostname = self.get_hostname()
        if not hostname:
            self.unit.status = BlockedStatus("Waiting for hostname to be configured")
            event.defer()
            return
        self._tls.certificate_relation_created(hostname)

    def _on_certificates_relation_joined(self, event: RelationJoinedEvent) -> None:
        """Handle the TLS Certificate relation joined event.

        Args:
            event: The event that fires this method.
        """
        if not self._are_relations_ready():
            self.unit.status = WaitingStatus("Waiting for certificates relation to be created")
            event.defer()
            return
        hostname = self.get_hostname()
        if not hostname:
            self.unit.status = BlockedStatus("Waiting for hostname to be configured")
            event.defer()
            return
        self._tls.certificate_relation_joined(hostname, self.certificates)

    def _on_certificates_relation_broken(self, _: Any) -> None:
        """Handle the TLS Certificate relation broken event."""
        self._reconcile()

    def _on_certificate_available(self, event: CertificateAvailableEvent) -> None:
        """Handle the TLS Certificate available event.

        Args:
            event: The event that fires this method.
        """
        tls_certificates_relation = self._tls.get_tls_relation()
        if not tls_certificates_relation:
            self.unit.status = WaitingStatus("Waiting for certificates relation to be created")
            event.defer()
            return
        self._tls.certificate_relation_available(event)
        self._reconcile()

    def _on_certificate_expiring(
        self,
        event: Union[CertificateExpiringEvent, CertificateInvalidatedEvent],
    ) -> None:
        """Handle the TLS Certificate expiring event.

        Args:
            event: The event that fires this method.
        """
        if not self._are_relations_ready():
            self.unit.status = WaitingStatus("Waiting for certificates relation to be created")
            event.defer()
            return
        self._tls.certificate_expiring(event, self.certificates)

    # This method is too complex but hard to simplify.
    def _certificate_revoked(self, revoke_list: List[str]) -> None:  # noqa: C901
        """Handle TLS Certificate revocation.

        Args:
            revoke_list: TLS Certificates list to revoke
        """
        if not self._are_relations_ready():
            return
        tls_certificates_relation = self._tls.get_tls_relation()
        for hostname in revoke_list:
            old_csr = self._tls.get_relation_data_field(
                f"csr-{hostname}",
                tls_certificates_relation,  # type: ignore[arg-type]
            )
            if not old_csr:
                continue
            if JujuVersion.from_environ().has_secrets:
                try:
                    secret = self.model.get_secret(label=f"private-key-{hostname}")
                    secret.remove_all_revisions()
                except SecretNotFoundError:
                    LOGGER.warning("Juju secret for %s already does not exist", hostname)
                    continue
            try:
                self._tls.pop_relation_data_fields(
                    [f"key-{hostname}", f"password-{hostname}"],
                    tls_certificates_relation,  # type: ignore[arg-type]
                )
            except KeyError:
                LOGGER.warning("Relation data for %s already does not exist", hostname)
            self.certificates.request_certificate_revocation(
                certificate_signing_request=old_csr.encode()
            )

    def _on_certificate_invalidated(self, event: CertificateInvalidatedEvent) -> None:
        """Handle the TLS Certificate invalidation event.

        Args:
            event: The event that fires this method.
        """
        tls_certificates_relation = self._tls.get_tls_relation()
        if not tls_certificates_relation:
            self.unit.status = WaitingStatus("Waiting for certificates relation to be created")
            event.defer()
            return
        if event.reason == "revoked":
            hostname = self._tls.get_hostname_from_cert(event.certificate)
            self._certificate_revoked([hostname])
        if event.reason == "expired":
            self._tls.certificate_expiring(event, self.certificates)
        self.unit.status = MaintenanceStatus("Waiting for new certificate")

    def _on_all_certificates_invalidated(self, _: AllCertificatesInvalidatedEvent) -> None:
        """Handle the TLS Certificate relation broken event.

        Args:
            _: The event that fires this method.
        """
        tls_relation = self._tls.get_tls_relation()
        if tls_relation:
            tls_relation.data[self.app].clear()
        if JujuVersion.from_environ().has_secrets:
            hostname = self.get_hostname()
            try:
                secret = self.model.get_secret(label=f"private-key-{hostname}")
                secret.remove_all_revisions()
            except SecretNotFoundError:
                LOGGER.warning("Juju secret for %s already does not exist", hostname)


if __name__ == "__main__":  # pragma: no cover
    main(GatewayAPICharm)
