# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator ingress charm state component."""

import dataclasses

import ops
from charms.traefik_k8s.v2.ingress import DataValidationError, IngressPerAppProvider

from exception import CharmStateValidationBaseError

INGRESS_RELATION = "gateway"


class IngressIntegrationMissingError(CharmStateValidationBaseError):
    """Exception raised when ingress integration is not established."""


class IngressIntegrationDataValidationError(CharmStateValidationBaseError):
    """Exception raised when ingress integration is not established."""


@dataclasses.dataclass(frozen=True)
class HTTPRouteResourceDefinition:
    """A component of charm state containing resource definition for kubernetes secret.

    Attrs:
        service_name: The name of the service we're providing routing to.
        service_port: The port of the service we're providing routing to.
        service_port_name: The port name of the service we're providing routing to.
        endpoints: Upstream endpoint ip addresses, only in ingress v2 relation.
    """

    service_name: str
    service_port: int
    service_port_name: str
    endpoints: list[str]

    @classmethod
    def from_charm(
        cls, charm: ops.CharmBase, ingress_provider: IngressPerAppProvider
    ) -> "HTTPRouteResourceDefinition":
        """Get TLS information from a charm instance.

        Args:
            charm (ops.CharmBase): The gateway-api-integrator charm.
            ingress_provider (IngressPerAppProvider): The ingress provider library.


        Raises:
            IngressIntegrationMissingError: When integration is not ready.
            IngressIntegrationDataValidationError: When data validation failed.

        Returns:
            HTTPRouteResourceDefinition: Information about configured TLS certs.
        """
        ingress_integration = charm.model.get_relation(INGRESS_RELATION)
        if ingress_integration is None:
            raise IngressIntegrationMissingError("Ingress integration not ready.")
        try:
            integration_data = ingress_provider.get_data(ingress_integration)
            service_name = integration_data.app.name
            service_port = integration_data.app.port
            service_port_name = f"tcp-{service_port}"

            endpoints = [u.ip for u in integration_data.units if u.ip is not None]
            return cls(
                service_name=service_name,
                service_port=service_port,
                service_port_name=service_port_name,
                endpoints=endpoints,
            )
        except DataValidationError as exc:
            raise IngressIntegrationDataValidationError(
                "Validation of ingress relation data failed."
            ) from exc
