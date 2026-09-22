# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for actions when there is no TLS relation."""

import json

import jubilant
import lightkube
import pytest
from helper import get_gateway_resource


@pytest.mark.abort_on_fail
def test_get_proxied_endpoints_action_without_hostname(
    juju: jubilant.Juju,
    configured_application_without_tls: str,
    ingress_requirer_application: str,
    lightkube_client: lightkube.Client,
):
    """Assert that returned URLs use the Gateway address without a hostname."""
    juju.integrate(
        configured_application_without_tls,
        f"{ingress_requirer_application}:ingress",
    )
    juju.wait(
        lambda status: jubilant.all_active(
            status, configured_application_without_tls, ingress_requirer_application
        ),
        error=jubilant.any_error,
    )

    gateway = get_gateway_resource(lightkube_client, configured_application_without_tls)
    gateway_address = gateway.status["addresses"][0]["value"]  # type: ignore
    result = juju.run(f"{configured_application_without_tls}/leader", "get-proxied-endpoints")
    endpoints = json.loads(result.results["proxied-endpoints"])

    assert endpoints[configured_application_without_tls]["url"] == f"http://{gateway_address}"
    assert endpoints[ingress_requirer_application]["url"].startswith(f"http://{gateway_address}/")
