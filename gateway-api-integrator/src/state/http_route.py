# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator ingress charm state component."""

import dataclasses

import ops
from charms.gateway_api_integrator.v0.gateway_route import GatewayRouteProvider
from charms.traefik_k8s.v2.ingress import DataValidationError, IngressPerAppProvider

from .exception import CharmStateValidationBaseError

INGRESS_RELATION = "gateway"
GATEWAY_ROUTE_RELATION = "gateway-route"


class IngressIntegrationMissingError(CharmStateValidationBaseError):
    """Exception raised when ingress integration is not established."""


class IngressIntegrationDataValidationError(CharmStateValidationBaseError):
    """Exception raised when ingress integration is not established."""


@dataclasses.dataclass(frozen=True)
class HTTPRouteResourceInformation:
    """A component of charm state containing resource definition for kubernetes secret.

    Attrs:
        application_name: The name of the application we're providing routing to.
        requirer_model_name: The name of the requirer model.
        service_name: The name of the service we're creating.
        service_port: The port of the service.
        service_port_name: The port name of the service.
        strip_prefix: Whether to strip the generated prefix.
        integration: The type of integration, can be ingress or gateway-api.
        paths: The list of paths to be added to the HTTPRoute resource.
        hostname: The hostname to be used in the HTTPRoute resource.
    """

    application_name: str
    requirer_model_name: str
    service_name: str
    service_port: int
    service_port_name: str
    strip_prefix: bool
    integration: str
    paths: list[str]
    hostname: str

    @classmethod
    def from_charm(
        cls,
        charm: ops.CharmBase,
        ingress_provider: IngressPerAppProvider,
        gateway_route_provider: GatewayRouteProvider,
    ) -> "HTTPRouteResourceInformation":
        """Get TLS information from a charm instance.

        Args:
            charm (ops.CharmBase): The gateway-api-integrator charm.
            ingress_provider (IngressPerAppProvider): The ingress provider library.
            gateway_route_provider (GatewayRouteProvider): The gateway route provider library.


        Raises:
            IngressIntegrationMissingError: When integration is not ready.
            IngressIntegrationDataValidationError: When data validation failed.

        Returns:
            HTTPRouteResourceInformation: Information about configured TLS certs.
        """
        ingress_integration = charm.model.get_relation(INGRESS_RELATION)
        gateway_route_integration = charm.model.get_relation(GATEWAY_ROUTE_RELATION)
        if ingress_integration is None and gateway_route_integration is None:
            raise IngressIntegrationMissingError(
                "Ingress and Gateway Route integration not ready." + " You must relate to either."
            )
        try:
            if ingress_integration:
                integration_data = ingress_provider.get_data(ingress_integration)
                integration = "ingress"
                paths = []
                hostname = ""
            else:
                integration_data = gateway_route_provider.get_data(gateway_route_integration)
                integration = GATEWAY_ROUTE_RELATION
                paths = integration_data.app.paths
                hostname = integration_data.app.hostname
            application_name = integration_data.app.name
            requirer_model_name = integration_data.app.model
            service_name = f"{charm.app.name}-{application_name}-service"
            service_port = integration_data.app.port
            service_port_name = f"tcp-{service_port}"
            strip_prefix = integration_data.app.strip_prefix

            return cls(
                application_name=application_name,
                requirer_model_name=requirer_model_name,
                service_name=service_name,
                service_port=service_port,
                service_port_name=service_port_name,
                strip_prefix=strip_prefix,
                integration=integration,
                paths=paths,
                hostname=hostname,
            )
        except DataValidationError as exc:
            raise IngressIntegrationDataValidationError(
                "Validation of ingress relation data failed."
            ) from exc
