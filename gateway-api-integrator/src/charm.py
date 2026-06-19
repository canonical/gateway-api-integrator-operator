#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator charm file."""

import logging
import typing
import uuid
from collections.abc import Collection
from ipaddress import ip_address

from charmlibs.interfaces.tls_certificates import (
    CertificateAvailableEvent,
    CertificateRequestAttributes,
    Mode,
    TLSCertificatesRequiresV4,
)
from charms.bind.v0.dns_record import (
    DNSRecordRequirerData,
    DNSRecordRequires,
    RecordClass,
    RecordType,
    RequirerEntry,
)
from charms.gateway_api_integrator.v1.gateway_route import (
    GatewayRouteProvider,
    HttpsMode,
)
from charms.traefik_k8s.v2.ingress import (
    IngressPerAppDataProvidedEvent,
    IngressPerAppDataRemovedEvent,
    IngressPerAppProvider,
)
from lightkube import Client
from lightkube.core.client import LabelSelector
from lightkube.generic_resource import create_global_resource
from ops import BlockedStatus
from ops.charm import (
    ActionEvent,
    CharmBase,
    RelationChangedEvent,
    RelationCreatedEvent,
    RelationJoinedEvent,
)
from ops.main import main
from ops.model import ActiveStatus, MaintenanceStatus, WaitingStatus

from client import LightKubeInitializationError, get_client
from resource_manager.gateway import GatewayResourceDefinition, GatewayResourceManager
from resource_manager.http_route import (
    HTTPRouteResourceDefinition,
    HTTPRouteResourceManager,
    HTTPRouteType,
)
from resource_manager.permission import map_k8s_auth_exception
from resource_manager.secret import SecretResourceDefinition, TLSSecretResourceManager
from resource_manager.service import ServiceResourceDefinition, ServiceResourceManager
from state.charm_state import (
    GATEWAY_ROUTE_RELATION,
    INGRESS_RELATION,
    CharmState,
    ProxyMode,
)
from state.exception import CharmStateValidationBaseError, InvalidGatewayAddressError
from state.gateway import GatewayResourceInformation
from state.http_route import (
    HTTPRouteResourceInformation,
)
from state.tls import TLSInformation, TLSInformationNotReadyError
from state.validation import validate_config_and_integration

logger = logging.getLogger(__name__)
CREATED_BY_LABEL = "gateway-api-integrator.charm.juju.is/managed-by"
TLS_CERT_RELATION = "certificates"
# Randomly selected UUID namespace for generating UUID for DNS records.
UUID_NAMESPACE = uuid.UUID("f8f206da-a7f8-4206-b044-30be3724a09d")
CUSTOM_RESOURCE_GROUP_NAME = "gateway.networking.k8s.io"
GATEWAY_CLASS_RESOURCE_NAME = "GatewayClass"
GATEWAY_CLASS_PLURAL = "gatewayclasses"


