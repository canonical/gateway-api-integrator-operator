# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Ingress requirer any charm."""

import pathlib
import subprocess

from charmlibs import apt
import ops
from any_charm_base import AnyCharmBase
from ingress import IngressPerAppRequirer


class AnyCharm(AnyCharmBase):
    """Any charm that uses the ingress requirer interface."""

    def __init__(self, *args, **kwargs):
        """Initialize the charm.

        Args:
            args: Positional arguments.
            kwargs: Keyword arguments.
        """
        super().__init__(*args, **kwargs)
        self.ingress = IngressPerAppRequirer(
            self, port=80, relation_name="ingress"
        )
        self.framework.observe(self.on.install, self.start_server)
        self.framework.observe(self.on.start, self._on_start)
        self.framework.observe(self.ingress.on.ready, self._on_ingress_ready)

    def start_server(self, _: ops.InstallEvent):
        """Install and prepare Apache content."""
        self.unit.open_port("tcp", 80)
        apt.update()
        apt.add_package(package_names="apache2")
        www_dir = pathlib.Path("/var/www/html/app1")
        file_path = www_dir / "index.html"
        file_path.parent.mkdir(exist_ok=True, parents=True)
        file_path.write_text("Hello from any_charm")

    def _on_start(self, _: ops.StartEvent):
        """Start Apache so the backend is reachable."""
        subprocess.run(["service", "apache2", "start"], check=False)

    def _on_ingress_ready(self, _: ops.EventBase):
        """Relation changed handler."""
        self.unit.status = ops.ActiveStatus("Server Ready")
