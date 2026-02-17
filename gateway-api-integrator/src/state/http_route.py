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


class IngressGatewayRouteConflictError(CharmStateValidationBaseError):
    """Exception raised when both ingress and gateway-route integrations are established."""


class GatewayRouteHostnameMissingError(CharmStateValidationBaseError):
    """Exception raised when hostname not configured in gateway-route mode.

    Hostname is configured either via the gateway-route relation or by setting external-hostname.
    """


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
    hostname: str

    @classmethod
    def from_provider(
        cls,
        external_hostname: str | None,
        ingress_provider: IngressPerAppProvider,
        gateway_route_provider: GatewayRouteProvider,
    ) -> "HTTPRouteResourceInformation":
        """Get TLS information from a charm instance.

        Args:
            external_hostname: The external-hostname charm configuration.
            ingress_provider: The ingress provider library.
            gateway_route_provider: The gateway route provider library.

        Raises:
            IngressIntegrationMissingError: When integration is not ready.
            IngressIntegrationDataValidationError: When data validation failed.
            IngressGatewayRouteConflictError: When both integrations are established.

        Returns:
            HTTPRouteResourceInformation: Information about configured TLS certs.
        """
        ingress_relations = ingress_provider.relations
        gateway_route_relation = gateway_route_provider.relation
        if ingress_relations and gateway_route_relation is not None:
            raise IngressGatewayRouteConflictError(
                "Both Ingress and Gateway Route integrations are established. Only one is allowed."
            )
        try:
            if ingress_relations:
                if len(ingress_relations) > 1:
                    raise IngressIntegrationDataValidationError(
                        "The charm does not support multiple ingress relations."
                    )
                return cls._from_ingress(ingress_provider)
            if gateway_route_relation is not None:
                return cls._from_gateway_route(
                    external_hostname, gateway_route_provider, gateway_route_relation
                )
        except DataValidationError as exc:
            raise IngressIntegrationDataValidationError(
                "Validation of ingress relation data failed."
            ) from exc
        raise IngressIntegrationMissingError(
            "Ingress and Gateway Route integration not ready. You must relate to either."
        )

    @classmethod
    def _from_ingress(
        cls,
        ingress_provider: IngressPerAppProvider,
    ) -> "HTTPRouteResourceInformation":
        """Populate fields from ingress integration.

        Args:
            charm (ops.CharmBase): The gateway-api-integrator charm.
            ingress_provider (IngressPerAppProvider): The ingress provider class.
            ingress_integration (ops.Relation): The ingress integration.
        """
        # Validation that len(ingress_provider.relations) == 1 is done in the caller method
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
            hostname="",
        )

    @classmethod
    def _from_gateway_route(
        cls,
        external_hostname: str | None,
        gateway_route_provider: GatewayRouteProvider,
        gateway_route_integration: ops.Relation,
    ) -> "HTTPRouteResourceInformation":
        """Populate fields from ingress integration.

        Args:
            external_hostname: The external-hostname charm configuration.
            gateway_route_provider: The gateway route provider library.
            gateway_route_integration: The gateway-route integration.
        """
        integration_data = gateway_route_provider.get_data(gateway_route_integration)
        if integration_data is None:
            raise IngressIntegrationMissingError("Gateway Route integration data not ready.")
        application_name = integration_data.application_data.name
        service_port = integration_data.application_data.port
        hostname = integration_data.application_data.hostname or external_hostname
        if hostname is None:
            raise IngressIntegrationDataValidationError(
                "No hostname configured. Configure hostname either via"
                " the gateway-route relation or by setting the external-hostname charm config."
            )
        return cls(
            application_name=application_name,
            requirer_model_name=integration_data.application_data.model,
            service_name=f"{gateway_route_provider.charm.app.name}-{application_name}-service",
            service_port=service_port,
            service_port_name=f"tcp-{service_port}",
            filters=[],
            paths=integration_data.application_data.paths,
            hostname=hostname,
        )
