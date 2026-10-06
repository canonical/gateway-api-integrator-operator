# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Ingress requirer implementation injected into any-charm for integration tests."""

import contextlib
import os
import pathlib
import signal
import subprocess  # nosec B404
import sys

import ops
from any_charm_base import AnyCharmBase
from ingress import IngressPerAppRequirer

HTTP_PORT = 8080
RESPONSE_BODY = "Hello from any-charm"
STATE_DIR = pathlib.Path.home() / ".local/state/any-charm-http"


class AnyCharm(AnyCharmBase):
    """Run an ingress requirer and a simple HTTP server on the charm unit."""

    def __init__(self, *args, **kwargs):
        """Initialize the ingress requirer."""
        super().__init__(*args, **kwargs)
        self.ingress = IngressPerAppRequirer(self, port=HTTP_PORT)
        self.framework.observe(self.ingress.on.ready, self._on_ingress_ready)

    def _on_ingress_ready(self, _: ops.EventBase) -> None:
        """Mark the unit active once ingress has published its URL."""
        self.unit.status = ops.ActiveStatus("Server ready")

    def start_server(self) -> int:
        """Start a detached HTTP server and return its port."""
        self.unit.open_port("tcp", HTTP_PORT)

        www_dir = STATE_DIR / "www"
        www_dir.mkdir(parents=True, exist_ok=True)
        response_path = www_dir / f"{self.model.name}-{self.app.name}"
        response_path.write_text(RESPONSE_BODY, encoding="utf-8")

        pid_file = STATE_DIR / "server.pid"
        if pid_file.exists():
            with contextlib.suppress(ProcessLookupError):
                os.kill(int(pid_file.read_text(encoding="utf-8")), signal.SIGKILL)
            pid_file.unlink()

        with (STATE_DIR / "server.log").open("wb+") as log_file:
            # The command contains no external input.
            process = subprocess.Popen(  # nosec B603
                [sys.executable, "-m", "http.server", "-d", str(www_dir), str(HTTP_PORT)],
                start_new_session=True,
                stdout=log_file,
                stderr=log_file,
            )
        pid_file.write_text(str(process.pid), encoding="utf-8")
        return HTTP_PORT