class GatewayAPICharm(CharmBase):
    """The main charm class for the gateway-api-integrator charm."""

    def __init__(self, *args) -> None:  # type: ignore[no-untyped-def]
        """Init method for the class.

        Args:
            args: Variable list of positional arguments passed to the parent constructor.
        """
        super().__init__(*args)

        self._ingress_provider = IngressPerAppProvider(charm=self, relation_name=INGRESS_RELATION)
        self.dns_record_requirer = DNSRecordRequires(self)
        self._gateway_route_provider = GatewayRouteProvider(self, GATEWAY_ROUTE_RELATION)

        self.certificates = TLSCertificatesRequiresV4(
            charm=self,
            relationship_name=TLS_CERT_RELATION,
            certificate_requests=self._get_certificate_requests(),
            mode=Mode.APP,
            refresh_events=[
                self.on.config_changed,
                self._ingress_provider.on.data_provided,
                self._ingress_provider.on.data_removed,
                self.on[GATEWAY_ROUTE_RELATION].relation_joined,
                self.on[GATEWAY_ROUTE_RELATION].relation_changed,
            ],
        )

        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.start, self._on_start)

        self.framework.observe(
            self.on.certificates_relation_joined, self._on_certificates_relation_joined
        )
        self.framework.observe(
            self.on.certificates_relation_broken, self._on_certificates_relation_broken
        )
        self.framework.observe(
            self.certificates.on.certificate_available, self._on_certificate_available
        )

        self.framework.observe(self.on.get_certificate_action, self._on_get_certificate_action)

        self.framework.observe(self._ingress_provider.on.data_provided, self._on_data_provided)
        self.framework.observe(self._ingress_provider.on.data_removed, self._on_data_removed)

        self.framework.observe(
            self.on[GATEWAY_ROUTE_RELATION].relation_changed, self._on_gateway_route_changed
        )
        self.framework.observe(
            self.on[GATEWAY_ROUTE_RELATION].relation_broken, self._on_gateway_route_broken
        )
        self.framework.observe(
            self.on.dns_record_relation_created, self._on_dns_record_relation_created
        )
        self.framework.observe(
            self.on.dns_record_relation_joined, self._on_dns_record_relation_joined
        )

    def _get_certificate_requests(self) -> list[CertificateRequestAttributes]:
        """Get certificate requests from charm state hostnames.

        Returns:
            List of certificate request attributes for hostnames in charm state,
            or empty list if charm state initialization fails.
        """
        try:
            charm_state = CharmState.from_charm_and_providers(
                self,
                self.available_gateway_classes(),
                self._ingress_provider,
                self._gateway_route_provider,
            )
            csrs = [
                CertificateRequestAttributes(common_name=hostname, sans_dns=[hostname])
                for hostname in sorted(charm_state.hostnames)
            ]
            if charm_state.requires_ip_certificate:
                gateway_address = self._current_gateway_address()
                if gateway_address:
                    csrs.append(
                        CertificateRequestAttributes(
                            common_name=gateway_address, sans_ip=[gateway_address]
                        )
                    )
            return csrs
        except CharmStateValidationBaseError as e:
            logger.warning(
                "Failed to initialize charm state, skipping certificate requests: %s", str(e)
            )
            return []

    def _current_gateway_address(self) -> str | None:
        """Get the current gateway IPv4 address.

        This is used when calculating certificate requests to include an IP SAN
        target only when an address is already known.
        """
        try:
            client = get_client(field_manager=self.app.name, namespace=self.model.name)
        except LightKubeInitializationError:
            return None

        gateway_resource_manager = GatewayResourceManager(self._labels, client)
        if not gateway_resource_manager.current_gateway_resource():
            return None

        gateway_resource_information = GatewayResourceInformation.from_charm(self)
        try:
            return gateway_resource_manager.gateway_address(
                gateway_resource_information.gateway_name
            )
        except InvalidGatewayAddressError:
            return None

    @property
    def _labels(self) -> LabelSelector:
        """Get labels assigned to resources created by this app."""
        return {CREATED_BY_LABEL: self.app.name}

    @validate_config_and_integration(defer=False)
    def _on_config_changed(self, _: typing.Any) -> None:
        """Handle the config-changed event."""
        self._reconcile()

    @validate_config_and_integration(defer=False)
    def _on_certificates_relation_joined(self, _: typing.Any) -> None:
        """Handle the certificates-relation-joined event."""
        self._reconcile()

    @validate_config_and_integration(defer=False)
    def _on_certificates_relation_broken(self, _: typing.Any) -> None:
        """Handle the certificates-relation-broken event."""
        self._reconcile()

    @validate_config_and_integration(defer=False)
    def _on_start(self, _: typing.Any) -> None:
        """Handle the start event."""
        self._reconcile()

    @validate_config_and_integration(defer=False)
    def _on_get_certificate_action(self, event: ActionEvent) -> None:
        """Triggered when users run the `get-certificate` Juju action.

        Args:
            event: Juju event
        """
        if not self.model.get_relation(TLS_CERT_RELATION):
            event.fail("Certificate relation not ready.")

        hostname = event.params["hostname"]
        provider_certificates = self.certificates.get_provider_certificates()
        for certificate in provider_certificates:
            if certificate.certificate.common_name == hostname:
                event.set_results(
                    {
                        "certificate": str(certificate.certificate),
                        "ca": str(certificate.ca),
                        "chain": "\n\n".join(str(cert) for cert in certificate.chain),
                    }
                )
                return
        event.fail(f"Missing or incomplete certificate data for {hostname}")

    @validate_config_and_integration(defer=False)
    def _on_certificate_available(self, _: CertificateAvailableEvent) -> None:
        """Handle the TLS Certificate available event."""
        logger.info("TLS certificate available, creating resources.")
        self._reconcile()

    @validate_config_and_integration(defer=False)
    def _on_data_provided(self, _: IngressPerAppDataProvidedEvent) -> None:
        """Handle the data-provided event."""
        self._reconcile()

    @validate_config_and_integration(defer=False)
    def _on_data_removed(self, _: IngressPerAppDataRemovedEvent) -> None:
        """Handle the data-removed event."""
        self._reconcile()

    @validate_config_and_integration(defer=False)
    def _on_gateway_route_changed(self, _: RelationChangedEvent) -> None:
        """Handle the gateway-route relation-changed event."""
        self._reconcile()

    @validate_config_and_integration(defer=False)
    def _on_gateway_route_broken(self, _: typing.Any) -> None:
        """Handle the gateway-route relation-broken event."""
        self._reconcile()

    @validate_config_and_integration(defer=False)
    def _on_dns_record_relation_created(self, _: RelationCreatedEvent) -> None:
        """Handle the DNS record relation created event."""
        self._reconcile()

    @validate_config_and_integration(defer=False)
    def _on_dns_record_relation_joined(self, _: RelationJoinedEvent) -> None:
        """Handle the DNS record relation joined event."""
        self._reconcile()

    def _determine_https_mode(self, enforce_https: bool, has_tls_relation: bool) -> HttpsMode:
        """Determine the HTTPS mode based on config and TLS relation presence."""
        if enforce_https:
            return HttpsMode.ENFORCED
        return HttpsMode.ENABLED if has_tls_relation else HttpsMode.DISABLED

    def _reconcile(self) -> None:
        """Reconcile charm status based on configuration and integrations.

        Actions performed in this method:
            1. Initialize charm state components.
            2. Create the gateway and secret resources.
            3. For ingress relation: create HTTPRoute and Gateway resources.
            4. For gateway-route relations: publish provider data via gateway-route relation.
            5. Update the DNS record relation with the DNS record data.
            6. Set the gateway LB address in the charm's status message.
        """
        if not self.unit.is_leader():
            self.unit.status = BlockedStatus("Deploying more than one unit is not supported.")
            return

        self.unit.status = MaintenanceStatus("Creating resources.")

        # Validate/parse TLS information and create TLS secret resources.
        client = get_client(field_manager=self.app.name, namespace=self.model.name)
        charm_state = CharmState.from_charm_and_providers(
            self,
            self.available_gateway_classes(),
            self._ingress_provider,
            self._gateway_route_provider,
        )

        has_tls_relation = self.model.get_relation(TLS_CERT_RELATION) is not None

        gateway_resource_information = GatewayResourceInformation.from_charm(self)
        gateway_resource_manager = GatewayResourceManager(
            labels=self._labels,
            client=client,
        )

        gateway_address = None
        if (
            charm_state.requires_ip_certificate
            and gateway_resource_manager.current_gateway_resource()
        ):
            gateway_address = gateway_resource_manager.gateway_address(
                gateway_resource_information.gateway_name
            )

        tls_information = None
        tls_not_ready = False
        if has_tls_relation:
            try:
                tls_information = TLSInformation.from_charm(
                    self, charm_state.hostnames, self.certificates, gateway_address
                )
            except TLSInformationNotReadyError as exc:
                logger.info("TLS certificates not ready yet: %s", str(exc))
                tls_not_ready = True

        self._define_secret_resources(client, tls_information)

        # Define gateway resource.
        self._define_gateway_resource(
            gateway_resource_manager,
            gateway_resource_information,
            charm_state,
            tls_information,
        )

        # Remove ingress resources when operating in any non-ingress mode.
        if charm_state.proxy_mode != ProxyMode.INGRESS:
            HTTPRouteResourceManager(self._labels, client).cleanup_resources(exclude=[])
            ServiceResourceManager(self._labels, client).cleanup_resources(exclude=[])

        # Handle mode-specific logic
        if charm_state.proxy_mode == ProxyMode.INGRESS:
            self._define_ingress_resources_and_publish_url(
                client,
                charm_state,
                tls_information,
                gateway_resource_information,
                gateway_resource_manager,
            )
        elif charm_state.proxy_mode == ProxyMode.GATEWAY_ROUTE:
            self._reconcile_gateway_route(
                client,
                charm_state,
                has_tls_relation,
                gateway_resource_information,
                gateway_resource_manager,
            )

        # Update DNS record relation with the gateway address for all hostnames.
        self._update_dns_record_relation(
            gateway_resource_manager,
            gateway_resource_information,
            charm_state.hostnames,
        )

        self._set_status_gateway_address(
            gateway_resource_manager,
            gateway_resource_information,
            charm_state.enforce_https,
        )

        if tls_not_ready:
            self.unit.status = WaitingStatus("Waiting for TLS certificates to be issued.")

    def _reconcile_gateway_route(
        self,
        client: Client,
        charm_state: CharmState,
        has_tls_relation: bool,
        gateway_resource_information: GatewayResourceInformation,
        gateway_resource_manager: GatewayResourceManager,
    ) -> None:
        """Publish provider data for gateway-route relations when gateway address is ready."""
        # Refresh the set of valid relations to publish to.
        self._gateway_route_provider.get_requirer_data()

        https_mode = self._determine_https_mode(charm_state.enforce_https, has_tls_relation)

        # Readiness gate: publish only when the gateway has an address.
        if not gateway_resource_manager.current_gateway_resource():
            return

        gateway_address = gateway_resource_manager.gateway_address(
            gateway_resource_information.gateway_name
        )
        if gateway_address is None:
            return

        self._gateway_route_provider.publish_provider_data(
            gateway_name=gateway_resource_information.gateway_name,
            gateway_model=self.model.name,
            https_mode=https_mode,
            gateway_address=gateway_address,
        )

    def _update_dns_record_relation(
        self,
        resource_manager: GatewayResourceManager,
        gateway_resource_information: GatewayResourceInformation,
        hostnames: Collection[str],
    ) -> None:
        """Update the DNS record relation with DNS records for all managed hostnames.

        Args:
            resource_manager: The Gateway resource manager to get the gateway address.
            gateway_resource_information: Information needed to create the gateway resource.
            hostnames: Hostnames to publish as DNS records.
        """
        relation = self.model.get_relation(self.dns_record_requirer.relation_name)
        if not relation:
            return

        sorted_hostnames = sorted(hostnames)
        if not sorted_hostnames:
            return

        if not resource_manager.current_gateway_resource():
            logger.warning(
                "No gateway resource found, cannot update DNS records",
            )
            return
        gateway_address = resource_manager.gateway_address(
            gateway_resource_information.gateway_name
        )
        if not gateway_address:
            logger.warning(
                "No gateway address found, cannot update DNS records",
            )
            return

        # Create DNS entries for each hostname
        entries = []
        for hostname in sorted_hostnames:
            entry = RequirerEntry(
                domain=hostname,
                host_label="@",
                ttl=600,
                record_class=RecordClass.IN,
                record_type=RecordType.A,
                record_data=ip_address(gateway_address),
                uuid=uuid.uuid5(UUID_NAMESPACE, str(hostname) + " " + str(gateway_address)),
            )
            entries.append(entry)

        dns_record_requirer_data = DNSRecordRequirerData(dns_entries=entries)
        self.dns_record_requirer.update_relation_data(relation, dns_record_requirer_data)

    def _define_gateway_resource(
        self,
        resource_manager: GatewayResourceManager,
        gateway_resource_information: GatewayResourceInformation,
        charm_state: CharmState,
        tls_information: TLSInformation | None,
    ) -> None:
        """Define the charm's gateway resource.

        Args:
            resource_manager: The Gateway resource manager to define the gateway resource.
            gateway_resource_information: Information needed to create the gateway resource.
            charm_state: Charm state.
            tls_information: Information needed to create TLS secret resources.
        """
        resource_definition = GatewayResourceDefinition(
            gateway_resource_information, charm_state, tls_information
        )
        gateway = resource_manager.define_resource(resource_definition)
        resource_manager.cleanup_resources(exclude=[gateway])

    def _define_secret_resources(
        self,
        client: Client,
        tls_information: TLSInformation | None,
    ) -> None:
        """Define TLS secret resources.

        Args:
            client: Lightkube client.
            tls_information: TLS-related information needed to create secret resources.
        """
        resource_manager = TLSSecretResourceManager(
            labels=self._labels,
            client=client,
        )

        if tls_information is None:
            # Clean up any existing secrets if we're not rendering the HTTPS listener.
            resource_manager.cleanup_resources(exclude=[])
            return

        # Create a secret for each hostname
        managed_secrets = []
        for hostname in tls_information.hostnames:
            resource_definition = SecretResourceDefinition.from_tls_information(
                tls_information, hostname
            )
            secret = resource_manager.define_resource(resource_definition)
            managed_secrets.append(secret)
        resource_manager.cleanup_resources(exclude=managed_secrets)

    def _define_ingress_resources_and_publish_url(
        self,
        client: Client,
        charm_state: CharmState,
        tls_information: TLSInformation | None,
        gateway_resource_information: GatewayResourceInformation,
        gateway_resource_manager: GatewayResourceManager,
    ) -> None:
        """Define ingress-relation resources and publish the ingress URL.

        Args:
            client: Lightkube client.
            charm_state: Charm state.
            tls_information: TLS information state component.
            gateway_resource_information: Information needed to attach http_route resources.
            gateway_resource_manager: Gateway resource manager.
        """
        hostname = next(iter(charm_state.hostnames), None)
        http_route_resource_information = HTTPRouteResourceInformation.from_ingress(
            self._ingress_provider, hostname
        )

        http_route_resource_manager = HTTPRouteResourceManager(self._labels, client)
        # If HTTPS is enforced, create 2 HTTPRoute resources for "HTTP" (redirect) and "HTTPS".
        # If HTTPS is not enforced but TLS is configured, create both "HTTP" and "HTTPS" HTTPRoute resources.
        # If HTTPS is not enforced and no TLS, only create the "HTTP" HTTPRoute resource.
        http_route_resources = []
        ingress_base_url = None
        if charm_state.enforce_https:
            if hostname:
                ingress_base_url = f"https://{hostname}"
            # When HTTPS is enforced, create both redirect and HTTPS routes
            http_route_resources = [
                HTTPRouteResourceDefinition(
                    http_route_resource_information,
                    gateway_resource_information,
                    HTTPRouteType.HTTP,
                    redirect_https=True,
                ),
                HTTPRouteResourceDefinition(
                    http_route_resource_information,
                    gateway_resource_information,
                    HTTPRouteType.HTTPS,
                ),
            ]
        else:
            if tls_information is not None and hostname:
                ingress_base_url = f"https://{hostname}"
            elif gateway_address := gateway_resource_manager.gateway_address(
                gateway_resource_information.gateway_name
            ):
                ingress_base_url = f"http://{gateway_address}"
            else:
                logger.warning("Gateway address not found.")
            http_route_resources = [
                HTTPRouteResourceDefinition(
                    http_route_resource_information,
                    gateway_resource_information,
                    HTTPRouteType.HTTP,
                    redirect_https=False,
                ),
            ]
            if tls_information is not None:
                http_route_resources.append(
                    HTTPRouteResourceDefinition(
                        http_route_resource_information,
                        gateway_resource_information,
                        HTTPRouteType.HTTPS,
                    )
                )
        managed_http_route_resources = [
            http_route_resource_manager.define_resource(http_route_resource)
            for http_route_resource in http_route_resources
        ]
        http_route_resource_manager.cleanup_resources(exclude=managed_http_route_resources)

        # Define service resource.
        service_resource_manager = ServiceResourceManager(self._labels, client)
        service = service_resource_manager.define_resource(
            ServiceResourceDefinition(http_route_resource_information)
        )
        service_resource_manager.cleanup_resources(exclude=[service])
        self._publish_ingress_url(
            ingress_base_url,
            http_route_resource_information,
        )

    def _publish_ingress_url(
        self,
        ingress_base_url: str | None,
        http_route_resource_information: HTTPRouteResourceInformation,
    ) -> None:
        """Publish the ingress URL to the requirer charm.

        Args:
            ingress_base_url: The base URL to publish.
            http_route_resource_information: Information needed to create HTTPRoute resources.
        """
        if not ingress_base_url:
            logger.warning("Cannot determine base URL, skipping publish.")
            return

        ingress_relation = self.model.get_relation(INGRESS_RELATION)
        if ingress_relation:
            ingress_url = (
                f"{ingress_base_url}"
                f"/{http_route_resource_information.requirer_model_name}"
                f"-{http_route_resource_information.application_name}"
            )

            self._ingress_provider.publish_url(
                ingress_relation,
                ingress_url,
            )

    def _set_status_gateway_address(
        self,
        resource_manager: GatewayResourceManager,
        gateway_resource_information: GatewayResourceInformation,
        enforce_https: bool,
    ) -> None:
        """Set the gateway address in the charm's status message.

        Args:
            resource_manager: The Gateway resource manager to get the gateway address.
            gateway_resource_information: Information about the created gateway resource.
            enforce_https: Whether HTTPS enforcement is enabled.
        """
        # Surface the conscious choice of disabling HTTPS enforcement to the user.
        enforce_https_note = "" if enforce_https else " (enforce-https is set to false)"

        self.unit.status = WaitingStatus("Waiting for gateway address")
        if gateway_address := resource_manager.gateway_address(
            gateway_resource_information.gateway_name
        ):
            self.unit.status = ActiveStatus(
                f"Gateway addresses: {gateway_address}{enforce_https_note}"
            )
        else:
            self.unit.status = WaitingStatus("Gateway address unavailable")

    @map_k8s_auth_exception
    def available_gateway_classes(self) -> list[str]:
        """Get the list of available gateway classes on the cluster.

        Returns:
            A list of available gateway class names.
        """
        client = get_client(field_manager=self.app.name, namespace=self.model.name)
        gateway_class_generic_resource = create_global_resource(
            CUSTOM_RESOURCE_GROUP_NAME, "v1", GATEWAY_CLASS_RESOURCE_NAME, GATEWAY_CLASS_PLURAL
        )
        gateway_classes = tuple(client.list(gateway_class_generic_resource))

        return [
            gateway_class.metadata.name
            for gateway_class in gateway_classes
            if gateway_class.metadata and gateway_class.metadata.name
        ]


if __name__ == "__main__":  # pragma: no cover
    main(GatewayAPICharm)
