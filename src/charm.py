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
from charms.traefik_k8s.v2.ingress import (
    IngressPerAppDataProvidedEvent,
    IngressPerAppDataRemovedEvent,
    IngressPerAppProvider,
)
from lightkube import Client, KubeConfig
from lightkube.core.exceptions import ConfigError
from ops.charm import (
    ActionEvent,
    CharmBase,
    RelationBrokenEvent,
    RelationCreatedEvent,
    RelationJoinedEvent,
)
from ops.main import main
from ops.model import ActiveStatus, MaintenanceStatus, SecretNotFoundError, WaitingStatus

from resource_manager.gateway import GatewayResourceDefinition, GatewayResourceManager
from resource_manager.http_route import (
    HTTPRouteRedirectResourceManager,
    HTTPRouteResourceDefinition,
    HTTPRouteResourceManager,
    HTTPRouteType,
)
from resource_manager.secret import SecretResourceDefinition, TLSSecretResourceManager
from resource_manager.service import ServiceResourceDefinition, ServiceResourceManager
from state.config import CharmConfig
from state.gateway import GatewayResourceInformation
from state.http_route import HTTPRouteResourceInformation
from state.tls import TLSInformation
from state.validation import validate_config_and_integration
from tls_relation import TLSRelationService, get_hostname_from_cert

logger = logging.getLogger(__name__)
CREATED_BY_LABEL = "gateway-api-integrator.charm.juju.is/managed-by"
INGRESS_RELATION = "gateway"
TLS_CERT_RELATION = "certificates"


def _get_client(field_manager: str, namespace: str) -> Client:
    """Initialize the lightkube client with the correct namespace and field_manager.

    Args:
        field_manager: field manager for server side apply when patching resources.
        namespace: The k8s namespace in which resources are managed.

    Raises:
        LightKubeInitializationError: When initialization of the lightkube client fails

    Returns:
        Client: The initialized lightkube client
    """
    try:
        # Set field_manager for server-side apply when patching resources
        # Keep this consistent across client initializations
        kubeconfig = KubeConfig.from_service_account()
        client = Client(config=kubeconfig, field_manager=field_manager, namespace=namespace)
    except ConfigError as exc:
        logger.exception("Error initializing the lightkube client.")
        raise LightKubeInitializationError("Error initializing the lightkube client.") from exc

    return client


class LightKubeInitializationError(Exception):
    """Exception raised when initialization of the lightkube client failed."""


