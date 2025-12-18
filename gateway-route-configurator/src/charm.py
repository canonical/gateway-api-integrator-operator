#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Gateway Route Configurator Charm."""

import logging
import re
import typing

import ops
from charms.gateway_api_integrator.v0.gateway_route import (
    DataValidationError as GatewayRouteDataValidationError,
)
from charms.gateway_api_integrator.v0.gateway_route import GatewayRouteRequirer
from charms.traefik_k8s.v2.ingress import DataValidationError, IngressPerAppProvider

logger = logging.getLogger(__name__)

HOSTNAME_REGEX = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*$")


class GatewayRouteConfiguratorCharm(ops.CharmBase):
    """Charm the service."""

    def __init__(self, *args: typing.Any):
        """Init method for the class.

        Args:
            args: Variable list of positional arguments passed to the parent constructor.
        """
        super().__init__(*args)

        self.ingress = IngressPerAppProvider(self, relation_name="ingress")
        self.gateway_route: typing.Optional[GatewayRouteRequirer] = None

        self.framework.observe(self.on.config_changed, self._on_update)
        self.framework.observe(self.ingress.on.data_provided, self._on_update)
        self.framework.observe(self.ingress.on.data_removed, self._on_update)
        self.unit.status = ops.MaintenanceStatus("Configuring gateway route")
        self.setup_gateway_route()

    def setup_gateway_route(self) -> None:
        """Set up the Gateway Route Requirer based on ingress data and config."""
        hostname = str(self.model.config.get("hostname"))
        paths_str = str(self.model.config.get("paths", "/"))
        paths = [p.strip() for p in paths_str.split(",")]
        try:
            if not self.ingress.relations:
                self.unit.status = ops.WaitingStatus("Waiting for ingress relation")
                return

            data = self.ingress.get_data(self.ingress.relations[0])

            application_name = data.app.name
            model_name = data.app.model
            port = data.app.port

            self.gateway_route = GatewayRouteRequirer(
                self,
                relation_name="gateway-route",
                name=application_name,
                model=model_name,
                port=port,
                paths=paths,
                hostname=hostname,
            )
            self.framework.observe(self.gateway_route.on.ready, self._on_update)
            self.framework.observe(self.gateway_route.on.removed, self._on_update)
            self.unit.status = ops.ActiveStatus("Ready")
        except GatewayRouteDataValidationError as e:
            logger.exception("Failed to set route configuration")
            self.unit.status = ops.BlockedStatus(f"Error sending config: {e}")
        except DataValidationError:
            self.unit.status = ops.BlockedStatus("Invalid ingress data")

    def _on_update(self, _: typing.Any) -> None:
        """Handle updates to config or relations."""
        hostname = str(self.model.config.get("hostname"))

        if not hostname:
            self.unit.status = ops.BlockedStatus("Missing 'hostname' config")
            return

        if not HOSTNAME_REGEX.match(hostname):
            self.unit.status = ops.BlockedStatus(f"Invalid hostname: {hostname}")
            return

        # 2. Get Ingress Data
        ingress_relation = self.model.get_relation("ingress")
        if not ingress_relation:
            self.unit.status = ops.BlockedStatus("Missing 'ingress' relation")
            return


if __name__ == "__main__":  # pragma: nocover
    ops.main.main(GatewayRouteConfiguratorCharm)
