#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator charm file."""

import logging
import typing
from typing import Any, List, Union

from charms.tls_certificates_interface.v3.tls_certificates import (
    AllCertificatesInvalidatedEvent,
    CertificateAvailableEvent,
    CertificateExpiringEvent,
    CertificateInvalidatedEvent,
    TLSCertificatesRequiresV3,
)
from lightkube import Client, KubeConfig
from ops.charm import ActionEvent, CharmBase, RelationCreatedEvent, RelationJoinedEvent
from ops.jujuversion import JujuVersion
from ops.main import main
from ops.model import (
    ActiveStatus,
    BlockedStatus,
    MaintenanceStatus,
    Relation,
    SecretNotFoundError,
    WaitingStatus,
)

from resource_manager.gateway import CreateGatewayError, GatewayResourceManager
from state.config import InvalidCharmConfigError
from state.gateway import GatewayResourceDefinition
from state.secret import SecretResourceDefinition
from state.tls import TLSInformation, TlsIntegrationMissingError
from tls_relation import TLSRelationService

TLS_CERT = "certificates"
LOGGER = logging.getLogger(__name__)
CREATED_BY_LABEL = "gateway-api-integrator.charm.juju.is/managed-by"


class GatewayAPICharm(CharmBase):
    """The main charm class for the gateway-api-integrator charm."""

    _authed = False

    def __init__(self, *args) -> None:  # type: ignore[no-untyped-def]
        """Init method for the class.

        Args:
            args: Variable list of positional arguments passed to the parent constructor.
        """
        super().__init__(*args)

        self._kubeconfig = KubeConfig.from_service_account()
        self.client = Client(config=self._kubeconfig)
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

    @property
    def _labels(self) -> typing.Dict[str, str]:
        """Get labels assigned to resources created by this app."""
        return {CREATED_BY_LABEL: self.app.name}

    def _reconcile(self) -> None:
        """Reconcile charm status based on configuration and integrations.

        Raises:
            RuntimeError: when the creation of the gateway resource failed.
        """
        try:
            gateway_resource_definition = GatewayResourceDefinition.from_charm(self)
        except InvalidCharmConfigError as exc:
            LOGGER.error("Invalid charm config: %s", exc.msg)
            self.unit.status = BlockedStatus("Invalid charm configuration")
            return

        try:
            # This will be replaced by a secret resource definition component of the state
            # InvalidCharmConfigError will also not be caught twice
            tls_information = TLSInformation.from_charm(self)
        except (TlsIntegrationMissingError, InvalidCharmConfigError):
            self.unit.status = BlockedStatus("Waiting for TLS.")
            return

        secret_resource_definition = SecretResourceDefinition.from_charm_and_tls_information(
            self, tls_information
        )

        gateway_resource_manager = GatewayResourceManager(
            namespace=gateway_resource_definition.namespace,
            labels=self._labels,
            client=self.client,
        )

        try:
            gateway = gateway_resource_manager.define_resource(gateway_resource_definition)
        except CreateGatewayError as exc:
            LOGGER.error("Error creating the gateway resource %s", exc)
            raise RuntimeError("Cannot create gateway.") from exc
        self.unit.status = ActiveStatus()
        gateway_resource_manager.cleanup_resources(exclude=gateway)

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

        try:
            tls_information = TLSInformation.from_charm(self)
        except (TlsIntegrationMissingError, InvalidCharmConfigError) as exc:
            event.fail(f"Charm is not in state to handle actions: {exc.msg}")
            return

        tls_rel_data = tls_information.tls_requirer_integration.data[self.app]
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
        try:
            tls_information = TLSInformation.from_charm(self)
        except (TlsIntegrationMissingError, InvalidCharmConfigError) as exc:
            LOGGER.error("Charm is not ready to handle this event, deferring: %s.", exc)
            event.defer()
            return

        self._tls.certificate_relation_created(
            tls_information.config.external_hostname, tls_information.tls_requirer_integration
        )

    def _on_certificates_relation_joined(self, event: RelationJoinedEvent) -> None:
        """Handle the TLS Certificate relation joined event.

        Args:
            event: The event that fires this method.
        """
        try:
            tls_information = TLSInformation.from_charm(self)
        except (TlsIntegrationMissingError, InvalidCharmConfigError) as exc:
            self.unit.status = BlockedStatus()
            LOGGER.error("Charm is not ready to handle this event, deferring: %s.", exc)
            event.defer()
            return

        self._tls.certificate_relation_joined(
            tls_information.config.external_hostname,
            self.certificates,
            tls_information.tls_requirer_integration,
        )

    def _on_certificates_relation_broken(self, _: Any) -> None:
        """Handle the TLS Certificate relation broken event."""
        self._reconcile()

    def _on_certificate_available(self, event: CertificateAvailableEvent) -> None:
        """Handle the TLS Certificate available event.

        Args:
            event: The event that fires this method.
        """
        try:
            tls_information = TLSInformation.from_charm(self)
        except (TlsIntegrationMissingError, InvalidCharmConfigError) as exc:
            self.unit.status = WaitingStatus("Waiting for certificates relation to be created")
            LOGGER.error(
                "(%s) charm is not ready to handle this event, deferring: %s.", event, exc
            )
            event.defer()
            return

        self._tls.certificate_relation_available(event, tls_information.tls_requirer_integration)
        LOGGER.info("TLS configured, creating kubernetes resources.")
        self._reconcile()

    def _on_certificate_expiring(
        self,
        event: Union[CertificateExpiringEvent, CertificateInvalidatedEvent],
    ) -> None:
        """Handle the TLS Certificate expiring event.

        Args:
            event: The event that fires this method.

        Raises:
            RuntimeError: _description_
        """
        try:
            tls_information = TLSInformation.from_charm(self)
        except TlsIntegrationMissingError as exc:
            self.unit.status = WaitingStatus("Waiting for certificates relation to be created")
            LOGGER.error(
                "(%s) charm is not ready to handle this event, deferring: %s.", event, exc
            )
            event.defer()
            return
        except InvalidCharmConfigError as exc:
            LOGGER.warning(
                "(%s) Invalid configuration : %s, cannot reissue cert, raising exception.",
                event,
                exc,
            )
            raise RuntimeError("Invalid configuration while reissuing certificate") from exc

        self._tls.certificate_expiring(
            event, self.certificates, tls_information.tls_requirer_integration
        )

    # This method is too complex but hard to simplify.
    def _certificate_revoked(
        self, revoke_list: List[str], tls_requirer_integration: Relation
    ) -> None:  # noqa: C901
        """Handle TLS Certificate revocation.

        Args:
            revoke_list: TLS Certificates list to revoke
            tls_requirer_integration: The TLS certificate integration.
        """
        for hostname in revoke_list:
            old_csr = self._tls.get_relation_data_field(
                f"csr-{hostname}",
                tls_requirer_integration,  # type: ignore[arg-type]
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
                    tls_requirer_integration,  # type: ignore[arg-type]
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
        try:
            tls_information = TLSInformation.from_charm(self)
        except (TlsIntegrationMissingError, InvalidCharmConfigError) as exc:
            self.unit.status = WaitingStatus("Waiting for certificates relation to be created")
            LOGGER.error(
                "(%s) charm is not ready to handle this event, deferring: %s.", event, exc
            )
            event.defer()
            return

        if event.reason == "revoked":
            hostname = self._tls.get_hostname_from_cert(event.certificate)
            self._certificate_revoked([hostname], tls_information.tls_requirer_integration)
        if event.reason == "expired":
            self._tls.certificate_expiring(
                event, self.certificates, tls_information.tls_requirer_integration
            )
        self.unit.status = MaintenanceStatus("Waiting for new certificate")

    def _on_all_certificates_invalidated(self, event: AllCertificatesInvalidatedEvent) -> None:
        """Handle the TLS Certificate relation broken event.

        Args:
            event: The event that fires this method.
        """
        try:
            tls_information = TLSInformation.from_charm(self)
            tls_information.tls_requirer_integration.data[self.app].clear()
        except (TlsIntegrationMissingError, InvalidCharmConfigError) as exc:
            self.unit.status = WaitingStatus("Waiting for certificates relation to be created")
            LOGGER.error(
                "(%s) charm is not ready to handle this event, deferring: %s.", event, exc
            )
            return

        try:
            gateway_resource_definition = GatewayResourceDefinition.from_charm(self)
        except InvalidCharmConfigError as exc:
            LOGGER.error("Charm config not valid, skipping: %s", exc.msg)
            return

        if JujuVersion.from_environ().has_secrets:
            hostname = gateway_resource_definition.config.external_hostname
            try:
                secret = self.model.get_secret(label=f"private-key-{hostname}")
                secret.remove_all_revisions()
            except SecretNotFoundError:
                LOGGER.warning("Juju secret for %s already does not exist", hostname)


if __name__ == "__main__":  # pragma: no cover
    main(GatewayAPICharm)
