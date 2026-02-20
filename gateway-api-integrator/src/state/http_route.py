# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator ingress charm state component."""

import dataclasses

from charms.gateway_api_integrator.v0.gateway_route import GatewayRouteProvider
from charms.traefik_k8s.v2.ingress import DataValidationError, IngressPerAppProvider

from state.tls import TLSInformation

from .exception import CharmStateValidationBaseError

INGRESS_RELATION = "gateway"
GATEWAY_ROUTE_RELATION = "gateway-route"


class IngressIntegrationMissingError(CharmStateValidationBaseError):
    """Exception raised when ingress relation is not established."""


class IngressIntegrationDataValidationError(CharmStateValidationBaseError):
    """Exception raised when ingress relation data validation fails."""


class GatewayRouteRelationNotReadyError(CharmStateValidationBaseError):
    """Exception raised when gateway route relation data is not ready."""


class GatewayRouteRelationDataValidationError(CharmStateValidationBaseError):
    """Exception raised when gateway route relation data validation fails."""


@dataclasses.dataclass(frozen=True)
class HTTPRouteResourceInformation:
    """A component of charm state containing resource definition for kubernetes secret.

    Attrs:
        application_name: The name of the application we're providing routing to.
        requirer_model_name: The name of the requirer model.
        service_name: The name of the service we're creating.
        service_port: The port of the service.
        service_port_name: The port name of the service.
        filters: The list of filters to be applied to the HTTPRoute resource.
        paths: The list of paths to be added to the HTTPRoute resource.
        hostname: The hostname to be used in the HTTPRoute resource.
    """

    application_name: str
    requirer_model_name: str
    service_name: str
    service_port: int
    service_port_name: str
    filters: list[dict]
    paths: list[str]
    hostname: str | None

    @classmethod
    def _from_ingress(
        cls,
        ingress_provider: IngressPerAppProvider,
        hostname: str | None,
    ) -> "HTTPRouteResourceInformation":
        """Populate fields from ingress integration.

        Args:
            charm (ops.CharmBase): The gateway-api-integrator charm.
            ingress_provider (IngressPerAppProvider): The ingress provider class.
            hostname: The hostname to be used in the HTTPRoute resource.
        """
        try:
            integration_data = ingress_provider.get_data(ingress_provider.relations[0])
            application_name = integration_data.app.name
            service_port = integration_data.app.port
            service_name = f"{ingress_provider.charm.app.name}-{application_name}-service"
            return cls(
                application_name=application_name,
                requirer_model_name=integration_data.app.model,
                service_name=service_name,
                service_port=service_port,
                service_port_name=f"tcp-{service_port}",
                filters=(
                    []
                    if not integration_data.app.strip_prefix
                    else [
                        {
                            "type": "URLRewrite",
                            "urlRewrite": {
                                "path": {
                                    "type": "ReplacePrefixMatch",
                                    "replacePrefixMatch": "/",
                                }
                            },
                        }
                    ]
                ),
                paths=[f"/{integration_data.app.model}-{application_name}"],
                hostname=hostname,
            )
        except DataValidationError as exc:
            raise IngressIntegrationDataValidationError(
                "Validation of ingress relation data failed."
            ) from exc

    @classmethod
    def _from_gateway_route(
        cls,
        gateway_route_provider: GatewayRouteProvider,
        hostname: str | None,
    ) -> "HTTPRouteResourceInformation":
        """Populate fields from ingress integration.

        Args:
            gateway_route_provider: The gateway route provider library.
            hostname: The hostname to be used in the HTTPRoute resource.

        Raises:
            GatewayRouteRelationDataValidationError: When data validation failed.
            GatewayRouteHostnameMissingError: When hostname is not configured.
        """
        relation_data = gateway_route_provider.get_data()
        if relation_data is None:
            raise GatewayRouteRelationNotReadyError("gateway-route relation data not ready.")
        application_name = relation_data.application_data.name
        service_port = relation_data.application_data.port
        try:
            return cls(
                application_name=application_name,
                requirer_model_name=relation_data.application_data.model,
                service_name=f"{gateway_route_provider.charm.app.name}-{application_name}-service",
                service_port=service_port,
                service_port_name=f"tcp-{service_port}",
                filters=[],
                paths=relation_data.application_data.paths,
                hostname=hostname,
            )
        except DataValidationError as exc:
            raise GatewayRouteRelationDataValidationError(
                "Validation of gateway-route relation data failed."
            ) from exc
