#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator charm file."""

import logging
import typing
import uuid

from charms.bind.v0.dns_record import (
    DNSRecordRequirerData,
    DNSRecordRequires,
    RecordClass,
    RecordType,
    RequirerEntry,
)
from charms.tls_certificates_interface.v3.tls_certificates import (
    AllCertificatesInvalidatedEvent,
    CertificateExpiringEvent,
    CertificateInvalidatedEvent,
    TLSCertificatesRequiresV3,
)
from charms.traefik_k8s.v2.ingress import IngressPerAppProvider
from client import get_client
from lightkube import Client
from ops import BlockedStatus, HookEvent
from ops.charm import (
    ActionEvent,
    CharmBase,
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
from resource_manager.permission import InsufficientPermissionError
from resource_manager.secret import SecretResourceDefinition, TLSSecretResourceManager
from resource_manager.service import ServiceResourceDefinition, ServiceResourceManager
from state.config import CharmConfig, InvalidCharmConfigError
from state.gateway import GatewayResourceInformation
from state.http_route import HTTPRouteResourceInformation
from state.tls import TLSInformation
from state.validation import validate_config_and_integration
from tls_relation import TLSRelationService, get_hostname_from_cert

logger = logging.getLogger(__name__)
CREATED_BY_LABEL = "gateway-api-integrator.charm.juju.is/managed-by"
INGRESS_RELATION = "gateway"
TLS_CERT_RELATION = "certificates"
# Randomly selected UUID namespace for generating UUID for DNS records.
UUID_NAMESPACE = uuid.UUID("f8f206da-a7f8-4206-b044-30be3724a09d")


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
        self.dns_record_requirer = DNSRecordRequires(self)

        self.framework.observe(self.on.start, self._reconcile)
        self.framework.observe(self.on.config_changed, self._reconcile)

        self.framework.observe(
            self.on.certificates_relation_joined, self._on_certificates_relation_joined
        )
        self.framework.observe(self.on.certificates_relation_broken, self._reconcile)
        self.framework.observe(self.certificates.on.certificate_available, self._reconcile)
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

        self.framework.observe(self._ingress_provider.on.data_provided, self._reconcile)
        self.framework.observe(self._ingress_provider.on.data_removed, self._reconcile)

        self.framework.observe(self.on.dns_record_relation_joined, self._reconcile)

    @property
    def _labels(self) -> dict[str, str]:
        """Get labels assigned to resources created by this app."""
        return {CREATED_BY_LABEL: self.app.name}


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
    def _on_certificates_relation_joined(self, _: RelationJoinedEvent) -> None:
        """Handle the TLS Certificate relation joined event."""
        client = get_client(field_manager=self.app.name, namespace=self.model.name)
        try:
            charm_config = CharmConfig.from_charm(self, client)
        except InvalidCharmConfigError as e:
            self.unit.status = BlockedStatus(str(e))
            return
        except InsufficientPermissionError as e:
            self.unit.status = BlockedStatus(str(e))
            return
        TLSInformation.validate(self)
        self._tls.request_certificate(charm_config.external_hostname)

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
        client = get_client(field_manager=self.app.name, namespace=self.model.name)
        try:
            charm_config = CharmConfig.from_charm(self, client)
        except InvalidCharmConfigError as e:
            self.unit.status = BlockedStatus(str(e))
            return
        except InsufficientPermissionError as e:
            self.unit.status = BlockedStatus(str(e))
            return
        TLSInformation.validate(self)
        if event.reason == "revoked":
            self._tls.certificate_invalidated(event)
        if event.reason == "expired":
            self._tls.certificate_expiring(event)
        self.unit.status = MaintenanceStatus("Waiting for new certificate")

    @validate_config_and_integration(defer=True)
    def _on_all_certificates_invalidated(self, _: AllCertificatesInvalidatedEvent) -> None:
        """Handle the TLS Certificate relation broken event."""
        client = get_client(field_manager=self.app.name, namespace=self.model.name)
        try:
            charm_config = CharmConfig.from_charm(self, client)
        except InvalidCharmConfigError as e:
            self.unit.status = BlockedStatus(str(e))
            return
        except InsufficientPermissionError as e:
            self.unit.status = BlockedStatus(str(e))
            return
        TLSInformation.validate(self)
        hostname = charm_config.external_hostname
        try:
            secret = self.model.get_secret(label=f"private-key-{hostname}")
            secret.remove_all_revisions()
        except SecretNotFoundError:
            logger.warning("Juju secret for %s already does not exist", hostname)

    @validate_config_and_integration(defer=False)
    def _reconcile(self, _: HookEvent) -> None:
        """Reconcile charm status based on configuration and integrations.

        Actions performed in this method:
            1. Initialize charm state components.
            2. Create the gateway and secret resources.
            3. Create ingress-related resources:
                - service
                - http_route (HTTPS)
                - http_route (HTTPtoHTTPS redirect)
            4. Publish the ingress URL to the requirer charm.
            5. Update the DNS record relation with the DNS record data
            6. Set the gateway LB address in the charm's status message.
        """
        client = get_client(field_manager=self.app.name, namespace=self.model.name)
        try:
            charm_config = CharmConfig.from_charm(self, client)
        except InvalidCharmConfigError as e:
            self.unit.status = BlockedStatus(str(e))
            return
        except InsufficientPermissionError as e:
            self.unit.status = BlockedStatus(str(e))
            return
        TLSInformation.validate(self)
        if self._certificates_revocation_needed(client, charm_config):
            self._tls.revoke_all_certificates()
            self._tls.generate_private_key(charm_config.external_hostname)
            self._tls.request_certificate(charm_config.external_hostname)
            return  # _reconcile will be triggered with the next certificates_available event.
        gateway_resource_information = GatewayResourceInformation.from_charm(self)
        tls_information = TLSInformation.from_charm(self, self.certificates)
        self.unit.status = MaintenanceStatus("Creating resources.")
        resource_manager = GatewayResourceManager(
            labels=self._labels,
            client=client,
        )
        self._define_gateway_resource(
            resource_manager, gateway_resource_information, charm_config, tls_information
        )
        self._define_secret_resources(client, charm_config, tls_information)
        self._define_ingress_resources_and_publish_url(
            client, charm_config, gateway_resource_information
        )
        self._update_dns_record_relation(
            resource_manager, charm_config.external_hostname, gateway_resource_information
        )
        self._set_status_gateway_address(resource_manager, gateway_resource_information)

    def _update_dns_record_relation(
        self,
        resource_manager: GatewayResourceManager,
        external_hostname: str,
        gateway_resource_information: GatewayResourceInformation,
    ) -> None:
        """Update the DNS record relation with the external hostname and gateway address.

        Args:
            resource_manager: The Gateway resource manager to get the gateway address.
            external_hostname: The external hostname to be used in the DNS record.
            gateway_resource_information: Information needed to create the gateway resource.
        """
        relation = self.model.get_relation(self.dns_record_requirer.relation_name)
        if not relation or not external_hostname:
            return
        if not resource_manager.current_gateway_resource():
            logger.warning(
                "No gateway resource found, cannot update DNS record for %s",
                external_hostname,
            )
            return
        gateway_address = resource_manager.gateway_address(
            gateway_resource_information.gateway_name
        )
        if not gateway_address:
            logger.warning(
                "No gateway address found for %s, cannot update DNS record",
                external_hostname,
            )
            return
        # External hostname as a zone for now to get a simple solution for the DNS record.
        # In the future, we might want to support multiple zones.
        entry = RequirerEntry(
            domain=external_hostname,
            host_label="@",
            ttl=600,
            record_class=RecordClass.IN,
            record_type=RecordType.A,
            record_data=gateway_address,
            uuid=uuid.uuid5(UUID_NAMESPACE, str(external_hostname) + " " + str(gateway_address)),
        )
        dns_record_requirer_data = DNSRecordRequirerData(dns_entries=[entry])
        self.dns_record_requirer.update_relation_data(relation, dns_record_requirer_data)

    def _define_gateway_resource(
        self,
        resource_manager: GatewayResourceManager,
        gateway_resource_information: GatewayResourceInformation,
        config: CharmConfig,
        tls_information: TLSInformation,
    ) -> None:
        """Define the charm's gateway resource.

        Args:
            resource_manager: The Gateway resource manager to define the gateway resource.
            gateway_resource_information: Information needed to create the gateway resource.
            config: Charm config.
            tls_information: Information needed to create TLS secret resources.
        """
        resource_definition = GatewayResourceDefinition(
            gateway_resource_information, config, tls_information
        )
        gateway = resource_manager.define_resource(resource_definition)
        resource_manager.cleanup_resources(exclude=[gateway])

    def _define_secret_resources(
        self,
        client: Client,
        config: CharmConfig,
        tls_information: TLSInformation,
    ) -> None:
        """Define TLS secret resources.

        Args:
            client: Lightkube client.
            config: Charm config.
            tls_information: TLS-related information needed to create secret resources.
        """
        resource_definition = SecretResourceDefinition.from_tls_information(
            tls_information, config.external_hostname
        )
        resource_manager = TLSSecretResourceManager(
            labels=self._labels,
            client=client,
        )
        secret = resource_manager.define_resource(resource_definition)
        resource_manager.cleanup_resources(exclude=[secret])

    def _define_ingress_resources_and_publish_url(
        self,
        client: Client,
        config: CharmConfig,
        gateway_resource_information: GatewayResourceInformation,
    ) -> None:
        """Define ingress-relation resources and publish the ingress URL.

        Args:
            client: Lightkube client.
            config: Charm config.
            gateway_resource_information: Information needed to attach http_route resources.
        """
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
                http_route_resource_information.strip_prefix,
            )
        )
        https_route = http_route_resource_manager.define_resource(
            HTTPRouteResourceDefinition(
                http_route_resource_information,
                gateway_resource_information,
                HTTPRouteType.HTTPS,
                http_route_resource_information.strip_prefix,
            )
        )
        service_resource_manager.cleanup_resources(exclude=[service])
        http_route_resource_manager.cleanup_resources(exclude=[https_route, redirect_route])
        relation = self.model.get_relation(INGRESS_RELATION)
        self._ingress_provider.publish_url(
            relation,
            (
                f"https://{config.external_hostname}"
                f"/{http_route_resource_information.requirer_model_name}"
                f"-{http_route_resource_information.application_name}"
            ),
        )

    def _set_status_gateway_address(
        self,
        resource_manager: GatewayResourceManager,
        gateway_resource_information: GatewayResourceInformation,
    ) -> None:
        """Set the gateway address in the charm's status message.

        Args:
            resource_manager: The Gateway resource manager to get the gateway address.
            gateway_resource_information: Information about the created gateway resource.
        """
        self.unit.status = WaitingStatus("Waiting for gateway address")
        if gateway_address := resource_manager.gateway_address(
            gateway_resource_information.gateway_name
        ):
            self.unit.status = ActiveStatus(f"Gateway addresses: {gateway_address}")
        else:
            self.unit.status = WaitingStatus("Gateway address unavailable")

    def _certificates_revocation_needed(self, client: Client, config: CharmConfig) -> bool:
        """Check if a new certificate is needed.

        Args:
            client: Lightkube client
            config: Charm config.

        Returns:
            True if the current certificate needs to be revoked.
        """
        gateway_resource_manager = GatewayResourceManager(
            labels=self._labels,
            client=client,
        )
        gateway = gateway_resource_manager.current_gateway_resource()
        if not gateway:
            return False

        gateway_listeners = gateway.spec["listeners"]
        listener_hostnames = [listener["hostname"] for listener in gateway_listeners]
        if len(set(listener_hostnames)) == 1 and config.external_hostname == listener_hostnames[0]:
            return False

        return True


if __name__ == "__main__":  # pragma: no cover
    main(GatewayAPICharm)
