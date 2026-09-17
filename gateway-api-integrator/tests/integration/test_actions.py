# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for actions."""

import json

import jubilant
import lightkube
import pytest
from conftest import TEST_EXTERNAL_HOSTNAME_CONFIG
from helper import get_gateway_resource


@pytest.mark.abort_on_fail
def test_get_certificate_action(
    juju: jubilant.Juju,
    configured_application_with_tls: str,
    ingress_requirer_application: str,
):
    """Deploy the charm with valid config and tls integration.

    Assert on valid output of get-certificate.
    """
    juju.integrate(
        configured_application_with_tls,
        f"{ingress_requirer_application}:ingress",
    )
    juju.wait(
        lambda status: jubilant.all_active(
            status, configured_application_with_tls, ingress_requirer_application
        ),
        error=jubilant.any_error,
    )

    result = juju.run(
        f"{configured_application_with_tls}/leader",
        "get-certificate",
        {"hostname": TEST_EXTERNAL_HOSTNAME_CONFIG},
    )
    assert "certificate" in result.results
    assert "ca" in result.results
    assert "chain" in result.results
    assert result.results["certificate"].startswith("-----BEGIN CERTIFICATE-----")
    assert result.results["ca"].startswith("-----BEGIN CERTIFICATE-----")
    assert result.results["chain"].startswith("-----BEGIN CERTIFICATE-----")


@pytest.mark.abort_on_fail
def test_get_proxied_endpoints_action(
    juju: jubilant.Juju,
    configured_application_with_tls: str,
    ingress_requirer_application: str,
):
    """Assert that get-proxied-endpoints returns gateway and ingress URLs."""
    juju.wait(
        lambda status: jubilant.all_active(
            status, configured_application_with_tls, ingress_requirer_application
        ),
        error=jubilant.any_error,
    )

    result = juju.run(
        f"{configured_application_with_tls}/leader",
        "get-proxied-endpoints",
    )
    endpoints = json.loads(result.results["proxied-endpoints"])
    assert (
        endpoints[configured_application_with_tls]["url"]
        == f"https://{TEST_EXTERNAL_HOSTNAME_CONFIG}"
    )
    assert endpoints[ingress_requirer_application]["url"].startswith(
        f"https://{TEST_EXTERNAL_HOSTNAME_CONFIG}/"
    )


@pytest.mark.abort_on_fail
def test_get_proxied_endpoints_action_without_hostname(
    juju: jubilant.Juju,
    configured_application_without_tls: str,
    ingress_requirer_application: str,
    lightkube_client: lightkube.Client,
):
    """Assert that returned URLs use the Gateway address without a hostname."""
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
