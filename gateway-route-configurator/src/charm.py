#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Gateway Route Configurator Charm."""

import logging
import re
import typing

import ops
from charms.gateway_api.v0.gateway_route import GatewayRouteRequirer
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
        self.gateway_route = GatewayRouteRequirer(self, relation_name="gateway-route")

        self.framework.observe(self.on.config_changed, self._on_update)
        self.framework.observe(self.ingress.on.data_provided, self._on_update)
        self.framework.observe(self.ingress.on.data_removed, self._on_update)
        self.framework.observe(self.gateway_route.on.ready, self._on_update)
        self.framework.observe(self.gateway_route.on.removed, self._on_update)

    def _on_update(self, _: typing.Any) -> None:
        """Handle updates to config or relations."""
        self.unit.status = ops.MaintenanceStatus("Configuring gateway route")

        # Check config values
        hostname = str(self.model.config.get("hostname"))
        paths_str = str(self.model.config.get("paths", "/"))

        if not hostname:
            self.unit.status = ops.BlockedStatus("Missing 'hostname' config")
            return

        if not HOSTNAME_REGEX.match(hostname):
            self.unit.status = ops.BlockedStatus(f"Invalid hostname: {hostname}")
            return

        paths = [p.strip() for p in paths_str.split(",")]

        # Check both relations exist
        ingress_relation = self.model.get_relation("ingress")
        if not ingress_relation:
            self.unit.status = ops.BlockedStatus("Missing 'ingress' relation")
            return
        if not self.model.get_relation("gateway-route"):
            self.unit.status = ops.BlockedStatus("Missing 'gateway-route' relation")
            return

        try:
            data = self.ingress.get_data(ingress_relation)
            application_name = data.app.name
            model_name = data.app.model
            port = data.app.port

        except DataValidationError:
            self.unit.status = ops.BlockedStatus("Invalid ingress data")
            return

        self.gateway_route.provide_gateway_route_requirements(
            name=application_name,
            model=model_name,
            port=port,
            paths=paths,
            hostname=hostname,
        )
        # Publish the ingress URL to the requirer charm
        if endpoints := self.gateway_route.get_routed_endpoints():
            self.ingress.publish_url(
                ingress_relation,
                endpoints[0],
            )
            self.unit.status = ops.ActiveStatus("Ready")
        else:
            self.unit.status = ops.MaintenanceStatus("Waiting for gateway route endpoints")


if __name__ == "__main__":  # pragma: nocover
    ops.main.main(GatewayRouteConfiguratorCharm)
