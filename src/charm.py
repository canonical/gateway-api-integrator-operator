#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator charm file."""

import logging
import typing

from charms.tls_certificates_interface.v3.tls_certificates import (
    AllCertificatesInvalidatedEvent,
    CertificateAvailableEvent,
    CertificateExpiringEvent,
    CertificateInvalidatedEvent,
    TLSCertificatesRequiresV3,
)
from lightkube import Client, KubeConfig
from lightkube.core.exceptions import ConfigError
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
from resource_manager.resource_manager import InsufficientPermissionError, InvalidResourceError
from state.config import CharmConfig, InvalidCharmConfigError
from state.gateway import GatewayResourceDefinition
from state.tls import TLSInformation, TlsIntegrationMissingError
from state.validation import validate_config_and_integration
from tls_relation import TLSRelationService

TLS_CERT = "certificates"
logger = logging.getLogger(__name__)
CREATED_BY_LABEL = "gateway-api-integrator.charm.juju.is/managed-by"


class GatewayAPICharm(CharmBase):
    """The main charm class for the gateway-api-integrator charm."""

    _authed = False

    def __init__(self, *args) -> None:  # type: ignore[no-untyped-def]
        """Init method for the class.

        Args:
            args: Variable list of positional arguments passed to the parent constructor.

        Raises:
            RuntimeError: If initialization of the lightkube client fails
        """
        super().__init__(*args)
        try:
            # Set field_manager for server-side apply when patching resources
            # Keep this consistent across client initializations
            kubeconfig = KubeConfig.from_service_account()
            self.client = Client(
                config=kubeconfig, field_manager=self.app.name, namespace=self.model.name
            )
        except ConfigError as exc:
            logger.exception("Error initializing the lightkube client.")
            raise RuntimeError("Error initializing the lightkube client.") from exc

        self.certificates = TLSCertificatesRequiresV3(self, TLS_CERT)
        self._tls = TLSRelationService(self.model)

        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.start, self._on_start)

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
    def _labels(self) -> dict[str, str]:
        """Get labels assigned to resources created by this app."""
        return {CREATED_BY_LABEL: self.app.name}

    @validate_config_and_integration(defer=False)
    def _reconcile(self) -> None:
        """Reconcile charm status based on configuration and integrations.

        Raises:
            RuntimeError: when initializing the lightkube client fails,
            or when creating the gateway resource fails.
        """
        config = CharmConfig.from_charm(self)
        gateway_resource_definition = GatewayResourceDefinition.from_charm(self)
        # This line is currently here to validate the existence of the certificates relation.
        # This charm state component will be used by the upcoming SecretResourceManager.
        TLSInformation.from_charm(self)

        gateway_resource_manager = GatewayResourceManager(
            labels=self._labels,
            client=self.client,
        )

        try:
            gateway = gateway_resource_manager.define_resource(gateway_resource_definition, config)
        except (CreateGatewayError, InvalidResourceError) as exc:
            logger.exception("Error creating the gateway resource %s", exc)
            raise RuntimeError("Cannot create gateway.") from exc
        except InsufficientPermissionError as exc:
            self.unit.status = BlockedStatus(exc.msg)
            return

        self.unit.status = WaitingStatus("Waiting for gateway address")
        if gateway_address := gateway_resource_manager.gateway_address(gateway.metadata.name):
            self.unit.status = ActiveStatus(f"Gateway addresses: {gateway_address}")
        else:
            self.unit.status = WaitingStatus("Gateway address unavailable")
        gateway_resource_manager.cleanup_resources(exclude=gateway)

    def _on_config_changed(self, _: typing.Any) -> None:
        """Handle the config-changed event."""
        self._reconcile()

    def _on_start(self, _: typing.Any) -> None:
        """Handle the start event."""
        self._reconcile()

    @validate_config_and_integration(defer=False)
    def _on_get_certificate_action(self, event: ActionEvent) -> None:
        """Triggered when users run the `get-certificate` Juju action.

        Args:
            event: Juju event
        """
        hostname = event.params["hostname"]
        tls_information = TLSInformation.from_charm(self)

        tls_rel_data = tls_information.tls_requirer_integration.data[self.app]
        if any(
            not tls_rel_data.get(key)
            for key in [f"certificate-{hostname}", f"ca-{hostname}", f"chain-{hostname}"]
        ):
            event.fail("Missing or incomplete certificate data")
            return

        event.set_results(
            {
                f"certificate-{hostname}": tls_rel_data[f"certificate-{hostname}"],
                f"ca-{hostname}": tls_rel_data[f"ca-{hostname}"],
                f"chain-{hostname}": tls_rel_data[f"chain-{hostname}"],
            }
        )

    @validate_config_and_integration(defer=True)
    def _on_certificates_relation_created(self, _: RelationCreatedEvent) -> None:
        """Handle the TLS Certificate relation created event."""
        tls_information = TLSInformation.from_charm(self)
        config = CharmConfig.from_charm(self)

        self._tls.certificate_relation_created(
            config.external_hostname, tls_information.tls_requirer_integration
        )

    @validate_config_and_integration(defer=True)
    def _on_certificates_relation_joined(self, _: RelationJoinedEvent) -> None:
        """Handle the TLS Certificate relation joined event."""
        tls_information = TLSInformation.from_charm(self)
        config = CharmConfig.from_charm(self)

        self._tls.certificate_relation_joined(
            config.external_hostname,
            self.certificates,
            tls_information.tls_requirer_integration,
        )

    def _on_certificates_relation_broken(self, _: typing.Any) -> None:
        """Handle the TLS Certificate relation broken event."""
        self._reconcile()

    @validate_config_and_integration(defer=True)
    def _on_certificate_available(self, event: CertificateAvailableEvent) -> None:
        """Handle the TLS Certificate available event.

        Args:
            event: The event that fires this method.
        """
        tls_information = TLSInformation.from_charm(self)

        self._tls.certificate_relation_available(event, tls_information.tls_requirer_integration)
        logger.info("TLS configured, creating kubernetes resources.")
        self._reconcile()

    @validate_config_and_integration(defer=True)
    def _on_certificate_expiring(
        self,
        event: typing.Union[CertificateExpiringEvent, CertificateInvalidatedEvent],
    ) -> None:
        """Handle the TLS Certificate expiring event.

        Args:
            event: The event that fires this method.
        """
        tls_information = TLSInformation.from_charm(self)
        self._tls.certificate_expiring(
            event, self.certificates, tls_information.tls_requirer_integration
        )

    # This method is too complex but hard to simplify.
    def _certificate_revoked(
        self, revoke_list: typing.List[str], tls_requirer_integration: Relation
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
                    logger.warning("Juju secret for %s already does not exist", hostname)
                    continue
            try:
                self._tls.pop_relation_data_fields(
                    [f"key-{hostname}", f"password-{hostname}"],
                    tls_requirer_integration,  # type: ignore[arg-type]
                )
            except KeyError:
                logger.warning("Relation data for %s already does not exist", hostname)
            self.certificates.request_certificate_revocation(
                certificate_signing_request=old_csr.encode()
            )

    @validate_config_and_integration(defer=True)
    def _on_certificate_invalidated(self, event: CertificateInvalidatedEvent) -> None:
        """Handle the TLS Certificate invalidation event.

        Args:
            event: The event that fires this method.
        """
        try:
            tls_information = TLSInformation.from_charm(self)
        except (TlsIntegrationMissingError, InvalidCharmConfigError) as exc:
            self.unit.status = WaitingStatus("Waiting for certificates relation to be created")
            logger.error(
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

    @validate_config_and_integration(defer=True)
    def _on_all_certificates_invalidated(self, _: AllCertificatesInvalidatedEvent) -> None:
        """Handle the TLS Certificate relation broken event."""
        tls_information = TLSInformation.from_charm(self)
        tls_information.tls_requirer_integration.data[self.app].clear()

        config = CharmConfig.from_charm(self)

        if JujuVersion.from_environ().has_secrets:
            hostname = config.external_hostname
            try:
                secret = self.model.get_secret(label=f"private-key-{hostname}")
                secret.remove_all_revisions()
            except SecretNotFoundError:
                logger.warning("Juju secret for %s already does not exist", hostname)


if __name__ == "__main__":  # pragma: no cover
    main(GatewayAPICharm)
