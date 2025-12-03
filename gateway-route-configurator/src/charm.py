#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Gateway Route Configurator Charm."""

import logging
import re
import typing

import ops
from charms.gateway_api_integrator.v0.gateway_route import GatewayRouteRequires
from charms.traefik_k8s.v2.ingress import DataValidationError, IngressPerAppProvider

logger = logging.getLogger(__name__)

HOSTNAME_REGEX = re.compile(
    r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*$"
)


class GatewayRouteConfiguratorCharm(ops.CharmBase):
    """Charm the service."""

    def __init__(self, *args: typing.Any):
        super().__init__(*args)

        self.ingress = IngressPerAppProvider(self, relation_name="ingress")
        self.gateway_route = GatewayRouteRequires(self, relation_name="gateway-route")

        self.framework.observe(self.on.config_changed, self._on_update)
        self.framework.observe(self.ingress.on.data_provided, self._on_update)
        self.framework.observe(self.ingress.on.data_removed, self._on_update)
        self.framework.observe(self.on.gateway_route_relation_joined, self._on_update)
        self.framework.observe(self.on.gateway_route_relation_changed, self._on_update)

    def _on_update(self, _):
        """Handle updates to config or relations."""
        self.unit.status = ops.MaintenanceStatus("Configuring gateway route")

        # 1. Get Config
        hostname = self.model.config.get("hostname")
        paths_str = self.model.config.get("paths", "/")

        if not hostname:
            self.unit.status = ops.BlockedStatus("Missing 'hostname' config")
            return

        if not HOSTNAME_REGEX.match(hostname):
             self.unit.status = ops.BlockedStatus(f"Invalid hostname: {hostname}")
             return

        paths = [p.strip() for p in paths_str.split(",")]

        # 2. Get Ingress Data
        ingress_relation = self.model.get_relation("ingress")
        if not ingress_relation:
            self.unit.status = ops.BlockedStatus("Missing 'ingress' relation")
            return

        try:
            # We assume single app relation for now
            if not self.ingress.relations:
                 self.unit.status = ops.WaitingStatus("Waiting for ingress relation")
                 return

            # Use the first relation that has data
            # IngressPerAppProvider.get_data returns IngressRequirerAppData
            # But get_data takes a relation object.
            # We need to iterate over relations and find one with data.

            # Note: IngressPerAppProvider usually handles multiple relations.
            # We should probably aggregate or just pick one.
            # The spec implies this charm sits between ONE workload and ONE integrator.

            data = self.ingress.get_data(self.ingress.relations[0])

            application_name = data.app.name
            model_name = data.app.model
            port = data.app.port

        except DataValidationError:
            self.unit.status = ops.BlockedStatus("Invalid ingress data")
            return
        except Exception:
            # If get_data fails (e.g. data not ready), wait.
            self.unit.status = ops.WaitingStatus("Waiting for ingress data")
            return

        logging.error(f"{hostname=}")
        logging.error(f"{paths=}")
        logging.error(f"{port=}")
        logging.error(f"{application_name}")
        logging.error(f"{model_name}")

        # 3. Send to Gateway Route
        try:
            self.gateway_route.send_route_configuration(
                hostname=hostname,
                paths=paths,
                port=port,
                name=application_name,
                model=model_name,
            )
            self.unit.status = ops.ActiveStatus("Ready")
        except Exception as e:
            logger.exception("Failed to send route configuration")
            self.unit.status = ops.BlockedStatus(f"Error sending config: {e}")


if __name__ == "__main__":  # pragma: nocover
    ops.main.main(GatewayRouteConfiguratorCharm)