class GatewayAPICharm(CharmBase):
    """The main charm class for the gateway-api-integrator charm."""

    def __init__(self, *args) -> None:  # type: ignore[no-untyped-def]
        """Init method for the class.

        Args:
            args: Variable list of positional arguments passed to the parent constructor.
        """
        super().__init__(*args)

        self.certificates = TLSCertificatesRequiresV3(self, TLS_CERT_RELATION)
        self._ingress_provider = IngressPerAppProvider(charm=self, relation_name=INGRESS_RELATION)
        self._tls = TLSRelationService(self.model, self.certificates)

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

        self.framework.observe(self._ingress_provider.on.data_provided, self._on_data_provided)
        self.framework.observe(self._ingress_provider.on.data_removed, self._on_data_removed)

    @property
    def _labels(self) -> dict[str, str]:
        """Get labels assigned to resources created by this app."""
        return {CREATED_BY_LABEL: self.app.name}

    @validate_config_and_integration(defer=False)
    def _reconcile(self) -> None:  # pylint: disable=too-many-locals
        """Reconcile charm status based on configuration and integrations."""
        client = _get_client(field_manager=self.app.name, namespace=self.model.name)

        config = CharmConfig.from_charm(self, client)
        gateway_resource_information = GatewayResourceInformation.from_charm(self)
        tls_information = TLSInformation.from_charm(self, self.certificates)

        gateway_resource_manager = GatewayResourceManager(
            labels=self._labels,
            client=client,
        )
        secret_resource_manager = TLSSecretResourceManager(self._labels, client)
        secret = secret_resource_manager.define_resource(
            SecretResourceDefinition.from_tls_information(
                tls_information, config.external_hostname
            )
        )
        gateway = gateway_resource_manager.define_resource(
            GatewayResourceDefinition(gateway_resource_information, config, tls_information)
        )
        gateway_resource_manager.cleanup_resources(exclude=[gateway])
        secret_resource_manager.cleanup_resources(exclude=[secret])

        http_route_resource_information = HTTPRouteResourceInformation.from_charm(
            self, self._ingress_provider
        )
        service_resource_manager = ServiceResourceManager(self._labels, client)
        service = service_resource_manager.define_resource(
            ServiceResourceDefinition(http_route_resource_information)
        )
        http_route_resource_manager = HTTPRouteResourceManager(self._labels, client)
        redirect_resource_manager = HTTPRouteRedirectResourceManager(self._labels, client)
        redirect_route = redirect_resource_manager.define_resource(
            HTTPRouteResourceDefinition(
                http_route_resource_information,
                gateway_resource_information,
                HTTPRouteType.HTTP,
            )
        )
        https_route = http_route_resource_manager.define_resource(
            HTTPRouteResourceDefinition(
                http_route_resource_information,
                gateway_resource_information,
                HTTPRouteType.HTTPS,
            )
        )
        service_resource_manager.cleanup_resources(exclude=[service])
        http_route_resource_manager.cleanup_resources(exclude=[https_route])
        redirect_resource_manager.cleanup_resources(exclude=[redirect_route])

        relation = self.model.get_relation(INGRESS_RELATION)
        self._ingress_provider.publish_url(
            relation,
            (
                f"https://{config.external_hostname}"
                f"/{http_route_resource_information.requirer_model_name}"
                f"-{http_route_resource_information.application_name}"
            ),
        )

        self.unit.status = WaitingStatus("Waiting for gateway address")
        if gateway_address := gateway_resource_manager.gateway_address(gateway.metadata.name):
            self.unit.status = ActiveStatus(f"Gateway addresses: {gateway_address}")
        else:
            self.unit.status = WaitingStatus("Gateway address unavailable")

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
        TLSInformation.validate(self)

        for cert in self.certificates.get_provider_certificates():
            if get_hostname_from_cert(cert.certificate) == hostname:
                event.set_results(
                    {
                        "certificate": cert.certificate,
                        "ca": cert.ca,
                        "chain": cert.chain_as_pem(),
                    }
                )
                return

        event.fail(f"Missing or incomplete certificate data for {hostname}")

    @validate_config_and_integration(defer=True)
    def _on_certificates_relation_created(self, _: RelationCreatedEvent) -> None:
        """Handle the TLS Certificate relation created event."""
        TLSInformation.validate(self)
        client = _get_client(field_manager=self.app.name, namespace=self.model.name)
        config = CharmConfig.from_charm(self, client)
        self._tls.certificate_relation_created(config.external_hostname)

    @validate_config_and_integration(defer=True)
    def _on_certificates_relation_joined(self, _: RelationJoinedEvent) -> None:
        """Handle the TLS Certificate relation joined event."""
        TLSInformation.validate(self)
        client = _get_client(field_manager=self.app.name, namespace=self.model.name)
        config = CharmConfig.from_charm(self, client)
        self._tls.certificate_relation_joined(config.external_hostname)

    def _on_certificates_relation_broken(self, _: RelationBrokenEvent) -> None:
        """Handle the TLS Certificate relation broken event."""
        self._reconcile()

    def _on_certificate_available(self, _: CertificateAvailableEvent) -> None:
        """Handle the TLS Certificate available event."""
        logger.info("TLS certificate available, creating resources.")
        self._reconcile()

    @validate_config_and_integration(defer=True)
    def _on_certificate_expiring(self, event: CertificateExpiringEvent) -> None:
        """Handle the TLS Certificate expiring event.

        Args:
            event: The event that fires this method.
        """
        TLSInformation.validate(self)
        self._tls.certificate_expiring(event)

    @validate_config_and_integration(defer=True)
    def _on_certificate_invalidated(self, event: CertificateInvalidatedEvent) -> None:
        """Handle the TLS Certificate invalidation event.

        Args:
            event: The event that fires this method.
        """
        TLSInformation.validate(self)
        if event.reason == "revoked":
            self._tls.certificate_invalidated(event)
        if event.reason == "expired":
            self._tls.certificate_expiring(event)
        self.unit.status = MaintenanceStatus("Waiting for new certificate")

    @validate_config_and_integration(defer=True)
    def _on_all_certificates_invalidated(self, _: AllCertificatesInvalidatedEvent) -> None:
        """Handle the TLS Certificate relation broken event."""
        TLSInformation.validate(self)
        client = _get_client(field_manager=self.app.name, namespace=self.model.name)
        config = CharmConfig.from_charm(self, client)
        hostname = config.external_hostname

        try:
            secret = self.model.get_secret(label=f"private-key-{hostname}")
            secret.remove_all_revisions()
        except SecretNotFoundError:
            logger.warning("Juju secret for %s already does not exist", hostname)

    def _on_data_provided(self, _: IngressPerAppDataProvidedEvent) -> None:
        """Handle the data-provided event."""
        self._reconcile()

    def _on_data_removed(self, _: IngressPerAppDataRemovedEvent) -> None:
        """Handle the data-removed event."""
        self._reconcile()


if __name__ == "__main__":  # pragma: no cover
    main(GatewayAPICharm)
